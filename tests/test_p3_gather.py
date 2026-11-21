import json
import unittest

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.runner import Session
from chonoi.sim.gather import GatherSim


def item(ident, kind="ca_linh", fresh=100):
    return {"id": ident, "kind": kind, "fresh": fresh}


def controls(*edges):
    return InputState((0, 0), {}, set(edges))


class GatherFreshnessTest(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]
        self.tuning["freshness"] = {
            "initial": 100, "gather_decay_per_s": 0.5,
            "quan_decay_per_s": 0.25, "spoiled_below": 30,
        }
        self.gather = self.tuning["gather"]
        self.decay = self.tuning["freshness"]["gather_decay_per_s"] / self.tuning["tick_hz"]

    def sim(self, *, ids=None, **scenario):
        fixture = {"random_fish": False, "monsters": [], **scenario}
        return GatherSim(self.tuning, fixture, Streams(42), ids or IdAllocator())

    def test_harvest_reserves_fixture_ids_and_starts_decay_next_step(self):
        fixture = [item("I10"), item("I2", "ca_loc", 31)]
        node = next(row for row in self.gather["nodes"] if row["kind"] == "keo_neo")
        sim = self.sim(hold=fixture, player={"pos": node["pos"]})

        self.assertEqual(sim.snapshot()["hold"], fixture)
        self.assertEqual(sim.inventory_items(), list(reversed(fixture)))
        self.assertEqual(sim.step(controls("interact"))[0][0], "gather")
        snapshot = sim.snapshot()["hold"]
        self.assertEqual(snapshot[-1], item("I11", "keo_neo"))
        self.assertAlmostEqual(snapshot[0]["fresh"], 100 - self.decay)

        sim.step(controls())
        self.assertAlmostEqual(sim.snapshot()["hold"][-1]["fresh"], 100 - self.decay)
        self.assertEqual(snapshot[-1]["fresh"], 100)
        self.assertEqual(fixture, [item("I10"), item("I2", "ca_loc", 31)])
        inventory = sim.inventory_items()
        inventory[0]["fresh"] = 0
        self.assertGreater(sim.inventory_items()[0]["fresh"], 0)

    def test_catch_needs_room_for_entire_yield_and_does_not_spend_ids(self):
        pos = [15, 5]
        school = {"id": "F1", "kind": "ca_linh", "pos": pos}
        capacity = self.gather["hold_capacity"]
        amount = self.gather["fish_yield"]["ca_linh"]
        fixture = [item(f"I{n}", fresh=0) for n in range(1, capacity - amount + 2)]
        sim = self.sim(hold=fixture, fish=[school], player={"pos": pos})

        self.assertEqual(sim.step(controls("catch")), [
            ("hold_full", {"action": "catch", "fish_id": "F1", "required": amount, "free": amount - 1}),
        ])
        self.assertEqual(sim.snapshot()["hold"], fixture)
        self.assertEqual([fish["id"] for fish in sim.fish], ["F1"])
        self.assertEqual(sim.catch_cd_ticks, 0)

        sim._drop_from_hold(1)
        self.assertEqual(sim.step(controls("catch"))[0][0], "fish_caught")
        next_id = len(fixture) + 1
        self.assertEqual(sim.snapshot()["hold"][-amount:], [
            item(f"I{n}") for n in range(next_id, next_id + amount)
        ])
        self.assertEqual(sim.snapshot()["hold_count"], capacity)

    def test_spoiled_is_once_in_id_order_and_zero_is_lower_bound(self):
        sim = self.sim(hold=[item("I10", fresh=30), item("I2", fresh=30), item("I1", fresh=0.001)])
        self.assertEqual(sim.step(controls()), [
            ("spoiled", {"item_id": ident, "kind": "ca_linh", "location": "hold"})
            for ident in ("I2", "I10")
        ])
        self.assertEqual(sim.step(controls()), [])
        rows = sim.snapshot()["hold"]
        self.assertEqual([row["id"] for row in rows], ["I10", "I2", "I1"])
        self.assertEqual(rows[-1]["fresh"], 0)
        self.assertAlmostEqual(rows[0]["fresh"], 30 - 2 * self.decay)

    def test_export_keeps_values_on_correct_side_of_threshold(self):
        sim = self.sim(hold=[
            item("I1", fresh=30.008333333333336),
            item("I2", fresh=30.008333333333333),
        ])
        events = sim.step(controls("interact"))
        self.assertEqual([(name, data.get("item_id")) for name, data in events],
                         [("spoiled", "I2"), ("gather_end", None)])
        inventory = events[-1][1]["inventory"]
        self.assertEqual(inventory["items"], sim.inventory_items())
        above, below = json.loads(json.dumps(inventory))["items"]
        self.assertGreaterEqual(above["fresh"], 30)
        self.assertLess(below["fresh"], 30)

        exact = self.sim(hold=[item("I1", fresh=30.025)])
        for _ in range(3):
            self.assertEqual(exact.step(controls()), [])
        self.assertEqual(exact.snapshot()["hold"][0]["fresh"], 30)
        self.assertEqual(exact.step(controls())[0][0], "spoiled")

    def test_pause_freezes_age_and_resume_crosses_threshold(self):
        session = Session("gather", self.tuning, {
            "hold": [item("I1", fresh=30)], "random_fish": False, "monsters": [],
        }, 42)
        self.assertEqual([event["name"] for event in session.step(controls("pause"))], ["paused"])
        self.assertEqual(session.step(controls()), [])
        self.assertEqual(session.snapshot()["hold"], [item("I1", fresh=30)])
        self.assertEqual(session.snapshot()["phase_tick"], 0)

        resumed = session.step(controls("pause"))
        self.assertEqual([(row["tick"], row["name"]) for row in resumed], [(3, "resumed"), (3, "spoiled")])
        self.assertAlmostEqual(session.snapshot()["hold"][0]["fresh"], 30 - self.decay)

    def test_aging_precedes_hit_then_faint_drops_remaining_items_in_lifo_order(self):
        pos = [60, 24]
        monster = {"id": "M1", "kind": "ca_sau", "pos": pos, "waypoints": [pos, [64, 24]]}
        ids = IdAllocator()
        sim = self.sim(ids=ids, player={"pos": pos, "hp": 1}, time_left_ticks=1, monsters=[monster],
                       hold=[item("I10"), item("I1", "ca_keo", 30), item("I4", "ca_loc", 31)])
        events = sim.step(controls("catch"))
        self.assertEqual([name for name, _ in events], ["spoiled", "monster_hit", "faint", "gather_end"])
        lost = events[1][1]["lost"] + events[2][1]["lost"]
        self.assertEqual([row["id"] for row in lost], ["I4", "I1", "I10"])
        self.assertAlmostEqual(lost[0]["fresh"], 31 - self.decay)
        self.assertLess(lost[1]["fresh"], 30)
        self.assertEqual(events[-1][1], {"reason": "fainted", "inventory": {"items": []}})
        self.assertEqual(sim.snapshot()["hold"], [])

        next_gather = self.sim(ids=ids, player={"pos": self.gather["nodes"][0]["pos"]})
        next_gather.step(controls("interact"))
        self.assertEqual(next_gather.snapshot()["hold"][0]["id"], "I11")

    def test_aging_precedes_fatal_choke_and_no_monster_hit_occurs(self):
        pos = [60, 24]
        monster = {"id": "M1", "kind": "ca_sau", "pos": pos, "waypoints": [pos, [64, 24]]}
        sim = self.sim(
            player={"pos": pos, "hp": 1, "oxygen_ticks": 0,
                    "zero_oxy_ticks": self.gather["choke_interval_ticks"] - 1},
            monsters=[monster], hold=[item("I10", fresh=30), item("I2")],
        )
        events = sim.step(controls("catch"))
        self.assertEqual([name for name, _ in events], ["spoiled", "choke", "faint", "gather_end"])
        self.assertEqual(events[-2][1]["cause"], "choke")
        self.assertEqual([row["id"] for row in events[-2][1]["lost"]], ["I2", "I10"])
        self.assertEqual(events[-1][1]["inventory"], {"items": []})

    def test_last_tick_keeps_fresh_catch_but_dock_has_priority(self):
        fixture = [item("I1", fresh=30)]
        docked = self.sim(hold=fixture, time_left_ticks=1)
        events = docked.step(controls("interact", "catch"))
        self.assertEqual([name for name, _ in events], ["spoiled", "gather_end"])
        self.assertEqual(events[-1][1]["reason"], "docked")
        self.assertLess(events[-1][1]["inventory"]["items"][0]["fresh"], 30)

        pos = [15, 5]
        caught = self.sim(hold=fixture, time_left_ticks=1, player={"pos": pos},
                          fish=[{"id": "F1", "kind": "ca_linh", "pos": pos}])
        events = caught.step(controls("catch"))
        self.assertEqual([name for name, _ in events], ["spoiled", "fish_caught", "gather_end"])
        self.assertEqual(events[-1][1]["reason"], "time")
        stock = events[-1][1]["inventory"]["items"]
        self.assertLess(stock[0]["fresh"], 30)
        self.assertEqual([row["fresh"] for row in stock[1:]], [100] * self.gather["fish_yield"]["ca_linh"])
