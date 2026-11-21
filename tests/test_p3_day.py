"""Unit tests cho Lát 4 Phase 3 (Người 4 · Integrator: Day, Shop, HUD & Kho cá thể).

AC-P3-01, AC-P3-06, AC-P3-07, AC-P3-08.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json
from chonoi.ids import IdAllocator
from chonoi.inputs import LiveInputs
from chonoi.rng import Streams
from chonoi.sim.day import DaySim, resolve_day_plans
from chonoi.sim.shop import ShopSim


def load_tuning():
    with open("game.contract.json", encoding="utf-8") as f:
        return json.load(f)["tuning"]


class TestDayPhase3(unittest.TestCase):
    def test_01_shop_with_item_list(self):
        """Shop nhận danh sách cá thể [dict(id, kind, fresh)], snapshot xuất mảng sắp ID."""
        tuning = load_tuning()
        raw_items = [
            {"id": "I10", "kind": "ca_loc", "fresh": 85.0},
            {"id": "I2", "kind": "bong_sung", "fresh": 92.0},
            {"id": "I1", "kind": "ca_keo", "fresh": 25.0},  # ươn
        ]
        shop = ShopSim(tuning, stock=raw_items, money=500, earned=800, reputation=4.0)
        snap = shop.snapshot()

        self.assertIsInstance(snap["stock"], list)
        self.assertEqual(len(snap["stock"]), 3)
        # Snapshot sắp xếp theo ID: I1, I2, I10
        ids = [it["id"] for it in snap["stock"]]
        self.assertEqual(ids, ["I1", "I2", "I10"])

        # Mua nâng cấp oxygen: trừ tiền, tăng cấp
        li = LiveInputs()
        li.set(buy="oxygen")
        evs = shop.step(li.advance())
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0][0], "bought")
        self.assertEqual(shop.money, 300)

        # Đóng shop bằng shop_done
        li.set(shop_done=True)
        evs = shop.step(li.advance())
        self.assertTrue(shop.done)
        self.assertEqual(evs[-1][0], "shop_end")

    def test_02_id_allocator_sequential_across_days(self):
        """Day 1 giữ ID fixture (I5, I2); Day 2 cấp ID mới liên tục (I6, I7) không trùng."""
        tuning = load_tuning()
        streams = Streams(42)
        ids = IdAllocator()
        scenario = {
            "gather": {
                "hold": [
                    {"id": "I5", "kind": "ca_loc", "fresh": 90.0},
                    {"id": "I2", "kind": "bong_sung", "fresh": 80.0}
                ]
            }
        }
        day_sim = DaySim(tuning, scenario, streams, ids, days=2)

        # Day 1: hold ban đầu dùng đúng ID fixture
        d1_hold = day_sim.current_sim.hold
        self.assertEqual([it["id"] for it in d1_hold], ["I5", "I2"])

        # Giả lập kết thúc các pha để sang Day 2
        day_sim.current_sim.done = True
        day_sim.phase = "shop"
        day_sim.current_sim = ShopSim(tuning, stock=[], money=100, earned=100, reputation=3.0)
        day_sim.current_sim.done = True

        li = LiveInputs()
        evs = day_sim.step(li.advance())
        # Đã sang Day 2
        self.assertEqual(day_sim.day, 2)
        d2_hold = day_sim.current_sim.hold
        self.assertEqual(len(d2_hold), 2)
        # ID mới phải tăng tiếp sau I5 (I6, I7)
        self.assertEqual([it["id"] for it in d2_hold], ["I6", "I7"])
        self.assertEqual(d2_hold[0]["kind"], "ca_loc")
        self.assertEqual(d2_hold[1]["kind"], "bong_sung")

    def test_03_phase_transition_events_carry_new_phase_and_day(self):
        """Khi chuyển pha trong cùng tick: phase_start mang đúng pha mới và day mới."""
        tuning = load_tuning()
        streams = Streams(42)
        ids = IdAllocator()
        day_sim = DaySim(tuning, {}, streams, ids, days=2)

        # Đang ở pha gather
        self.assertEqual(day_sim.phase, "gather")
        day_sim.current_sim.done = True  # Giả lập gather kết thúc

        li = LiveInputs()
        evs = day_sim.step(li.advance())

        # Sự kiện phase_start phải mang phase: quan, day: 1
        ps_ev = [ev for ev in evs if ev[0] == "phase_start"]
        self.assertTrue(len(ps_ev) >= 1)
        name, data, phase, day = ps_ev[0]
        self.assertEqual(phase, "quan")
        self.assertEqual(day, 1)

    def test_04_phase_transition_snapshot_at_phase_tick_zero(self):
        """Chạy headless: tại tick chuyển pha, snapshot pha mới được ghi nhận với phase_tick: 0."""
        with Workdir() as w:
            # Tạo kịch bản kết thúc gather ngay tại tick 0 (cập bến)
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [2, 0]},
                    "random_fish": False,
                    "monsters": []
                }
            })
            code, err = run_headless("--mode", "day", "--days", "1", "--seed", "42",
                                     "--scenario", sc, "--inputs", inp, "--ticks", "5",
                                     "--snapshot-every", "10", "--out", w.path("d.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("d.jsonl"))

            # Tìm snapshot của pha quan
            quan_snaps = [r for r in rows if r["type"] == "snapshot" and r.get("phase") == "quan"]
            self.assertTrue(len(quan_snaps) >= 1, "Phải có snapshot ghi lại pha quan")
            # Snapshot đầu tiên của pha quan phải có phase_tick == 0
            self.assertEqual(quan_snaps[0]["phase_tick"], 0)


if __name__ == "__main__":
    unittest.main()
