"""Soak headless nhiều Ngày (Phase 4 · Test Contract v1.3).

Cách chạy:
    python3 -m chonoi.soak --seed 7 --days 10 --out soak.json

Đặc điểm:
- Dùng MỘT Session / DaySim cho toàn bộ N Ngày (mở rộng giới hạn 1..5 qua allow_extended_days=True).
- Bot tất định 100%, chỉ đọc snapshot, tuning và tick; không dùng random toàn cục hay đồng hồ hệ thống
  trong quyết định gameplay.
- Ghi đúng một kết quả {day, earned, reputation, score} khi nhận event `shop_end`, lấy `day` từ event.
- Mã thoát: 0 khi days_completed == days và crashes == 0; 2 khi tham số/đầu vào sai (không tạo file đích);
  1 khi crash, chạy không hoàn tất hoặc lỗi ghi.
"""

import argparse
import json
import math
import os
import sys
import tempfile
import time

from .contract import load_contract
from .errors import BadInput
from .ids import id_key
from .inputs import BUTTONS_V11, InputState, normalize
from .runner import Session
from .sim.shop import DEFAULT_UPGRADES


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"lỗi: {message}\n")
        sys.exit(2)


def _int(name):
    def conv(s):
        try:
            return int(s)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{name} phải là số nguyên")
    return conv


def _direction_to(pos, target) -> tuple:
    dx = float(target[0]) - float(pos[0])
    dy = float(target[1]) - float(pos[1])
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return (0.0, 0.0)
    return normalize((dx / dist, dy / dist))


def _hold_counts(hold) -> dict:
    counts = {}
    for item in hold:
        kind = item["kind"] if isinstance(item, dict) else item
        counts[kind] = counts.get(kind, 0) + 1
    return counts


class DeterministicSoakBot:
    """Bot tất định điều khiển Út Sen qua Gather -> Quán -> Shop trong nhiều Ngày."""

    def __init__(self, tuning):
        self.tuning = tuning
        self._held = {b: False for b in BUTTONS_V11}

    def _make_input(self, move=(0.0, 0.0), press=None, buy=None) -> InputState:
        """Tạo InputState có cạnh lên hợp lệ (tự nhả ở tick sau nếu nút đang giữ)."""
        want = set(press or ())
        edges = set()
        for b in BUTTONS_V11:
            if b in want and not self._held[b]:
                edges.add(b)
                self._held[b] = True
            else:
                self._held[b] = False
        return InputState(normalize(move), dict(self._held), edges, buy=buy)

    def decide(self, snap: dict) -> InputState:
        phase = snap.get("phase")
        if phase == "gather":
            return self._decide_gather(snap)
        if phase == "quan":
            return self._decide_quan(snap)
        if phase == "shop":
            return self._decide_shop(snap)
        return self._make_input()

    def _decide_gather(self, snap: dict) -> InputState:
        g_cfg = self.tuning["gather"]
        player = snap["player"]
        pos = player["pos"]
        dock_pos = g_cfg["dock_pos"]
        dock_r = g_cfg["dock_radius"]
        interact_r = g_cfg["interact_radius"]
        catch_r = g_cfg["catch_radius"]
        fish_yield = g_cfg["fish_yield"]

        hold = snap.get("hold", [])
        hold_count = snap.get("hold_count", len(hold))
        hold_cap = snap.get("hold_capacity", g_cfg["hold_capacity"])
        have = _hold_counts(hold)
        plan_ing = snap.get("day_plan", {}).get("ingredients", {})
        needed = {k: amt - have.get(k, 0) for k, amt in plan_ing.items() if amt > have.get(k, 0)}

        oxy_max = max(1, player.get("oxygen_max_ticks", 1))
        oxy = player.get("oxygen_ticks", oxy_max)
        at_surface = player.get("at_surface", True)

        # 1. An toàn oxy: lên mặt nước trước khi cạn oxy
        if not at_surface and oxy < oxy_max * 0.45:
            return self._make_input(move=(0.0, -1.0))

        # 2. Điều kiện về bến: đầy giỏ, đủ nguyên liệu theo kế hoạch, hoặc sắp hết giờ
        time_left = snap.get("time_left_ticks", 0)
        dist_dock = math.dist(pos, dock_pos)
        return_time_ticks = int((dist_dock / max(0.5, g_cfg["swim_speed"])) * self.tuning["tick_hz"]) + 180
        go_dock = (
            hold_count >= hold_cap
            or (plan_ing and not needed)
            or (hold_count > 0 and time_left <= max(600, return_time_ticks))
        )

        if go_dock:
            if dist_dock <= dock_r * 0.85:
                return self._make_input(move=(0.0, 0.0), press=("interact",))
            return self._make_input(move=_direction_to(pos, dock_pos))

        # 3. Ưu tiên hái nút mặt nước đang sẵn sàng cho nguyên liệu còn thiếu
        nodes = snap.get("nodes", [])
        ready_needed_nodes = [
            n for n in nodes
            if n.get("ready") and needed.get(n["kind"], 0) > 0
            and hold_count + g_cfg["node_yield"] <= hold_cap
        ]
        if ready_needed_nodes:
            target = min(ready_needed_nodes, key=lambda n: (math.dist(pos, n["pos"]), id_key(n["id"])))
            if math.dist(pos, target["pos"]) <= interact_r * 0.85:
                return self._make_input(move=(0.0, 0.0), press=("interact",))
            return self._make_input(move=_direction_to(pos, target["pos"]))

        # 4. Bắt cá còn thiếu (tránh lại gần thủy quái đang tuần tra/đuổi)
        monsters = snap.get("monsters", [])

        def _monster_dist(pt):
            if not monsters:
                return 999.0
            return min(math.dist(pt, m["pos"]) for m in monsters)

        fish_list = snap.get("fish", [])
        wanted_fish = [
            f for f in fish_list
            if needed.get(f["kind"], 0) > 0
            and hold_count + fish_yield.get(f["kind"], 1) <= hold_cap
            and _monster_dist(f["pos"]) > 6.0
        ]
        if wanted_fish:
            target = min(wanted_fish, key=lambda f: (math.dist(pos, f["pos"]), id_key(f["id"])))
            if math.dist(pos, target["pos"]) <= catch_r * 0.85 and player.get("catch_cd_ticks", 0) == 0:
                return self._make_input(move=(0.0, 0.0), press=("catch",))
            return self._make_input(move=_direction_to(pos, target["pos"]))

        # 5. Nếu đã có hàng trong giỏ thì về bến sớm để giữ độ tươi cao và mở Quán
        if hold_count > 0:
            if dist_dock <= dock_r * 0.85:
                return self._make_input(move=(0.0, 0.0), press=("interact",))
            return self._make_input(move=_direction_to(pos, dock_pos))

        # 6. Chưa có hàng nào: lấy nút gần nhất đang sẵn sàng hoặc cá gần nhất an toàn
        any_ready_nodes = [
            n for n in nodes
            if n.get("ready") and hold_count + g_cfg["node_yield"] <= hold_cap
        ]
        if any_ready_nodes:
            target = min(any_ready_nodes, key=lambda n: (math.dist(pos, n["pos"]), id_key(n["id"])))
            if math.dist(pos, target["pos"]) <= interact_r * 0.85:
                return self._make_input(move=(0.0, 0.0), press=("interact",))
            return self._make_input(move=_direction_to(pos, target["pos"]))

        return self._make_input(move=_direction_to(pos, dock_pos))

    def _decide_quan(self, snap: dict) -> InputState:
        q_cfg = self.tuning["quan"]
        pos = snap["player"]["pos"]
        hand = snap.get("hand")
        stoves = snap.get("stoves", [])
        tables = snap.get("tables", [])
        customers = snap.get("customers", [])
        table_by_id = {tb["id"]: tb for tb in tables}
        # Tiến sát mục tiêu (< 0.45) để đảm bảo trong interact_radius và luôn là vật thể gần nhất
        aim_r = min(0.45, q_cfg["interact_radius"] * 0.4)

        # 1. Đang bưng món -> giao đúng bàn của đơn đó
        if isinstance(hand, dict):
            cust = next(
                (c for c in customers if c["id"] == hand.get("order_id") and c.get("state") == "waiting"),
                None,
            )
            if cust is not None:
                tb = table_by_id.get(cust["table_id"])
                if tb is not None:
                    if math.dist(pos, tb["pos"]) <= aim_r:
                        return self._make_input(move=(0.0, 0.0), press=("interact",))
                    return self._make_input(move=_direction_to(pos, tb["pos"]))

        # 2. Tay trống & có bếp đã nấu xong -> tới lấy món
        if hand is None:
            ready_stoves = [s for s in stoves if s.get("state") == "ready"]
            if ready_stoves:
                target = min(ready_stoves, key=lambda s: (math.dist(pos, s["pos"]), id_key(s["id"])))
                if math.dist(pos, target["pos"]) <= aim_r:
                    return self._make_input(move=(0.0, 0.0), press=("interact",))
                return self._make_input(move=_direction_to(pos, target["pos"]))

        # 3. Có khách đang chờ (đã giữ nguyên liệu) & có bếp rảnh -> tới bật bếp
        has_reserved = any(
            c.get("state") == "waiting" and c.get("order_status") == "reserved"
            for c in customers
        )
        idle_stoves = [s for s in stoves if s.get("state") == "idle"]
        if has_reserved and idle_stoves:
            target = min(idle_stoves, key=lambda s: (math.dist(pos, s["pos"]), id_key(s["id"])))
            if math.dist(pos, target["pos"]) <= aim_r:
                return self._make_input(move=(0.0, 0.0), press=("interact",))
            return self._make_input(move=_direction_to(pos, target["pos"]))

        # 4. Chờ ở gần bếp đầu tiên
        if stoves:
            home = stoves[0]["pos"]
            if math.dist(pos, home) > aim_r:
                return self._make_input(move=_direction_to(pos, home))
        return self._make_input()

    def _decide_shop(self, snap: dict) -> InputState:
        money = snap.get("money", 0)
        upgrades = snap.get("upgrades", {})
        cfg = self.tuning.get("shop", {}).get("upgrades", DEFAULT_UPGRADES)

        # Mua nâng cấp theo thứ tự cố định nếu đủ tiền
        for kind in sorted(cfg.keys()):
            levels = cfg[kind]
            cur_lvl = upgrades.get(kind, 0)
            if cur_lvl < len(levels):
                price = levels[cur_lvl]["price"]
                if money >= price:
                    return self._make_input(buy=kind)

        # Hết món cần mua -> đóng Shop
        return self._make_input(press=("shop_done",))


def _write_json_atomic(path: str, payload: dict) -> None:
    abs_path = os.path.abspath(path)
    parent = os.path.dirname(abs_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".soak-", suffix=".tmp", dir=parent or ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp_path, abs_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def run_soak(seed: int, days: int, *, tuning: dict = None, contract_version: str = None,
             scenario: dict = None, bot_cls=DeterministicSoakBot) -> dict:
    """Chạy soak N Ngày trên MỘT Session/DaySim và trả từ điển kết quả."""
    if isinstance(days, bool) or not isinstance(days, int) or days <= 0:
        raise BadInput("--days phải là số nguyên >= 1")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise BadInput("--seed phải là số nguyên")

    if tuning is None or contract_version is None:
        contract = load_contract()
        if tuning is None:
            tuning = contract["tuning"]
        if contract_version is None:
            contract_version = contract["contract_version"]

    t0 = time.perf_counter()
    results = []
    crashes = 0
    days_completed = 0
    error_message = None

    tick_hz = int(tuning.get("tick_hz", 60))
    gather_ticks = int(round(tuning["gather"]["duration_s"] * tick_hz))
    quan_ticks = int(round(tuning["quan"]["duration_s"] * tick_hz))
    shop_ticks = int(tuning.get("shop", {}).get("max_ticks", 600))
    max_ticks = days * (gather_ticks + quan_ticks + shop_ticks + 120) + 600
    rep_mult = tuning["score"]["reputation_multiplier"]

    sess = None
    try:
        sess = Session(
            "day",
            tuning,
            scenario or {},
            seed,
            days=days,
            contract_version=contract_version,
            allow_extended_days=True,
        )
        if hasattr(sess.sim, "flush_initial_events"):
            sess.sim.flush_initial_events()
        bot = bot_cls(tuning)

        while not sess.done and sess.tick < max_ticks:
            snap = sess.snapshot()
            inp = bot.decide(snap)
            evs = sess.step(inp)
            for ev in evs:
                if ev.get("name") == "shop_end":
                    closed_day = int(ev.get("day", sess.sim.days_completed))
                    earned = sess.sim.earned
                    reputation = sess.sim.reputation
                    score = earned + rep_mult * math.floor(reputation)
                    results.append({
                        "day": closed_day,
                        "earned": earned,
                        "reputation": reputation,
                        "score": score,
                    })

        days_completed = int(getattr(sess.sim, "days_completed", 0))
    except Exception as exc:
        crashes += 1
        error_message = f"{type(exc).__name__}: {exc}"
        if sess is not None:
            days_completed = int(getattr(sess.sim, "days_completed", 0))

    duration_s = round(time.perf_counter() - t0, 4)
    payload = {
        "days": days,
        "days_completed": days_completed,
        "crashes": crashes,
        "results": results,
        "duration_s": duration_s,
    }
    return payload, error_message


def main(argv=None) -> int:
    p = _Parser(prog="chonoi.soak")
    p.add_argument("--seed", required=True, type=_int("seed"))
    p.add_argument("--days", required=True, type=_int("days"))
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)

    try:
        if a.days <= 0:
            raise BadInput("--days phải là số nguyên >= 1")
        if not a.out or not a.out.strip():
            raise BadInput("--out không được rỗng")
        contract = load_contract()
        tuning = contract["tuning"]
        version = contract["contract_version"]
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2

    payload, error_message = run_soak(
        a.seed,
        a.days,
        tuning=tuning,
        contract_version=version,
    )

    try:
        _write_json_atomic(a.out, payload)
    except OSError as e:
        sys.stderr.write(f"lỗi ghi: {e}\n")
        return 1

    if error_message is not None:
        sys.stderr.write(f"lỗi soak: {error_message}\n")
        return 1

    if payload["crashes"] != 0 or payload["days_completed"] != a.days or len(payload["results"]) != a.days:
        sys.stderr.write(
            f"soak chưa hoàn tất: days_completed={payload['days_completed']}/{a.days}, "
            f"results={len(payload['results'])}, crashes={payload['crashes']}\n"
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
