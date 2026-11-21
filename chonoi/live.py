"""Cửa sổ chơi trực tiếp bằng TRÌNH DUYỆT, chỉ dùng thư viện chuẩn Python.

    python3 -m chonoi.live --mode gather|quan|day [--days 1..5] [--seed N] [--port 8000]

Máy chủ HTTP nhỏ (ThreadingHTTPServer) phục vụ `chonoi/web/index.html` và các endpoint:
    GET  /state  -> snapshot JSON hiện tại + `meta`, `events` và `presentation`
    POST /input  -> {"move": [a, b], "interact": bool, "catch": bool, "pause": bool, "shop_done": bool, "buy": str}
    POST /presentation -> {"action": "advance" | "menu"}
    POST /restart -> chơi lại từ đầu (cùng seed, cùng scenario)

Mô phỏng chạy 60 tick/s trong một luồng nền, dùng CÙNG lớp sim như headless (qua `runner.Session`).
Client chỉ ĐỌC snapshot và tự bỏ qua trường chưa có, nên luật do nhóm viết thêm trường nào cũng không vỡ.
Ngẫu nhiên vẫn đi qua `Streams` (seed); chỉ nhịp chạy theo đồng hồ thật, không đi vào luật.
"""

import argparse
import json
import os
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .contract import load_contract
from .errors import BadInput
from .inputs import LiveInputs
from .inventory import item_rows, read_inventory
from .runner import Session
from .scenario import load_scenario

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
TICK_S = 1.0 / 60.0
MAX_BODY = 4096
RECENT_EVENTS = 40
PLAY_SCREENS = {"gather", "quan", "shop"}
ADVANCE_SCREEN = {"day_intro": "gather", "evening_intro": "quan", "day_result": "shop"}


class LiveGame:
    """Một lượt chơi + luồng nền bước 60 tick/s. Mọi truy cập trạng thái đi qua khóa."""

    def __init__(self, mode, tuning, scenario, seed, inventory=None, inventory_out=None, days=1, contract_version="1.1"):
        self.mode = mode
        self.tuning = tuning
        self.scenario = scenario
        self.seed = seed
        self.inventory = inventory
        self.inventory_out = inventory_out
        self.days = days
        self.contract_version = contract_version
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._reset()

    def _reset(self):
        self.session = Session(self.mode, self.tuning, self.scenario, self.seed,
                               inventory=self.inventory, days=self.days, contract_version=self.contract_version)
        self.inputs = LiveInputs()
        self.events = []
        self.screen = "menu" if self.mode == "day" else self.mode
        self.day_result = None
        self.summary = None
        self._served = 0
        self._left = 0
        self._tips = 0
        self._shift_reputation = None
        self._dish_counts = {}
        self._saved = False
        self.error = None

    # --- luồng nền ----------------------------------------------------------------
    def start(self):
        self._thread = threading.Thread(target=self._loop, name="chonoi-sim", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self):
        nxt = time.perf_counter()
        while not self._stop.is_set():
            nxt += TICK_S
            with self._lock:
                try:
                    self._tick_once()
                except Exception:  # luật của nhóm lỗi: báo ra terminal + client, dừng bước (restart để chơi lại)
                    self.error = traceback.format_exc()
                    sys.stderr.write(self.error)
                    self.session.sim.done = True
                    self.session.sim.reason = "error"
            delay = nxt - time.perf_counter()
            if delay > 0:
                self._stop.wait(delay)
            elif delay < -0.25:  # chạy chậm quá thì bỏ bù, tránh chạy dồn
                nxt = time.perf_counter()

    def _tick_once(self):
        s = self.session
        if s.done or self.screen not in PLAY_SCREENS:
            return
        rows = s.step(self.inputs.advance())
        self.events.extend(rows)
        del self.events[:-RECENT_EVENTS]
        if self.mode == "day":
            self._update_day_presentation(rows)
        if s.done and not self._saved:
            self._saved = True
            if self.inventory_out:
                try:
                    s.write_inventory_if_done(self.inventory_out)
                except OSError as e:
                    sys.stderr.write(f"lỗi ghi kho: {e}\n")

    def _set_screen(self, screen):
        self.screen = screen
        self.inputs = LiveInputs()

    def _update_day_presentation(self, rows):
        for row in rows:
            name, data = row["name"], row["data"]
            if name == "gather_end":
                self._served = self._left = self._tips = 0
                self._shift_reputation = self.session.sim.reputation
                self.day_result = None
                self._set_screen("evening_intro")
            elif name == "served":
                self._served += 1
                dish = data["dish_id"]
                self._dish_counts[dish] = self._dish_counts.get(dish, 0) + 1
            elif name == "customer_left":
                self._left += 1
            elif name == "paid":
                self._tips += data["tip"]
            elif name == "quan_end":
                self.day_result = {
                    "served": self._served, "left": self._left,
                    "shift_earned": data["shift_earned"], "tip": self._tips,
                    "reputation_delta": data["reputation"] - self._shift_reputation,
                }
                self._set_screen("day_result")
            elif name == "shop_end":
                if self.session.done:
                    result = self.session.end_row()
                    best = max(self._dish_counts.values(), default=0)
                    self.summary = {key: result[key] for key in ("money", "earned", "score", "reputation")}
                    self.summary["top_dishes"] = sorted(
                        dish for dish, count in self._dish_counts.items() if count == best
                    )
                    self._set_screen("summary")
                else:
                    self.day_result = None
                    self._set_screen("day_intro")

    # --- API cho handler -----------------------------------------------------------
    def state_json(self) -> bytes:
        with self._lock:
            snap = self.session.snapshot()
            cur_phase = getattr(self.session.sim, "phase", self.mode)
            if cur_phase == "shop" and isinstance(snap["stock"], list):
                snap["stock"] = item_rows(snap["stock"])
            snap["meta"] = self.tuning.get(cur_phase, self.tuning.get(self.mode, {}))
            if "freshness" in self.tuning:
                snap["meta"] = {**snap["meta"], "freshness": self.tuning["freshness"]}
            snap["presentation"] = {
                "screen": self.screen, "day_result": self.day_result, "summary": self.summary,
            }
            snap["events"] = list(self.events)
            snap["finished"] = self.session.done
            snap["reason"] = self.session.sim.reason if self.session.done else None
            snap["error"] = self.error
            return json.dumps(snap, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def set_input(self, body: dict):
        move = body.get("move")
        if move is not None:
            ok = (isinstance(move, list) and len(move) == 2 and
                  all(isinstance(c, (int, float)) and not isinstance(c, bool) and abs(c) <= 1 for c in move))
            if not ok:
                raise ValueError("move phải là [a, b] trong [-1, 1]")
        buttons = {}
        for b in ("interact", "catch", "pause", "shop_done", "attack", "photo"):
            if b in body:
                if not isinstance(body[b], bool):
                    raise ValueError(f"{b} phải là boolean")
                buttons[b] = body[b]
        buy = body.get("buy")
        if buy is not None:
            if not isinstance(buy, str):
                raise ValueError("buy phải là chuỗi")
        with self._lock:
            if self.screen in PLAY_SCREENS and not self.session.done:
                self.inputs.set(move, buy=buy, **buttons)

    def set_presentation(self, action):
        if action not in ("advance", "menu"):
            raise ValueError("action phải là advance hoặc menu")
        with self._lock:
            if action == "menu":
                self._reset()
                self._set_screen("menu")
            elif self.screen == "menu":
                self._set_screen("day_intro" if self.mode == "day" else self.mode)
            elif self.screen in ADVANCE_SCREEN:
                self._set_screen(ADVANCE_SCREEN[self.screen])

    def restart(self):
        with self._lock:
            self._reset()
            if self.mode == "day":
                self._set_screen("day_intro")


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    game: LiveGame = None  # gán trên lớp con trong make_server

    def log_message(self, fmt, *args):  # yên lặng
        pass

    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/state":
            self._send(200, self.game.state_json())
        elif path in ("/", "/index.html"):
            try:
                with open(os.path.join(WEB_DIR, "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(404, b'{"error":"thieu index.html"}')
        else:
            self._send(404, b'{"error":"khong co"}')

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if n < 0 or n > MAX_BODY:
            self._send(400, b'{"error":"body sai"}')
            return
        raw = self.rfile.read(n) if n else b""
        try:
            if path == "/input":
                body = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(body, dict):
                    raise ValueError("body phải là object")
                self.game.set_input(body)
            elif path == "/presentation":
                body = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(body, dict):
                    raise ValueError("body phải là object")
                self.game.set_presentation(body.get("action"))
            elif path == "/restart":
                self.game.restart()
            else:
                self._send(404, b'{"error":"khong co"}')
                return
        except (ValueError, UnicodeDecodeError) as e:
            self._send(400, json.dumps({"error": str(e)}).encode("utf-8"))
            return
        self._send(200, b'{"ok":true}')


class LiveServer:
    """Máy chủ + mô phỏng. port=0 -> cổng ngẫu nhiên (đọc `.port`)."""

    def __init__(self, game: LiveGame, host="127.0.0.1", port=8000):
        handler = type("Handler", (_Handler,), {"game": game})
        self.game = game
        self.httpd = ThreadingHTTPServer((host, port), handler)
        self.httpd.daemon_threads = True
        self.host = host
        self.port = self.httpd.server_address[1]
        self._thread = None

    @property
    def url(self):
        return f"http://{self.host}:{self.port}/"

    def start(self):
        self.game.start()
        self._thread = threading.Thread(target=self.httpd.serve_forever, name="chonoi-http", daemon=True)
        self._thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        if self._thread:
            self._thread.join(timeout=2)
        self.game.stop()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.live", description="Chơi trực tiếp trên trình duyệt.")
    p.add_argument("--mode", required=True, choices=["gather", "quan", "day"])
    p.add_argument("--days", type=int, default=1)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--port", type=int, default=8000, help="0 = cổng ngẫu nhiên")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--scenario")
    p.add_argument("--inventory", help="chỉ với quan: nạp kho từ file")
    p.add_argument("--inventory-out", dest="inventory_out", help="chỉ với gather: ghi kho khi kết thúc buổi")
    a = p.parse_args(argv)
    try:
        if a.inventory and a.mode != "quan":
            raise BadInput("--inventory chỉ dùng với quan")
        if a.inventory_out and a.mode != "gather":
            raise BadInput("--inventory-out chỉ dùng với gather")
        if a.mode == "day" and (a.inventory or a.inventory_out):
            raise BadInput("chế độ day không dùng --inventory hoặc --inventory-out")
        contract = load_contract()
        tuning = contract["tuning"]
        contract_version = contract.get("contract_version", "1.1")
        try:
            scenario = load_scenario(a.scenario, a.mode, tuning, contract_version=contract_version)
        except TypeError:
            scenario = load_scenario(a.scenario, a.mode, tuning)
        if a.inventory:
            try:
                inventory = read_inventory(a.inventory, contract_version=contract_version)
            except TypeError:
                inventory = read_inventory(a.inventory)
        else:
            inventory = None
        if inventory is not None and scenario and "stock" in scenario:
            raise BadInput("vừa có quan.stock vừa có --inventory")
        game = LiveGame(a.mode, tuning, scenario, a.seed, inventory=inventory,
                        inventory_out=a.inventory_out, days=a.days, contract_version=contract_version)
        server = LiveServer(game, a.host, a.port)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"không mở được cổng {a.port}: {e}\n")
        return 1
    server.start()
    print(f"Mở trình duyệt tại {server.url}  (chế độ {a.mode}, seed {a.seed}). Ctrl+C để dừng.", flush=True)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
