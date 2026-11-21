import io
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from chonoi import headless
from chonoi.errors import BadInput
from chonoi.ids import IdAllocator
from chonoi.rng import Streams
from chonoi.scenario import load_scenario
from chonoi.sim.gather import GatherSim
from chonoi.sim.quan import QuanSim
from helpers import Workdir, write_json
from test_p2_gather_monsters import gather_tuning, monster, step


class PhaseTwoScenarioTest(unittest.TestCase):
    def setUp(self):
        self.tuning = gather_tuning()

    def load(self, obj, mode="day"):
        with Workdir() as work:
            return load_scenario(write_json(work.path("scenario.json"), obj), mode, self.tuning)

    def test_default_blocks_and_standalone_shape(self):
        self.assertEqual(load_scenario(None, "day", self.tuning), {"day": {}, "gather": {}, "quan": {}})
        self.assertEqual(load_scenario(None, "gather", self.tuning), {})
        self.assertEqual(self.load({"gather": {"monsters": []}}, "gather"), {"monsters": []})
        with self.assertRaises(BadInput):
            self.load({"day": {}}, "gather")

    def test_day_rejects_independent_quan_fields_and_invalid_economy(self):
        cases = (
            {"quan": {"stock": {}}}, {"quan": {"reputation": 3}},
            {"day": {"money": 1}}, {"day": {"money": 3, "earned": 2}},
            {"day": {"money": True}}, {"day": {"reputation": 5.1}},
            {"day": {"upgrades": {"oxygen": 3}}}, {"day": {"upgrades": {"oxygen": True}}},
            {"day": {"upgrades": {"unknown": 0}}}, {"day": []}, {"shop": {}},
        )
        for fixture in cases:
            with self.subTest(fixture=fixture), self.assertRaises(BadInput):
                self.load(fixture)

    def test_hold_and_fixture_fish_use_manifest_kinds(self):
        block = {
            "hold": ["ca_keo", "keo_neo"], "random_fish": False,
            "fish": [{"id": "F3", "kind": "ca_keo", "pos": [21, 24], "age_ticks": 119}],
        }
        self.assertEqual(self.load({"gather": block})["gather"], block)
        for age in (-1, True, 1.5):
            with self.subTest(age=age), self.assertRaises(BadInput):
                block["fish"][0]["age_ticks"] = age
                self.load({"gather": block})

    def test_monster_fixture_domains(self):
        sample = monster("M2", [80, 20])
        good = dict(sample, state="recoil", state_ticks_left=1, recoil_dir=[0.6, -0.8])
        self.assertEqual(self.load({"gather": {"monsters": [good]}})["gather"]["monsters"], [good])
        for fields in (
            {"kind": []}, {"kind": "ran"}, {"pos": [0, 9]}, {"waypoints": [[81, 20]]},
            {"waypoints": [[80, 20], [101, 20]]}, {"target_idx": True}, {"target_idx": 2},
            {"state": "unknown"}, {"state": "stunned", "state_ticks_left": 2},
            {"state": "recoil", "recoil_dir": [1, 0]},
            {"state": "recoil", "state_ticks_left": 2},
            {"state": "recoil", "state_ticks_left": 1, "recoil_dir": [0.5, 0]},
            {"state_ticks_left": 1}, {"recoil_dir": [1, 0]}, {"speed": 1},
        ):
            with self.subTest(fields=fields), self.assertRaises(BadInput):
                self.load({"gather": {"monsters": [dict(sample, **fields)]}})
        with self.assertRaises(BadInput):
            self.load({"gather": {"monsters": [sample, sample]}})

    def test_effective_player_limits_are_checked_when_gather_starts(self):
        fixture = {"player": {"hp": 4, "oxygen_ticks": 2700}, "random_fish": False}
        active = {"hp": 1, "oxygen": 1}
        with self.assertRaises(BadInput):
            self.load({"gather": fixture}, "gather")
        day = self.load({"day": {"money": 0, "earned": 200, "upgrades": active}, "gather": fixture})
        with self.assertRaises(BadInput):
            GatherSim(self.tuning, day["gather"], Streams(42), IdAllocator())
        sim = GatherSim(self.tuning, day["gather"], Streams(42), IdAllocator(), active_upgrades=active)
        player = sim.snapshot()["player"]
        self.assertEqual((player["hp"], player["hp_max"]), (4, 4))
        self.assertEqual((player["oxygen_ticks"], player["oxygen_max_ticks"]), (2700, 2700))
        fresh = GatherSim(self.tuning, {}, Streams(42), IdAllocator(), active_upgrades={"hp": 2, "oxygen": 2})
        self.assertEqual((fresh.hp, fresh.oxygen_ticks), (5, 3600))

    def test_quan_fixture_is_checked_against_handed_over_stock_when_built(self):
        fixture = {"quan": {"customers": [{
            "id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
        }]}}
        day = self.load(fixture)
        ids, streams = IdAllocator(), Streams(42)
        sim = GatherSim(self.tuning, {
            "player": {"pos": [60, 24], "hp": 1}, "hold": ["ca_loc"], "random_fish": False,
        }, streams, ids)
        self.assertEqual(step(sim)[-1][1]["reason"], "fainted")
        self.assertEqual(sim.inventory_items(), {})
        with self.assertRaises(BadInput):
            QuanSim(self.tuning, day["quan"], streams, ids, inventory=sim.inventory_items())
        quan = QuanSim(self.tuning, {}, streams, ids, inventory=sim.inventory_items())
        self.assertEqual(quan.snapshot()["stock"], {})

    def test_invalid_monster_returns_cli_code_two_without_replacing_outputs(self):
        with Workdir() as work, patch.object(headless, "load_contract", return_value={"tuning": self.tuning}):
            source = write_json(work.path("scenario.json"), {"gather": {"monsters": [
                monster("M1", [10, 10], state="recoil"),
            ]}})
            out, stock = Path(work.path("out.jsonl")), Path(work.path("stock.json"))
            out.write_bytes(b"existing output")
            stock.write_bytes(b"existing stock")
            with redirect_stderr(io.StringIO()) as stderr:
                code = headless.main([
                    "--mode", "gather", "--seed", "42", "--ticks", "1", "--scenario", source,
                    "--out", str(out), "--inventory-out", str(stock),
                ])
            self.assertEqual(code, 2)
            self.assertIn("state_ticks_left", stderr.getvalue())
            self.assertEqual(out.read_bytes(), b"existing output")
            self.assertEqual(stock.read_bytes(), b"existing stock")
