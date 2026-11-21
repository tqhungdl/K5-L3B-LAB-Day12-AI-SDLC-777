"""Unit tests cho Lát 4 Phase 2 (Người 4 · Integrator: Day, Shop, Pause, Kế hoạch Ngày).

AC-P2-06, AC-P2-07, AC-P2-08.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json
from chonoi.sim.day import resolve_day_plans
from chonoi.sim.shop import ShopSim
from chonoi.inputs import LiveInputs


def load_tuning():
    with open("game.contract.json", encoding="utf-8") as f:
        return json.load(f)["tuning"]


class TestDayAndShop(unittest.TestCase):
    def test_01_resolve_day_plans(self):
        """Kế hoạch D1..D5 tính đúng nguyên liệu từ công thức món."""
        tuning = load_tuning()
        plans = resolve_day_plans(tuning)
        self.assertIn(1, plans)
        self.assertIn(5, plans)
        # D1: ca_loc_nuong_trui x3 (3 ca_loc), goi_bong_sung x3 (6 bong_sung)
        d1 = plans[1]
        self.assertEqual(d1["dishes"]["ca_loc_nuong_trui"], 3)
        self.assertEqual(d1["dishes"]["goi_bong_sung"], 3)
        self.assertEqual(d1["ingredients"]["ca_loc"], 3)
        self.assertEqual(d1["ingredients"]["bong_sung"], 6)

    def test_02_shop_buy_upgrades_and_events(self):
        """Shop nhận buy: 'oxygen', trừ tiền, tăng cấp, phát bought.
        Không đủ tiền -> phát buy_failed (funds). Đạt trần -> buy_failed (max_level).
        """
        tuning = load_tuning()
        shop = ShopSim(tuning, stock={"bong_sung": 2}, money=300, earned=500, reputation=3.0)

        # Mua oxygen cấp 1 giá 200 (còn 100)
        li = LiveInputs()
        li.set(buy="oxygen")
        evs = shop.step(li.advance())
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0][0], "bought")
        self.assertEqual(evs[0][1]["upgrade"], "oxygen")
        self.assertEqual(evs[0][1]["level"], 1)
        self.assertEqual(evs[0][1]["price"], 200)
        self.assertEqual(shop.money, 100)
        self.assertEqual(shop.earned, 500)  # earned giữ nguyên

        # Thử mua tiếp oxygen cấp 2 (giá 400 trong khi còn 100) -> buy_failed (funds)
        li.set(buy="oxygen")
        evs = shop.step(li.advance())
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0][0], "buy_failed")
        self.assertEqual(evs[0][1]["reason"], "funds")

        # Đóng shop bằng shop_done
        li.set(shop_done=True)
        evs = shop.step(li.advance())
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0][0], "shop_end")
        self.assertEqual(evs[0][1]["reason"], "done")
        self.assertTrue(shop.done)

    def test_03_shop_timeout_after_max_ticks(self):
        """Shop không có tương tác sẽ tự đóng sau 600 tick với reason time."""
        tuning = load_tuning()
        shop = ShopSim(tuning, stock={}, money=100, earned=100, reputation=3.0)
        li = LiveInputs()
        for _ in range(599):
            shop.step(li.advance())
            self.assertFalse(shop.done)
        evs = shop.step(li.advance())
        self.assertTrue(shop.done)
        self.assertEqual(evs[-1][0], "shop_end")
        self.assertEqual(evs[-1][1]["reason"], "time")

    def test_04_pause_freezes_gameplay(self):
        """Bấm pause làm game dừng lại, phát paused, snapshot có state: paused.
        Bấm pause lần 2 phát resumed và tiếp tục bước gameplay.
        """
        with Workdir() as w:
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "move": [1, 0]},
                {"tick": 5, "pause": True},
                {"tick": 6, "pause": False},
                {"tick": 10, "pause": True},
                {"tick": 11, "pause": False}
            ))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "20",
                                     "--inputs", inp, "--snapshot-every", "1", "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))

            paused_ev = events(rows, "paused")
            self.assertEqual(len(paused_ev), 1)
            self.assertEqual(paused_ev[0]["tick"], 6)

            resumed_ev = events(rows, "resumed")
            self.assertEqual(len(resumed_ev), 1)
            self.assertEqual(resumed_ev[0]["tick"], 11)

            # Kiểm tra trạng thái snapshot lúc đang pause
            s_map = {s["tick"]: s for s in snapshots(rows)}
            self.assertEqual(s_map[6]["state"], "paused")
            self.assertEqual(s_map[7]["state"], "paused")
            # Tọa độ không đổi khi đang pause (từ tick 6 đến 10)
            self.assertEqual(s_map[6]["player"]["pos"], s_map[10]["player"]["pos"])

    def test_05_day_mode_initial_events_and_snapshot(self):
        """Chạy --mode day: phát day_start, day_plan, phase_start trước snapshot tick 0.
        Snapshot chứa day, day_plan, upgrades, active_upgrades.
        """
        with Workdir() as w:
            code, err = run_headless("--mode", "day", "--days", "1", "--seed", "42",
                                     "--ticks", "10", "--out", w.path("d.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("d.jsonl"))

            # Kiểm tra các sự kiện khởi tạo trước snapshot
            ev_names = [r["name"] for r in rows if r["type"] == "event" and r["tick"] == 0]
            self.assertEqual(ev_names, ["day_start", "day_plan", "phase_start"])

            # Snapshot tick 0 có đầy đủ trường của mode day
            s0 = snapshots(rows)[0]
            self.assertEqual(s0["mode"], "day")
            self.assertEqual(s0["day"], 1)
            self.assertIn("day_plan", s0)
            self.assertIn("upgrades", s0)
            self.assertIn("active_upgrades", s0)


if __name__ == "__main__":
    unittest.main()
