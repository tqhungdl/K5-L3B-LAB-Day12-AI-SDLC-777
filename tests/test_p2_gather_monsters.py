import json
import unittest
from pathlib import Path
from unittest.mock import patch

from chonoi import headless
from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.sim import gather_resources
from chonoi.sim.gather import GatherSim
from helpers import Workdir, events, frames, read_jsonl, snapshots, write_json


def monster(ident, pos, **fields):
    return {
        "id": ident, "kind": "ca_sau", "pos": list(pos),
        "waypoints": [list(pos), [pos[0] + 4, pos[1]]], **fields,
    }


def gather_tuning():
    tuning = load_contract()["tuning"]
    gather = tuning["gather"]
    # Fixture dùng độc lập với các lát dữ liệu cá và Shop.
    gather["fish_initial"] = []
    gather["fish_yield"]["ca_keo"] = 2
    if all(node["kind"] != "keo_neo" for node in gather["nodes"]):
        gather["nodes"].append({"id": "N5", "kind": "keo_neo", "pos": [76, 0]})
    gather["monsters"] = {
        "species": {"ca_sau": {
            "patrol_speed": 1.0, "chase_speed": 3.0, "detect_radius": 10,
            "exit_radius": 16, "depths": [10, 30], "hit_radius": 1.5,
            "recoil_ticks": 60, "recoil_dist": 2,
        }},
        "spawns": [
            monster("M1", [60, 24], from_day=1),
            monster("M2", [85, 18], from_day=3),
        ],
        "invuln_ticks": 90,
        "loss_ratio": 0.5,
    }
    tuning["shop"] = {"upgrades": {
        "oxygen": [{"level": 1, "oxygen_max_s": 45}, {"level": 2, "oxygen_max_s": 60}],
        "hp": [{"level": 1, "hp_max": 4}, {"level": 2, "hp_max": 5}],
    }}
    return tuning


def step(sim, *edges):
    return sim.step(InputState((0.0, 0.0), {}, set(edges)))


class GatherMonstersTest(unittest.TestCase):
    def setUp(self):
        self.tuning = gather_tuning()

    def sim(self, scenario=None, **options):
        fixture = {"random_fish": False, **(scenario or {})}
        return GatherSim(self.tuning, fixture, Streams(42), IdAllocator(), **options)

    def test_default_spawns_repeat_by_day_and_fixture_empty_overrides(self):
        ids = IdAllocator()
        for day, expected in ((1, ["M1"]), (2, ["M1"]), (3, ["M1", "M2"]), (5, ["M1", "M2"])):
            with self.subTest(day=day):
                sim = GatherSim(self.tuning, {}, Streams(42), ids, day_number=day)
                self.assertEqual([m["id"] for m in sim.monsters], expected)
                self.assertEqual(sim.monsters[0]["pos"], [60, 24])
                step(sim)
        self.assertEqual(ids.new("M"), "M3")
        self.assertEqual(self.sim({"monsters": []}, day_number=5).snapshot()["monsters"], [])

    def test_patrol_reaches_waypoint_before_turning(self):
        sim = self.sim()
        croc = sim.monsters[0]
        for _ in range(239):
            step(sim)
        self.assertEqual(croc["target_idx"], 1)
        step(sim)
        self.assertEqual(croc["pos"], [64, 24])
        self.assertEqual(croc["target_idx"], 0)
        step(sim)
        self.assertAlmostEqual(croc["pos"][0], 64 - 1 / sim.tick_hz)

    def test_detection_threshold_depth_and_chase_hysteresis(self):
        for initial, player, expected in (
            ("patrol", [20, 10], "chase"), ("patrol", [20.01, 10], "patrol"),
            ("chase", [26, 10], "chase"), ("chase", [26.01, 10], "patrol"),
            ("chase", [11, 9.99], "patrol"),
        ):
            with self.subTest(initial=initial, player=player):
                sim = self.sim({"player": {"pos": player}, "monsters": [
                    monster("M1", [10, 10], state=initial),
                ]})
                self.assertEqual(step(sim), [])
                croc = sim.monsters[0]
                self.assertEqual(croc["state"], expected)
                speed = 3 if expected == "chase" else 1
                self.assertAlmostEqual(croc["pos"][0], 10 + speed / sim.tick_hz)

    def test_hit_breaks_tie_by_numeric_id_and_drops_lifo(self):
        sim = self.sim({
            "player": {"pos": [50, 24]},
            "monsters": [monster("M10", [50, 24]), monster("M2", [50, 24])],
            "hold": ["ca_loc", "bong_sung", "ca_linh", "keo_neo", "ca_keo"],
        })
        actual = step(sim)
        self.assertEqual(actual, [("monster_hit", {
            "monster_id": "M2", "hp": 2, "lost": ["ca_keo", "keo_neo"], "pos": [50, 24],
        })])
        self.assertEqual(sim.hold, ["ca_loc", "bong_sung", "ca_linh"])
        self.assertEqual(sim.invuln_ticks, 90)
        hit, other = sim.monsters
        self.assertEqual((hit["state"], hit["state_ticks_left"], hit["recoil_dir"]),
                         ("recoil", 60, [1.0, 0.0]))
        self.assertEqual(other["state"], "chase")
        initial_snapshot = sim.snapshot()
        for _ in range(59):
            self.assertEqual(step(sim), [])
        self.assertEqual(hit["state_ticks_left"], 1)
        self.assertEqual(step(sim), [])
        self.assertEqual(hit["state"], "patrol")
        self.assertAlmostEqual(hit["pos"][0], 52)
        self.assertEqual(initial_snapshot["monsters"][0]["state_ticks_left"], 60)
        for _ in range(29):
            self.assertEqual(step(sim), [])
        self.assertEqual(sim.invuln_ticks, 1)
        self.assertEqual(step(sim)[0][1]["monster_id"], "M10")

    def test_hit_at_radius_after_motion_and_recoil_at_boundary(self):
        sim = self.sim({
            "player": {"pos": [21.55, 10]},
            "monsters": [monster("M1", [20, 10])],
        })
        self.assertEqual(step(sim)[0][0], "monster_hit")

        sim = self.sim({
            "player": {"pos": [100, 10]},
            "monsters": [monster("M1", [100, 10], waypoints=[[100, 10], [99, 10]],
                                 state="recoil", state_ticks_left=1, recoil_dir=[1, 0])],
        })
        self.assertEqual(step(sim), [])
        self.assertEqual(sim.monsters[0]["pos"], [100, 10])
        self.assertEqual(sim.monsters[0]["state"], "patrol")
        self.assertEqual(step(sim)[0][0], "monster_hit")

    def test_choke_precedes_hit_and_faint_precedes_end_of_time(self):
        fixture = {
            "player": {"pos": [50, 24], "hp": 2, "oxygen_ticks": 1, "zero_oxy_ticks": 0},
            "monsters": [monster("M1", [50, 24])],
            "hold": ["ca_loc", "bong_sung", "ca_keo"], "time_left_ticks": 1,
        }
        for hp, invuln, names, final in (
            (1, 2, ["choke", "faint", "gather_end"], "choke"),
            (2, 0, ["choke", "monster_hit", "faint", "gather_end"], "monster"),
            (2, 2, ["choke", "gather_end"], None),
        ):
            with self.subTest(hp=hp, invuln=invuln):
                fixture["player"].update(hp=hp, invuln_ticks=invuln, oxygen_ticks=0, zero_oxy_ticks=59)
                sim = self.sim(fixture)
                rows = step(sim, "catch")
                self.assertEqual([name for name, _ in rows], names)
                if final:
                    lost = ["ca_keo", "bong_sung", "ca_loc"] if final == "choke" else ["bong_sung", "ca_loc"]
                    self.assertEqual(rows[-2][1], {"hp": 0, "lost": lost, "cause": final})
                    self.assertEqual(rows[-1][1], {"reason": "fainted", "inventory": {"items": {}}})
                else:
                    self.assertEqual(rows[-1][1]["reason"], "time")
                    self.assertEqual(sim.hold, fixture["hold"])

    def test_dynamic_fish_hook_runs_after_catch_only_while_shift_is_active(self):
        self.tuning["gather"]["fish_initial"] = 8
        fish = {"id": "F1", "kind": "ca_keo", "pos": [15, 24], "heading_deg": 0, "age_ticks": 7}
        scenario = {"player": {"pos": [15, 24]}, "monsters": [], "fish": [fish]}

        def verify_caught_before_advance(sim, phase_tick, rows):
            self.assertEqual(sim.fish, [])
            self.assertEqual([name for name, _ in rows], ["fish_caught"])

        with (
            patch.object(gather_resources, "init_fish", side_effect=lambda sim, fixture: fixture["fish"].copy(),
                         create=True),
            patch.object(gather_resources, "advance_fish", side_effect=verify_caught_before_advance,
                         create=True) as advance,
        ):
            sim = self.sim(dict(scenario, random_fish=True, time_left_ticks=2))
            self.assertEqual(sim.snapshot()["fish"][0]["age_ticks"], 7)
            rows = step(sim, "catch")
            self.assertEqual([name for name, _ in rows], ["fish_caught"])
            self.assertEqual(sim.fish, [])
            advance.assert_called_once_with(sim, 1, rows)
            step(sim)
            advance.assert_called_once()
            sim = self.sim(scenario)
            self.assertEqual(step(sim), [])
            advance.assert_called_once()

    def test_headless_harvest_catch_and_faint_inventory_are_deterministic(self):
        cases = (
            ({"player": {"pos": [76, 0]}}, "interact", ["gather", "gather_end"], {"keo_neo": 1}),
            ({"player": {"pos": [15, 24]}, "fish": [
                {"id": "F1", "kind": "ca_keo", "pos": [15, 24], "age_ticks": 7},
             ]}, "catch", ["fish_caught", "gather_end"], {"ca_keo": 2}),
            ({"player": {"pos": [60, 24], "hp": 1}, "monsters": [monster("M1", [60, 24])],
              "hold": ["ca_keo"]}, "catch", ["monster_hit", "faint", "gather_end"], {}),
        )
        with patch.object(headless, "load_contract", return_value={"tuning": self.tuning}):
            for fixture, button, names, items in cases:
                with self.subTest(button=button, names=names), Workdir() as work:
                    source = write_json(work.path("scenario.json"), {"gather": {
                        "random_fish": False, "monsters": [], "time_left_ticks": 1, **fixture,
                    }})
                    inputs = write_json(work.path("inputs.json"), frames({"tick": 0, button: True}))
                    results = []
                    for run in range(2):
                        out = Path(work.path(f"gather-{run}.jsonl"))
                        inventory = Path(work.path(f"stock-{run}.json"))
                        self.assertEqual(headless.main([
                            "--mode", "gather", "--seed", "42", "--ticks", "1",
                            "--scenario", source, "--inputs", inputs, "--out", str(out),
                            "--inventory-out", str(inventory),
                        ]), 0)
                        rows = read_jsonl(out)
                        self.assertEqual([row["name"] for row in events(rows)], names)
                        self.assertEqual(events(rows, "gather_end")[0]["data"]["inventory"], {"items": items})
                        self.assertEqual(json.loads(inventory.read_bytes()), {"items": items})
                        self.assertEqual(snapshots(rows)[0]["phase_tick"], 0)
                        results.append((out.read_bytes(), inventory.read_bytes()))
                    self.assertEqual(*results)
