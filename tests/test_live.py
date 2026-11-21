"""Test cửa sổ chơi trực tiếp (chonoi.live). Chỉ dành cho starter Python: nhóm đổi ngôn ngữ thì xóa file này."""

import json
import time
import unittest
import urllib.error
import urllib.request

from chonoi.contract import load_contract
from chonoi.live import LiveGame, LiveServer


def _get(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.status, r.read()


def _post(url, obj):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        e.close()
        return e.code


class LiveServerTest(unittest.TestCase):
    def test_state_input_and_clean_stop(self):
        tuning = load_contract()["tuning"]
        server = LiveServer(LiveGame("gather", tuning, {}, 1), port=0)  # cổng ngẫu nhiên
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}"
            code, body = _get(base + "/state")
            self.assertEqual(code, 200)
            st = json.loads(body)
            self.assertIn("tick", st)
            self.assertEqual(st["mode"], "gather")
            self.assertEqual(st["player"]["pos"], [2, 0])
            self.assertEqual(_post(base + "/input", {"move": [1, 0], "interact": False, "catch": False}), 200)
            self.assertEqual(_post(base + "/input", {"move": [5, 0]}), 400)
            code, html = _get(base + "/")
            self.assertEqual(code, 200)
            self.assertIn(b"<canvas", html)
            deadline = time.time() + 3
            while time.time() < deadline:
                st2 = json.loads(_get(base + "/state")[1])
                if st2["tick"] > st["tick"] + 3 and st2["player"]["pos"][0] > st["player"]["pos"][0]:
                    break
                time.sleep(0.05)
            self.assertGreater(st2["tick"], st["tick"], "mô phỏng phải chạy nền")
            self.assertGreater(st2["player"]["pos"][0], st["player"]["pos"][0], "input phải tác động tới sim")
        finally:
            server.stop()
        self.assertFalse(server.game._thread.is_alive())
        self.assertFalse(server._thread.is_alive())

    def test_gather_inputs_update_basket_and_resources(self):
        tuning = load_contract()["tuning"]
        gather = tuning["gather"]
        plant = gather["nodes"][0]
        kind = "ca_linh"
        fish = {"id": "F1", "kind": kind,
                "pos": [gather["fish_spawn_x"][0], gather["fish_spawn_depths"][kind][0]]}
        cases = (
            (plant, "interact", "gather", gather["node_yield"]),
            (fish, "catch", "fish_caught", gather["fish_yield"][fish["kind"]]),
        )
        for resource, button, event, amount in cases:
            with self.subTest(button=button):
                scenario = {"player": {"pos": resource["pos"]}, "random_fish": False, "fish": [fish]}
                server = LiveServer(LiveGame("gather", tuning, scenario, 1), port=0)
                server.start()
                try:
                    base = f"http://127.0.0.1:{server.port}"
                    self.assertEqual(_post(base + "/input", {button: True}), 200)
                    deadline = time.monotonic() + 3
                    while True:
                        state = json.loads(_get(base + "/state")[1])
                        if state["hold"] or time.monotonic() >= deadline:
                            break
                        time.sleep(0.02)
                    self.assertEqual(state["hold"], [resource["kind"]] * amount)
                    self.assertIn(event, [row["name"] for row in state["events"]])
                    if button == "interact":
                        node = next(node for node in state["nodes"] if node["id"] == resource["id"])
                        self.assertFalse(node["ready"])
                    else:
                        self.assertNotIn(resource["id"], [school["id"] for school in state["fish"]])
                        self.assertGreater(state["player"]["catch_cd_ticks"], 0)
                finally:
                    server.stop()

    def test_day_mode_live_server(self):
        tuning = load_contract()["tuning"]
        server = LiveServer(LiveGame("day", tuning, {}, 1, days=1), port=0)
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}"
            code, body = _get(base + "/state")
            self.assertEqual(code, 200)
            st = json.loads(body)
            self.assertEqual(st["mode"], "day")
            self.assertEqual(st["day"], 1)
            self.assertIn("day_plan", st)
            self.assertIn("meta", st)
            # Thử gửi input pause, shop_done, buy và presentation
            self.assertEqual(_post(base + "/input", {"pause": True}), 200)
            self.assertEqual(_post(base + "/input", {"shop_done": False, "buy": "oxygen"}), 200)
            self.assertEqual(_post(base + "/presentation", {"action": "advance"}), 200)
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
