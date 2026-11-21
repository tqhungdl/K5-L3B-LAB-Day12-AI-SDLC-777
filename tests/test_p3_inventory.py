import json
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.headless import main
from chonoi.ids import IdAllocator
from chonoi.inventory import decay_items, fresh_price, item_rows, new_item, read_inventory, write_inventory
from chonoi.jsonl import dumps
from chonoi.scenario import load_scenario
from helpers import Workdir, write_json


class InventoryV12Test(unittest.TestCase):
    def setUp(self):
        self.manifest = load_contract()
        self.manifest["contract_version"] = "1.2"
        self.tuning = self.manifest["tuning"]
        self.tuning["freshness"] = {
            "initial": 100, "gather_decay_per_s": 0.5, "quan_decay_per_s": 0.25, "spoiled_below": 30,
        }
        self.item = {"id": "I2", "kind": "ca_loc", "fresh": 29.9999}

    def test_manifest_requires_freshness_for_v12(self):
        with Workdir() as work:
            path = write_json(work.path("contract.json"), self.manifest)
            self.assertEqual(load_contract(path), self.manifest)
            self.tuning["freshness"]["initial"] = True
            write_json(path, self.manifest)
            with self.assertRaises(BadInput):
                load_contract(path)

    def test_file_schema_is_versioned_and_rejects_invalid_items(self):
        with Workdir() as work:
            path = write_json(work.path("inventory.json"), {"items": {"ca_loc": 1}})
            self.assertEqual(read_inventory(path), {"ca_loc": 1})
            with self.assertRaises(BadInput):
                read_inventory(path, contract_version="1.2")
            for rows in (
                [self.item, self.item],
                [dict(self.item, id="")],
                [dict(self.item, kind="unknown")],
                [dict(self.item, fresh=True)],
                [dict(self.item, fresh=float("nan"))],
                [dict(self.item, fresh=float("inf"))],
                [dict(self.item, fresh=101)],
                [dict(self.item, extra=0)],
            ):
                with self.subTest(rows=rows), self.assertRaises(BadInput):
                    write_json(path, {"items": rows})
                    read_inventory(path, contract_version="1.2")

    def test_freshness_is_preserved_in_handoff_and_coordinates_still_round(self):
        ids = IdAllocator()
        ids.reserve("I9")
        new = new_item(ids, "ca_keo", 100)
        self.assertEqual(new["id"], "I10")
        almost_spoiled = dict(self.item, fresh=Fraction(30) - Fraction(1, 10**17))
        rows = item_rows([almost_spoiled, new])
        with Workdir() as work:
            path = work.path("inventory.json")
            write_inventory(path, list(reversed(rows)), contract_version="1.2")
            event = json.loads(dumps({"inventory": {"items": [almost_spoiled, new]}, "pos": [1.23456, 0]}))
            self.assertEqual(event["inventory"], json.loads(Path(path).read_text(encoding="utf-8")))
            self.assertEqual(read_inventory(path, contract_version="1.2"), rows)
            self.assertLess(rows[0]["fresh"], 30)
            self.assertEqual(event["pos"], [1.235, 0])

    def test_decay_crosses_once_in_id_order_and_price_uses_exact_average(self):
        rows = [dict(self.item, id=ident, fresh=30) for ident in ("I10", "I2")]
        events = []
        self.assertEqual(decay_items(rows, 0.5, 60, 30, "hold", events), {"I2", "I10"})
        self.assertEqual([event[1]["item_id"] for event in events], ["I2", "I10"])
        self.assertEqual(rows[0]["fresh"], Fraction(30) - Fraction(1, 120))
        self.assertEqual(decay_items(rows, 0.5, 60, 30, "hold", []), set())
        self.assertEqual(fresh_price(60, [dict(self.item, fresh=Fraction(100) - Fraction(1, 120))]), 59)

    def test_scenario_preserves_hold_order_and_missing_reservation(self):
        customer = {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}
        hold = [dict(self.item, id="I10"), self.item]
        with Workdir() as work:
            path = write_json(work.path("day.json"), {
                "gather": {"hold": hold}, "quan": {"customers": [customer]},
            })
            parsed = load_scenario(path, "day", self.tuning, contract_version="1.2")
            self.assertEqual(parsed["gather"]["hold"], hold)
            self.assertNotIn("reserved", parsed["quan"]["customers"][0])
            path = write_json(path, {"quan": {"customers": [dict(customer, reserved=["I2", "I2"])]}})
            with self.assertRaises(BadInput):
                load_scenario(path, "quan", self.tuning, contract_version="1.2")

    def test_headless_rejects_count_file_before_writing_output(self):
        with Workdir() as work, patch("chonoi.headless.load_contract", return_value=self.manifest):
            path = write_json(work.path("inventory.json"), {"items": {"ca_loc": 1}})
            out = work.path("out.jsonl")
            self.assertEqual(main([
                "--mode", "quan", "--seed", "1", "--ticks", "0", "--inventory", path, "--out", out,
            ]), 2)
            self.assertFalse(Path(out).exists())
