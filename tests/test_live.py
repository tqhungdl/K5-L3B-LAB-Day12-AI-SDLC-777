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


def _state(base):
    return json.loads(_get(base + "/state")[1])


class LiveServerTest(unittest.TestCase):
    def test_state_input_and_clean_stop(self):
        contract = load_contract()
        game = LiveGame("gather", contract["tuning"], {}, 1, contract_version=contract["contract_version"])
        server = LiveServer(game, port=0)  # cổng ngẫu nhiên
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
        contract = load_contract()
        tuning = contract["tuning"]
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
                game = LiveGame("gather", tuning, scenario, 1, contract_version=contract["contract_version"])
                server = LiveServer(game, port=0)
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
                    kinds = [item["kind"] for item in state["hold"]] if "freshness" in tuning else state["hold"]
                    self.assertEqual(kinds, [resource["kind"]] * amount)
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
        contract = load_contract()
        tuning = contract["tuning"]
        version = contract["contract_version"] if "freshness" in tuning else "1.2"
        tuning.setdefault("freshness", {
            "initial": 100, "gather_decay_per_s": 0.5, "quan_decay_per_s": 0.25,
            "spoiled_below": 30,
        })
        dish = "goi_bong_sung"
        table, other = tuning["quan"]["tables"][:2]
        scenario = {
            "gather": {
                "hold": [{"id": "I1", "kind": "ca_loc", "fresh": 95}],
                "random_fish": False, "monsters": [],
            },
            "quan": {
                "time_left_ticks": 90, "random_customers": False,
                "player": {"pos": table["pos"]},
                "hand": {"order_id": "C1", "dish_id": dish, "base_price": 40},
                "customers": [
                    {"id": "C1", "table_id": table["id"], "dish_id": dish,
                     "state": "waiting", "order_status": "assigned", "patience_ticks_left": 3500},
                    {"id": "C2", "table_id": other["id"], "dish_id": dish,
                     "state": "waiting", "order_status": "unfulfillable", "patience_ticks_left": 1},
                ],
            },
        }
        game = LiveGame("day", tuning, scenario, 1, days=1, contract_version=version)
        server = LiveServer(game, port=0)
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}"
            timers = ("tick", "sim_tick", "phase_tick", "time_left_ticks")

            def wait_screen(wanted):
                deadline = time.monotonic() + 3
                while True:
                    state = _state(base)
                    if state["presentation"]["screen"] == wanted or time.monotonic() >= deadline:
                        self.assertEqual(state["presentation"]["screen"], wanted, state["error"])
                        return state
                    time.sleep(0.02)

            def assert_waiting(screen):
                before = wait_screen(screen)
                time.sleep(0.08)
                after = wait_screen(screen)
                self.assertEqual([before[key] for key in timers], [after[key] for key in timers])
                return after

            def advance():
                self.assertEqual(_post(base + "/presentation", {"action": "advance"}), 200)

            st = assert_waiting("menu")
            self.assertEqual(st["mode"], "day")
            self.assertEqual(st["day"], 1)
            self.assertIn("day_plan", st)
            for bad in ([], {}, {"action": "shop"}, {"action": ["advance"]}):
                self.assertEqual(_post(base + "/presentation", bad), 400)
            advance()
            assert_waiting("day_intro")
            self.assertEqual(_post(base + "/input", {"pause": True}), 200)
            advance()
            self.assertEqual(wait_screen("gather")["state"], "playing")
            self.assertEqual(_post(base + "/input", {"interact": True}), 200)
            evening = assert_waiting("evening_intro")
            self.assertEqual(evening["phase_tick"], 0)
            self.assertEqual([item["id"] for item in evening["stock"]], ["I1"])
            self.assertEqual(evening["meta"]["freshness"]["spoiled_below"], 30)
            self.assertEqual(_post(base + "/input", {"interact": True}), 200)
            advance()
            self.assertIsNotNone(wait_screen("quan")["hand"])
            self.assertEqual(_post(base + "/input", {"interact": True}), 200)
            after_quan = assert_waiting("day_result")
            self.assertEqual(set(after_quan["stock"][0]), {"id", "kind", "fresh"})
            result = after_quan["presentation"]["day_result"]
            self.assertEqual({key: result[key] for key in ("served", "left", "shift_earned", "tip")},
                             {"served": 1, "left": 1, "shift_earned": 48, "tip": 8})
            self.assertAlmostEqual(result["reputation_delta"], -0.3)
            advance()
            wait_screen("shop")
            self.assertEqual(_post(base + "/input", {"shop_done": True}), 200)
            final = assert_waiting("summary")
            self.assertEqual(final["reason"], "days_complete")
            self.assertEqual(final["presentation"]["summary"]["top_dishes"], [dish])
            for key in ("money", "earned", "score", "reputation"):
                self.assertEqual(final["presentation"]["summary"][key], final[key])

            self.assertEqual(_post(base + "/presentation", {"action": "menu"}), 200)
            menu = assert_waiting("menu")
            self.assertEqual(menu["tick"], 0)
            self.assertIsNone(menu["presentation"]["summary"])
            self.assertEqual(_post(base + "/restart", {}), 200)
            assert_waiting("day_intro")
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
