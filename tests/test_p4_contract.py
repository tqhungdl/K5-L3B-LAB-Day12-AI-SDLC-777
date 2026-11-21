"""Kiểm tra Test Contract v1.3, tương thích v1.2 và v1.1 lịch sử (AC-P4-01)."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.headless import main
from chonoi.inventory import read_inventory, write_inventory
from helpers import Workdir, events, read_jsonl, snapshots, write_json


class ContractV13Test(unittest.TestCase):
    def setUp(self):
        self.manifest = load_contract()

    def test_01_manifest_v13_fields(self):
        """Manifest chuẩn phải là v1.3, có run_cmd, bench_cmd, soak_cmd và tuning.freshness."""
        self.assertEqual(self.manifest["contract_version"], "1.3")
        self.assertIn("bench_cmd", self.manifest)
        self.assertIn("soak_cmd", self.manifest)
        self.assertIn("run_cmd", self.manifest)
        self.assertTrue(self.manifest["bench_cmd"].startswith("python3 -m chonoi.bench"))
        self.assertTrue(self.manifest["soak_cmd"].startswith("python3 -m chonoi.soak"))
        self.assertTrue(self.manifest["run_cmd"].startswith("python3 -m chonoi.live"))

        freshness = self.manifest["tuning"].get("freshness")
        self.assertIsNotNone(freshness)
        self.assertEqual(freshness["initial"], 100)
        self.assertEqual(freshness["gather_decay_per_s"], 0.5)
        self.assertEqual(freshness["quan_decay_per_s"], 0.25)
        self.assertEqual(freshness["spoiled_below"], 30)

    def test_02_v13_rejects_count_inventory_with_code_2(self):
        """v1.3 từ chối file kho đếm với mã lỗi 2 (AC-P4-01)."""
        with Workdir() as work:
            inv_path = write_json(work.path("inv_count.json"), {"items": {"ca_loc": 2}})
            out_path = work.path("out.jsonl")
            code = main([
                "--mode", "quan", "--seed", "42", "--ticks", "0",
                "--inventory", inv_path, "--out", out_path,
            ])
            self.assertEqual(code, 2)
            self.assertFalse(Path(out_path).exists())

    def test_03_v13_accepts_individual_inventory(self):
        """v1.3 chấp nhận kho cá thể có {id, kind, fresh} (AC-P4-01)."""
        with Workdir() as work:
            items = [{"id": "I1", "kind": "ca_loc", "fresh": 100.0}]
            inv_path = write_json(work.path("inv_ind.json"), {"items": items})
            out_path = work.path("out.jsonl")
            code = main([
                "--mode", "quan", "--seed", "42", "--ticks", "0",
                "--inventory", inv_path, "--out", out_path,
            ])
            self.assertEqual(code, 0)
            self.assertTrue(Path(out_path).exists())

    def test_04_v13_spoiled_at_tick_1(self):
        """Hàng có độ tươi 30 phát sự kiện spoiled ở tick 1 khi sang Quán."""
        with Workdir() as work:
            items = [{"id": "I1", "kind": "ca_loc", "fresh": 30.0}]
            inv_path = write_json(work.path("inv_spoiled.json"), {"items": items})
            out_path = work.path("out.jsonl")
            code = main([
                "--mode", "quan", "--seed", "42", "--ticks", "1",
                "--inventory", inv_path, "--out", out_path,
            ])
            self.assertEqual(code, 0)
            rows = read_jsonl(out_path)
            spoiled_events = events(rows, "spoiled")
            self.assertEqual(len(spoiled_events), 1)
            self.assertEqual(spoiled_events[0]["data"]["item_id"], "I1")
            self.assertEqual(spoiled_events[0]["data"]["kind"], "ca_loc")
            self.assertEqual(spoiled_events[0]["data"]["location"], "stock")

    def test_05_v12_v13_jsonl_parity(self):
        """Cùng fixture tại v1.2 và v1.3 cho ra cùng JSONL kết quả."""
        with Workdir() as work:
            items = [{"id": "I1", "kind": "ca_loc", "fresh": 90.0}]
            inv_path = write_json(work.path("inv.json"), {"items": items})
            out_v13 = work.path("out_v13.jsonl")
            code13 = main([
                "--mode", "quan", "--seed", "42", "--ticks", "60",
                "--inventory", inv_path, "--out", out_v13,
            ])
            self.assertEqual(code13, 0)
            out_v12 = work.path("out_v12.jsonl")
            with patch("chonoi.headless.load_contract", return_value=dict(self.manifest, contract_version="1.2")):
                self.assertEqual(main([
                    "--mode", "quan", "--seed", "42", "--ticks", "60",
                    "--inventory", inv_path, "--out", out_v12,
                ]), 0)
            self.assertEqual(Path(out_v12).read_bytes(), Path(out_v13).read_bytes())

            # Test v1.2 via read/write_inventory directly
            read_12 = read_inventory(inv_path, contract_version="1.2")
            read_13 = read_inventory(inv_path, contract_version="1.3")
            self.assertEqual(read_12, read_13)

            out_inv_12 = work.path("inv_12.json")
            out_inv_13 = work.path("inv_13.json")
            write_inventory(out_inv_12, items, contract_version="1.2")
            write_inventory(out_inv_13, items, contract_version="1.3")
            self.assertEqual(
                Path(out_inv_12).read_text(encoding="utf-8"),
                Path(out_inv_13).read_text(encoding="utf-8"),
            )

    def test_06_v11_historical_contract_still_functional(self):
        """Manifest v1.1 cũ vẫn đọc kho đếm bình thường qua tham số contract_version."""
        with Workdir() as work:
            inv_path = write_json(work.path("inv_v11.json"), {"items": {"ca_loc": 2}})
            read_11 = read_inventory(inv_path, contract_version="1.1")
            self.assertEqual(read_11, {"ca_loc": 2})

    def test_day_exports_remaining_individual_stock_in_shop_snapshot(self):
        with Workdir() as work:
            scenario = write_json(work.path("day.json"), {
                "gather": {"time_left_ticks": 1, "hold": [{"id": "I1", "kind": "ca_loc", "fresh": 95}]},
                "quan": {"time_left_ticks": 2, "random_customers": False},
            })
            output = work.path("out.jsonl")
            self.assertEqual(main([
                "--mode", "day", "--seed", "42", "--ticks", "5",
                "--scenario", scenario, "--out", output,
            ]), 0)
            rows = read_jsonl(output)
            quan = next(row for row in snapshots(rows) if row["phase"] == "quan")
            self.assertEqual(quan["stock"], events(rows, "gather_end")[0]["data"]["inventory"]["items"])
            shop = [row for row in snapshots(rows) if row["phase"] == "shop"]
            self.assertEqual(shop[0]["phase_tick"], 0)
            item, = shop[0]["stock"]
            self.assertEqual(set(item), {"id", "kind", "fresh"})
            self.assertEqual((item["id"], item["kind"]), ("I1", "ca_loc"))
            self.assertAlmostEqual(item["fresh"], 95 - 1 / 60)
            self.assertEqual(shop[-1]["stock"], shop[0]["stock"])

            out_inv_11 = work.path("inv_v11_out.json")
            write_inventory(out_inv_11, {"ca_loc": 2}, contract_version="1.1")
            self.assertEqual(
                json.loads(Path(out_inv_11).read_text(encoding="utf-8")),
                {"items": {"ca_loc": 2}},
            )
