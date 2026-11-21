"""Unit tests cho Quán Service (Phase 1 regression — tương thích cả v1.1 và v1.2):
Bếp, bưng món, phục vụ tại bàn, tính tiền, boa, uy tín, tương tác và đóng ca.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json


def contract_data():
    with open("game.contract.json", encoding="utf-8") as f:
        return json.load(f)


def is_v12():
    return "freshness" in contract_data().get("tuning", {})


class TestQuanService(unittest.TestCase):
    def test_01_cook_started_and_dish_ready(self):
        """Đứng ở bếp B1 [2, 8], kho có nguyên liệu, có khách đặt đơn -> bấm interact:
        Bếp chuyển sang cooking, phát cook_started, trừ kho vật lý.
        Sau 360 tick (6s) nấu xong -> phát dish_ready, bếp chuyển sang ready.
        """
        v12 = is_v12()
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "quan": {
                    "player": {"pos": [2, 8], "vel": [0, 0]},
                    "stock": [{"id": "I1", "kind": "ca_loc", "fresh": 100}] if v12 else {"ca_loc": 1},
                    "customers": [{
                        "id": "C1",
                        "table_id": "T1",
                        "dish_id": "ca_loc_nuong_trui",
                        "order_tick": 0,
                        "state": "waiting",
                        "patience_ticks_left": 3600,
                        "eat_ticks_left": 0,
                        "order_status": "reserved",
                        "reserved": ["I1"] if v12 else {"ca_loc": 1},
                        "base_price": 60,
                        "tip": 0,
                    }],
                    "random_customers": False,
                }
            })
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},
                {"tick": 1, "interact": False},
            ))
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "365",
                                     "--scenario", sc, "--inputs", inp, "--snapshot-every", "1",
                                     "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))

            cook_ev = events(rows, "cook_started")
            self.assertEqual(len(cook_ev), 1)
            self.assertEqual(cook_ev[0]["data"]["stove_id"], "B1")
            self.assertEqual(cook_ev[0]["data"]["order_id"], "C1")
            self.assertEqual(cook_ev[0]["data"]["dish_id"], "ca_loc_nuong_trui")
            if v12:
                # Ở v1.2, I1 hao 1 tick ở bước 0 (100 - 1/240) -> floor(60 * fresh / 100) = 59
                self.assertEqual(cook_ev[0]["data"]["base_price"], 59)
                self.assertEqual([it["id"] for it in cook_ev[0]["data"]["items"]], ["I1"])
            else:
                self.assertEqual(cook_ev[0]["data"]["base_price"], 60)
                self.assertEqual(cook_ev[0]["data"]["items"], ["ca_loc"])

            ready_ev = events(rows, "dish_ready")
            self.assertEqual(len(ready_ev), 1)
            self.assertEqual(ready_ev[0]["data"]["stove_id"], "B1")
            self.assertEqual(ready_ev[0]["data"]["order_id"], "C1")
            self.assertEqual(ready_ev[0]["data"]["dish_id"], "ca_loc_nuong_trui")

            s_final = snapshots(rows)[-1]
            self.assertEqual(s_final["stock"], [] if v12 else {})
            stoves = {s["id"]: s for s in s_final["stoves"]}
            self.assertEqual(stoves["B1"]["state"], "ready")
            self.assertGreater(stoves["B1"]["ready_ticks"], 0)

    def test_02_dish_picked_up(self):
        """Bếp B1 đang ready với món -> bấm interact khi tay trống -> bưng lên tay, bếp về idle."""
        v12 = is_v12()
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "quan": {
                    "player": {"pos": [2, 8]},
                    "stoves": [{
                        "id": "B1",
                        "pos": [2, 8],
                        "state": "ready",
                        "dish": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
                        "cook_ticks_left": 0,
                        "ready_ticks": 10,
                    }],
                    "customers": [{
                        "id": "C1",
                        "table_id": "T1",
                        "dish_id": "ca_loc_nuong_trui",
                        "state": "waiting",
                        "order_status": "assigned",
                        "reserved": [] if v12 else {},
                    }],
                    "random_customers": False,
                }
            })
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},
                {"tick": 1, "interact": False},
            ))
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))

            pick_ev = events(rows, "dish_picked")
            self.assertEqual(len(pick_ev), 1)
            self.assertEqual(pick_ev[0]["data"]["stove_id"], "B1")
            self.assertEqual(pick_ev[0]["data"]["order_id"], "C1")
            self.assertEqual(pick_ev[0]["data"]["dish_id"], "ca_loc_nuong_trui")

            s_final = snapshots(rows)[-1]
            self.assertEqual(s_final["hand"], {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60})
            stoves = {s["id"]: s for s in s_final["stoves"]}
            self.assertEqual(stoves["B1"]["state"], "idle")
            self.assertIsNone(stoves["B1"]["dish"])

    def test_03_served_with_tip(self):
        """Phục vụ tại bàn T1 khi kiên nhẫn còn >= 50% -> chốt boa floor(60 * 0.2) = 12."""
        v12 = is_v12()
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "quan": {
                    "player": {"pos": [9, 2]},
                    "hand": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
                    "customers": [{
                        "id": "C1",
                        "table_id": "T1",
                        "dish_id": "ca_loc_nuong_trui",
                        "order_tick": 0,
                        "state": "waiting",
                        "patience_ticks_left": 3000,
                        "eat_ticks_left": 0,
                        "order_status": "assigned",
                        "reserved": [] if v12 else {},
                        "base_price": 60,
                        "tip": 0,
                    }],
                    "random_customers": False,
                }
            })
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},
                {"tick": 1, "interact": False},
            ))
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))

            served_ev = events(rows, "served")
            self.assertEqual(len(served_ev), 1)
            self.assertEqual(served_ev[0]["data"]["base_price"], 60)
            self.assertEqual(served_ev[0]["data"]["tip"], 12)

            s_final = snapshots(rows)[-1]
            self.assertIsNone(s_final["hand"])
            cust = s_final["customers"][0]
            self.assertEqual(cust["state"], "eating")
            self.assertEqual(cust["tip"], 12)

    def test_04_served_without_tip_when_low_patience(self):
        """Khách kiên nhẫn còn < 50% -> boa = 0."""
        v12 = is_v12()
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "quan": {
                    "player": {"pos": [9, 2]},
                    "hand": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
                    "customers": [{
                        "id": "C1",
                        "table_id": "T1",
                        "dish_id": "ca_loc_nuong_trui",
                        "order_tick": 0,
                        "state": "waiting",
                        "patience_ticks_left": 1000,
                        "eat_ticks_left": 0,
                        "order_status": "assigned",
                        "reserved": [] if v12 else {},
                        "base_price": 60,
                        "tip": 0,
                    }],
                    "random_customers": False,
                }
            })
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},
                {"tick": 1, "interact": False},
            ))
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            served_ev = events(rows, "served")
            self.assertEqual(len(served_ev), 1)
            self.assertEqual(served_ev[0]["data"]["tip"], 0)

    def test_05_paid_when_finished_eating(self):
        """Khách ăn xong trả tiền, cộng uy tín và rời bàn."""
        v12 = is_v12()
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "quan": {
                    "player": {"pos": [8, 5]},
                    "reputation": 3.0,
                    "customers": [{
                        "id": "C1",
                        "table_id": "T1",
                        "dish_id": "ca_loc_nuong_trui",
                        "order_tick": 0,
                        "state": "eating",
                        "patience_ticks_left": 2000,
                        "eat_ticks_left": 2,
                        "order_status": "served",
                        "reserved": [] if v12 else {},
                        "base_price": 60,
                        "tip": 12,
                    }],
                    "random_customers": False,
                }
            })
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "3",
                                     "--scenario", sc, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))

            paid_ev = events(rows, "paid")
            self.assertEqual(len(paid_ev), 1)
            self.assertEqual(paid_ev[0]["data"]["amount"], 72)
            self.assertEqual(paid_ev[0]["data"]["reason"], "finished_eating")

            s_final = snapshots(rows)[-1]
            self.assertEqual(s_final["money"], 72)
            self.assertAlmostEqual(s_final["reputation"], 3.2, places=2)
            self.assertEqual(len(s_final["customers"]), 0)

    def test_06_closing_pays_eating(self):
        """Khi hết ca: khách đang ăn lập tức trả tiền closing, phát quan_end."""
        v12 = is_v12()
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "quan": {
                    "player": {"pos": [8, 5]},
                    "time_left_ticks": 1,
                    "reputation": 3.0,
                    "customers": [{
                        "id": "C1",
                        "table_id": "T1",
                        "dish_id": "ca_loc_nuong_trui",
                        "order_tick": 0,
                        "state": "eating",
                        "patience_ticks_left": 2000,
                        "eat_ticks_left": 500,
                        "order_status": "served",
                        "reserved": [] if v12 else {},
                        "base_price": 60,
                        "tip": 12,
                    }],
                    "random_customers": False,
                }
            })
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))

            paid_ev = events(rows, "paid")
            self.assertEqual(len(paid_ev), 1)
            self.assertEqual(paid_ev[0]["data"]["reason"], "closing")
            end_ev = events(rows, "quan_end")
            self.assertEqual(end_ev[0]["data"]["money"], 72)
            self.assertAlmostEqual(end_ev[0]["data"]["reputation"], 3.2, places=2)


if __name__ == "__main__":
    unittest.main()