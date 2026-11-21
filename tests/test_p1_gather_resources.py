import unittest

from chonoi import TICK_HZ
from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.rng import Streams
from chonoi.sim.gather import GatherSim
from chonoi.sim.gather_resources import catch_fish, harvest, tick_resources


class GatherFixture(GatherSim):
    def _try_add_to_hold(self, kind, amount):
        # Giao diện giỏ của lát 1 để kiểm module tài nguyên độc lập.
        if len(self.hold) + amount > self.t["hold_capacity"]:
            return False
        self.hold.extend([kind] * amount)
        return True


def node(ident, x, timer=0):
    return {"id": ident, "pos": [x, 0], "kind": "bong_sung", "regrow_ticks": timer}


def fish(ident, x, kind="ca_linh"):
    return {"id": ident, "pos": [x, 5], "kind": kind}


class GatherResourcesTest(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]
        self.gather = self.tuning["gather"]
        self.events = []

    def sim(self, *, pos=(20, 0), nodes=(), schools=(), hold=(), cooldown=0):
        scenario = {"player": {"pos": pos, "catch_cd_ticks": cooldown}, "nodes": list(nodes),
                    "fish": list(schools), "hold": list(hold)}
        return GatherFixture(self.tuning, scenario, Streams(42), IdAllocator())

    def test_regrow_in_id_order_and_harvest_on_same_step(self):
        radius = self.gather["interact_radius"]
        sim = self.sim(nodes=[node("N10", 20 - radius, 1), node("N2", 20 + radius, 1),
                             node("N1", 20, 2)], cooldown=1)
        tick_resources(sim, self.events)
        harvest(sim, self.events)
        amount = self.gather["node_yield"]
        self.assertEqual(self.events, [
            ("node_regrown", {"node_id": "N2"}), ("node_regrown", {"node_id": "N10"}),
            ("gather", {"node_id": "N2", "kind": "bong_sung", "amount": amount}),
        ])
        self.assertEqual(sim.catch_cd_ticks, 0)
        self.assertEqual(sim.hold, ["bong_sung"] * amount)
        self.assertEqual({n["id"]: n["regrow_ticks"] for n in sim.nodes},
                         {"N1": 1, "N2": round(self.gather["regrow_s"] * TICK_HZ), "N10": 0})

    def test_harvest_skips_unready_out_of_range_and_underwater(self):
        radius = self.gather["interact_radius"]
        sim = self.sim(nodes=[node("N1", 20, 1), node("N2", 21 + radius)])
        harvest(sim, self.events)
        sim.pos[1] = self.gather["surface_depth"] + 0.1
        sim.nodes[0]["regrow_ticks"] = 0
        harvest(sim, self.events)
        self.assertEqual(self.events, [])
        self.assertEqual(sim.hold, [])

    def test_full_hold_keeps_node_ready(self):
        hold = ["ca_loc"] * self.gather["hold_capacity"]
        sim = self.sim(nodes=[node("N1", 20)], hold=hold)
        harvest(sim, self.events)
        self.assertEqual(self.events, [("hold_full", {"action": "gather", "node_id": "N1",
                                                     "required": self.gather["node_yield"], "free": 0})])
        self.assertEqual(sim.hold, hold)
        self.assertEqual(sim.nodes[0]["regrow_ticks"], 0)

    def test_catch_at_radius_breaks_tie_and_waits_until_cooldown_zero(self):
        radius = self.gather["catch_radius"]
        sim = self.sim(pos=(20, 5), schools=[fish("F10", 20 - radius, "ca_loc"),
                                             fish("F2", 20 + radius)])
        catch_fish(sim, self.events)
        amount = self.gather["fish_yield"]["ca_linh"]
        duration = round(self.gather["catch_cooldown_s"] * TICK_HZ)
        self.assertEqual(self.events, [("fish_caught", {"fish_id": "F2", "kind": "ca_linh", "yield": amount})])
        self.assertEqual(sim.hold, ["ca_linh"] * amount)
        self.assertEqual(sim.catch_cd_ticks, duration)

        for _ in range(max(0, duration - 1)):
            tick_resources(sim, self.events)
            catch_fish(sim, self.events)
        self.assertEqual([school["id"] for school in sim.fish], ["F10"])
        tick_resources(sim, self.events)
        catch_fish(sim, self.events)
        self.assertEqual(self.events[-1][1]["fish_id"], "F10")
        self.assertEqual(sim.fish, [])

    def test_insufficient_space_keeps_nearest_fish_and_does_not_try_another(self):
        hold = ["bong_sung"] * (self.gather["hold_capacity"] - 1)
        sim = self.sim(pos=(20, 5), schools=[fish("F2", 20 + self.gather["catch_radius"], "ca_loc"),
                                             fish("F1", 20)], hold=hold)
        catch_fish(sim, self.events)
        self.assertEqual(self.events, [("hold_full", {"action": "catch", "fish_id": "F1",
                                                     "required": self.gather["fish_yield"]["ca_linh"], "free": 1})])
        self.assertCountEqual([school["id"] for school in sim.fish], ["F2", "F1"])
        self.assertEqual(sim.hold, hold)
        self.assertEqual(sim.catch_cd_ticks, 0)

    def test_catch_above_water_or_out_of_range_does_not_start_cooldown(self):
        sim = self.sim(pos=(20, self.gather["surface_depth"]), schools=[fish("F1", 20)])
        sim.fish[0]["pos"][1] = sim.pos[1] + self.gather["catch_radius"] / 2
        catch_fish(sim, self.events)
        sim.pos[:] = [21 + self.gather["catch_radius"], 5]
        catch_fish(sim, self.events)
        self.assertEqual(self.events, [])
        self.assertEqual(sim.catch_cd_ticks, 0)
        self.assertEqual(sim.hold, [])
