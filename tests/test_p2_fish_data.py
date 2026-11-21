import json
import math
import unittest
from pathlib import Path

from chonoi.contract import load_contract
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.runner import build_sim
from chonoi.sim.day import resolve_day_plans
from helpers import Workdir, events, read_jsonl, run_headless, snapshots, write_json


class FishDataTest(unittest.TestCase):
    def setUp(self):
        self.contract = load_contract()
        self.tuning = self.contract["tuning"]
        self.idle = InputState((0, 0), {}, set())

    def gather(self, seed=42, **scenario):
        return build_sim("gather", self.tuning, {"monsters": [], **scenario}, seed, None)

    def test_default_data_and_day_plans(self):
        expected_version = "1.2" if "freshness" in self.tuning else "1.1"
        self.assertEqual(self.contract["contract_version"], expected_version)
        self.assertEqual(len(self.tuning["menu"]), 6)
        self.assertEqual(len(self.tuning["quan"]["stoves"]), 2)
        self.assertEqual(len(self.tuning["quan"]["tables"]), 4)
        self.assertEqual(resolve_day_plans(self.tuning), {
            plan["day"]: {"dishes": plan["dishes"], "ingredients": plan["ingredients"]}
            for plan in self.tuning["day_plan"]
        })

    def test_seeded_initial_positions_and_periodic_population_cap(self):
        sim = self.gather()
        self.assertEqual(sim.fish, self.gather().fish)
        self.assertNotEqual(sim.fish, self.gather(seed=43).fish)
        self.assertEqual(len({tuple(fish["pos"]) for fish in sim.fish}), 8)
        spawn_ticks = []
        for tick in range(1, 1801):
            for name, data in sim.step(self.idle):
                if name == "fish_spawned":
                    spawn_ticks.append(tick)
                    school = next(fish for fish in sim.fish if fish["id"] == data["id"])
                    self.assertEqual(school["age_ticks"], 0)
                    self.assertTrue(all(
                        math.dist(data["pos"], fish["pos"]) > 1
                        for fish in sim.fish if fish is not school
                    ))
        self.assertEqual(spawn_ticks, [360, 720, 1080, 1440])
        self.assertEqual(len(sim.fish), 12)

    def test_corner_reflection_and_turn_before_movement(self):
        fixture = {"id": "F9", "kind": "ca_keo", "pos": [95.99, 27.99], "heading_deg": 45}
        sim = self.gather(fish=[fixture])
        sim.step(self.idle)
        school = sim.fish[0]
        delta = 0.025 / math.sqrt(2)
        self.assertAlmostEqual(school["pos"][0], 96.01 - delta)
        self.assertAlmostEqual(school["pos"][1], 28.01 - delta)
        self.assertAlmostEqual(school["heading_deg"], 225)

        sim = self.gather(fish=[dict(fixture, pos=[45, 24], age_ticks=119)])
        sim.step(self.idle)
        school = sim.fish[0]
        heading = Streams(42).get("fish_turn").random() * 360
        self.assertEqual(school["age_ticks"], 120)
        self.assertEqual(school["heading_deg"], heading)
        self.assertAlmostEqual(school["pos"][0], 45 + 0.025 * math.cos(math.radians(heading)))

    def test_fixed_fixture_and_next_spawn_id(self):
        fish = [{"id": "F20", "kind": "ca_keo", "pos": [45, 24], "age_ticks": 119}]
        fixed = self.gather(random_fish=False, fish=fish)
        moving = self.gather(fish=fish)
        for _ in range(360):
            self.assertEqual(fixed.step(self.idle), [])
            rows = moving.step(self.idle)
        self.assertEqual(fixed.fish[0]["pos"], [45, 24])
        self.assertEqual(fixed.fish[0]["age_ticks"], 119)
        self.assertEqual(rows[0][0], "fish_spawned")
        self.assertEqual(rows[0][1]["id"], "F21")
        self.assertEqual(self.gather(random_fish=False).fish, [])

    def test_standalone_inventory_handoff_with_new_ingredients(self):
        individual_items = self.contract["contract_version"] == "1.2"
        hold = [{"id": "I1", "kind": "keo_neo", "fresh": 100}] if individual_items else ["keo_neo"]
        with Workdir() as work:
            source = write_json(work.path("scenario.json"), {"gather": {
                "player": {"pos": [45, 24]}, "hold": hold, "time_left_ticks": 1,
                "fish": [{"id": "F1", "kind": "ca_keo", "pos": [45, 24]}],
                "random_fish": False, "monsters": [],
            }})
            inputs = write_json(work.path("inputs.json"), {"frames": [{"tick": 0, "catch": True}]})
            gathered = work.path("gather.jsonl")
            inventory = work.path("catch.json")
            code, error = run_headless(
                "--mode", "gather", "--seed", "42", "--ticks", "1", "--scenario", source,
                "--inputs", inputs, "--out", gathered, "--inventory-out", inventory,
            )
            self.assertEqual(code, 0, error)
            expected = json.loads(Path(inventory).read_text(encoding="utf-8"))["items"]
            if individual_items:
                self.assertEqual([(item["id"], item["kind"]) for item in expected],
                                 [("I1", "keo_neo"), ("I2", "ca_keo"), ("I3", "ca_keo")])
                decay = self.tuning["freshness"]["gather_decay_per_s"] / self.tuning["tick_hz"]
                self.assertAlmostEqual(expected[0]["fresh"], 100 - decay, delta=0.01)
                self.assertEqual([item["fresh"] for item in expected[1:]], [100, 100])
            else:
                self.assertEqual(expected, {"ca_keo": 2, "keo_neo": 1})
            self.assertEqual(events(read_jsonl(gathered), "gather_end")[0]["data"]["inventory"], {"items": expected})
            quan = work.path("quan.jsonl")
            code, error = run_headless(
                "--mode", "quan", "--seed", "42", "--ticks", "0", "--inventory", inventory, "--out", quan,
            )
            self.assertEqual(code, 0, error)
            self.assertEqual(snapshots(read_jsonl(quan))[0]["stock"], expected)
