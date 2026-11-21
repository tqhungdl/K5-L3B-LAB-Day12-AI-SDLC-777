"""Unit & integration tests cho Phase 4 · Nhiệm vụ 3 (Soak headless 10 Ngày)."""

import copy
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from helpers import Workdir, run_headless
from chonoi.ids import IdAllocator
from chonoi.inputs import LiveInputs
from chonoi.rng import Streams
from chonoi.runner import Session
from chonoi.sim.day import DaySim
from chonoi.sim.shop import ShopSim
from chonoi.soak import run_soak


def load_contract_data():
    with open("game.contract.json", encoding="utf-8") as f:
        return json.load(f)


def run_soak_cli(*args):
    cmd = [sys.executable, "-m", "chonoi.soak", *args]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


class TestPhase4Soak(unittest.TestCase):
    def test_01_soak_10_days_cli_and_determinism(self):
        """Chạy CLI soak 10 Ngày với seed 7 hai lần: đủ 10 kết quả, crashes=0, gameplay lặp y hệt."""
        with Workdir() as w:
            out1 = w.path("soak1.json")
            out2 = w.path("soak2.json")

            code1, _, err1 = run_soak_cli("--seed", "7", "--days", "10", "--out", out1)
            self.assertEqual(code1, 0, err1)
            code2, _, err2 = run_soak_cli("--seed", "7", "--days", "10", "--out", out2)
            self.assertEqual(code2, 0, err2)

            with open(out1, encoding="utf-8") as f:
                data1 = json.load(f)
            with open(out2, encoding="utf-8") as f:
                data2 = json.load(f)

            self.assertEqual(
                set(data1.keys()),
                {"days", "days_completed", "crashes", "results", "duration_s"},
            )
            self.assertEqual(data1["days"], 10)
            self.assertEqual(data1["days_completed"], 10)
            self.assertEqual(data1["crashes"], 0)
            self.assertIsInstance(data1["duration_s"], (int, float))
            self.assertGreaterEqual(data1["duration_s"], 0.0)
            self.assertEqual(len(data1["results"]), 10)

            days_list = [r["day"] for r in data1["results"]]
            self.assertEqual(days_list, list(range(1, 11)))
            for row in data1["results"]:
                self.assertEqual(set(row.keys()), {"day", "earned", "reputation", "score"})

            # Bot phải thực sự kiếm tiền qua 10 ngày và earned không giảm
            earned_seq = [r["earned"] for r in data1["results"]]
            self.assertGreater(earned_seq[-1], 0)
            self.assertEqual(earned_seq, sorted(earned_seq))

            # So tính tất định ở mọi trường gameplay (bỏ duration_s)
            g1 = {k: v for k, v in data1.items() if k != "duration_s"}
            g2 = {k: v for k, v in data2.items() if k != "duration_s"}
            self.assertEqual(g1, g2)

    def test_02_soak_10_days_with_v13_freshness_fixture(self):
        """Soak 10 Ngày tương thích hoàn toàn với tuning.freshness (kho cá thể v1.2/v1.3)."""
        contract = load_contract_data()
        tuning = copy.deepcopy(contract["tuning"])
        tuning["freshness"] = {
            "initial": 100,
            "gather_decay_per_s": 0.5,
            "quan_decay_per_s": 0.25,
            "spoiled_below": 30,
        }
        # Rút ngắn thời lượng ca trong unit test để kiểm nhanh kho cá thể xuyên 10 Ngày
        tuning["gather"]["duration_s"] = 60
        tuning["quan"]["duration_s"] = 60

        payload, err = run_soak(7, 10, tuning=tuning, contract_version="1.3")
        self.assertIsNone(err)
        self.assertEqual(payload["days"], 10)
        self.assertEqual(payload["days_completed"], 10)
        self.assertEqual(payload["crashes"], 0)
        self.assertEqual([r["day"] for r in payload["results"]], list(range(1, 11)))
        self.assertGreater(payload["results"][-1]["earned"], 0)

    def test_03_day_6_to_10_repeat_plans_and_keep_continuous_ids_and_state(self):
        """Ngày 6–10 lặp kế hoạch D1–D5, giữ tiền/nâng cấp/uy tín và cấp ID cá thể liên tục I1..I10."""
        contract = load_contract_data()
        tuning = copy.deepcopy(contract["tuning"])
        tuning["freshness"] = {
            "initial": 100,
            "gather_decay_per_s": 0.5,
            "quan_decay_per_s": 0.25,
            "spoiled_below": 30,
        }
        scenario = {
            "day": {"money": 500, "earned": 500, "reputation": 3.5},
            "gather": {
                "hold": [{"id": "I1", "kind": "ca_loc", "fresh": 100.0}],
                "random_fish": False,
                "monsters": [],
            },
        }
        sess = Session(
            "day", tuning, scenario, seed=7, days=10,
            contract_version="1.3", allow_extended_days=True,
        )
        day_sim = sess.sim
        self.assertEqual(day_sim.days, 10)

        seen_plans = {}
        seen_hold_ids = []
        li = LiveInputs()

        for expected_day in range(1, 11):
            self.assertEqual(day_sim.day, expected_day)
            seen_plans[expected_day] = day_sim.day_plan["dishes"]
            seen_hold_ids.append(day_sim.current_sim.hold[0]["id"])

            # Chuyển thẳng sang Shop để kiểm tra đóng shop và nối sang Ngày tiếp theo
            day_sim.phase = "shop"
            day_sim.current_sim = ShopSim(
                tuning,
                stock=[],
                money=day_sim.money,
                earned=day_sim.earned,
                reputation=day_sim.reputation,
                upgrades=day_sim.upgrades,
            )
            if expected_day == 1:
                # Mua nâng cấp oxygen cấp 1 ở Ngày 1 và kiểm duy trì xuyên 10 Ngày
                li.set(buy="oxygen", shop_done=False)
                day_sim.step(li.advance())
                li.set(buy=None, shop_done=True)
            else:
                li.set(shop_done=False)
                li.advance()
                li.set(shop_done=True)

            evs = day_sim.step(li.advance())
            shop_ends = [ev for ev in evs if ev[0] == "shop_end"]
            self.assertEqual(len(shop_ends), 1)
            # Event shop_end phải mang đúng số ngày vừa đóng ngay cả khi Ngày kế vừa được dựng
            self.assertEqual(shop_ends[0][3], expected_day)

        self.assertTrue(day_sim.done)
        self.assertEqual(day_sim.reason, "days_complete")
        self.assertEqual(day_sim.days_completed, 10)
        self.assertEqual(day_sim.upgrades.get("oxygen"), 1)
        self.assertEqual(day_sim.active_upgrades.get("oxygen"), 1)
        self.assertEqual(day_sim.money, 300)
        self.assertEqual(day_sim.earned, 500)
        self.assertEqual(day_sim.reputation, 3.5)

        # Kế hoạch Ngày 6..10 lặp lại đúng Ngày 1..5
        for d in range(1, 6):
            self.assertEqual(seen_plans[d + 5], seen_plans[d])

        # ID cá thể liên tục I1..I10 không reset
        self.assertEqual(seen_hold_ids, [f"I{i}" for i in range(1, 11)])

    def test_04_cli_validation_and_regular_headless_limit(self):
        """soak --days 0 trả mã 2 (không ghi file); headless --mode day --days 6 vẫn trả mã 2."""
        with Workdir() as w:
            bad_out = w.path("should_not_exist.json")
            code, _, err = run_soak_cli("--seed", "7", "--days", "0", "--out", bad_out)
            self.assertEqual(code, 2, err)
            self.assertFalse(os.path.exists(bad_out))

            code_neg, _, err_neg = run_soak_cli("--seed", "7", "--days", "-3", "--out", bad_out)
            self.assertEqual(code_neg, 2, err_neg)
            self.assertFalse(os.path.exists(bad_out))

            hl_out = w.path("hl.jsonl")
            hl_code, hl_err = run_headless(
                "--mode", "day", "--days", "6", "--seed", "7", "--ticks", "10", "--out", hl_out
            )
            self.assertEqual(hl_code, 2, hl_err)
            self.assertFalse(os.path.exists(hl_out))


if __name__ == "__main__":
    unittest.main()
