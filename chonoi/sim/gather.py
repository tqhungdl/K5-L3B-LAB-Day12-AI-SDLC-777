"""Buổi sáng — Lặn & Hái. Tọa độ [x, d] có độ sâu d tăng khi lặn xuống."""

import math

from ..ids import sort_by_id
from ..inventory import hold_to_items
from ..scenario import validate_gather_player_limits
from .gather_monsters import advance_monsters, init_monsters
from .gather_resources import catch_fish, harvest, tick_resources
from .ramp import ramp_velocity

AXES = ("x", "d")


class GatherSim:
    mode = "gather"
    phase = "gather"

    def __init__(self, tuning, scenario, streams, ids, *, day_number=1, active_upgrades=None):
        t = tuning["gather"]
        self.t = t
        self.tick_hz = tuning["tick_hz"]
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        self.heading = float(p.get("heading_deg", t["start_heading_deg"]))
        upgrades = tuning.get("shop", {}).get("upgrades", {})
        active_upgrades = active_upgrades or {}
        oxygen_s = _upgrade_value(upgrades, active_upgrades, "oxygen", "oxygen_max_s", t["oxygen_max_s"])
        self.oxygen_max = round(oxygen_s * self.tick_hz)
        self.hp_max = _upgrade_value(upgrades, active_upgrades, "hp", "hp_max", t["hp_max"])
        validate_gather_player_limits(p, self.oxygen_max, self.hp_max)
        self.oxygen_ticks = p.get("oxygen_ticks", self.oxygen_max)
        self.hp = p.get("hp", self.hp_max)
        self.zero_oxy_ticks = p.get("zero_oxy_ticks", 0)
        self.invuln_ticks = p.get("invuln_ticks", 0)
        self.catch_cd_ticks = p.get("catch_cd_ticks", 0)
        self.hold = list(scenario.get("hold", []))  # thứ tự nhặt, cuối mảng là mới nhất
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * self.tick_hz)))
        self.phase_tick = 0
        src_nodes = scenario.get("nodes", t["nodes"])
        self.nodes = [{"id": n["id"], "kind": n["kind"], "pos": [float(c) for c in n["pos"]],
                       "regrow_ticks": n.get("regrow_ticks", 0)} for n in src_nodes]
        for node in self.nodes:
            ids.reserve(node["id"])
        self.monsters = init_monsters(self, scenario, day_number)
        self.random_fish = scenario.get("random_fish", True)
        self._advance_fish = None
        self.fish = self._init_fish(scenario)
        self.money = 0
        self.earned = 0
        self.reputation = tuning["quan"]["reputation_initial"]
        self.done = False
        self.reason = None

    def _init_fish(self, scenario):
        initial = self.t["fish_initial"]
        if isinstance(initial, list):
            # Manifest v1.0 liệt kê đàn cá cố định. V1.1 dựng đàn qua module của lát 1.
            fish = scenario.get("fish", initial if self.random_fish else [])
            for school in fish:
                self.ids.reserve(school["id"])
            return [
                dict(school, pos=list(school["pos"]), heading_deg=school.get("heading_deg", 0),
                     age_ticks=school.get("age_ticks", 0))
                for school in fish
            ]

        from .gather_resources import advance_fish, init_fish

        self._advance_fish = advance_fish
        return init_fish(self, scenario)

    # --- giao diện cho runner -------------------------------------------------
    def inventory_items(self) -> dict:
        return hold_to_items(self.hold)

    def snapshot(self) -> dict:
        return {
            "player": {"pos": self.pos, "vel": self.vel, "heading_deg": self.heading,
                       "oxygen_ticks": self.oxygen_ticks, "oxygen_max_ticks": self.oxygen_max,
                       "hp": self.hp, "hp_max": self.hp_max, "zero_oxy_ticks": self.zero_oxy_ticks,
                       "invuln_ticks": self.invuln_ticks, "catch_cd_ticks": self.catch_cd_ticks,
                       "at_surface": self._at_surface()},
            "hold": self.hold, "hold_count": len(self.hold),
            "hold_capacity": self.t["hold_capacity"],
            "nodes": [{"id": n["id"], "pos": n["pos"], "kind": n["kind"],
                       "ready": n["regrow_ticks"] == 0, "regrow_ticks": n["regrow_ticks"]}
                      for n in sort_by_id(self.nodes)],
            "fish": [{"id": f["id"], "pos": f["pos"], "kind": f["kind"], "heading_deg": f["heading_deg"],
                      "age_ticks": f.get("age_ticks", 0)}
                     for f in sort_by_id(self.fish)],
            "monsters": [dict(monster) for monster in sort_by_id(self.monsters)],
        }

    # --- một bước ---------------------------------------------------------------
    def step(self, inp):
        events = []
        self.phase_tick += 1
        # 1. đồng hồ và hàng có sẵn: giảm bộ đếm, nút mọc lại
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.invuln_ticks = max(0, self.invuln_ticks - 1)
        tick_resources(self, events)
        # 2. bơi, chặn mép và tính oxy theo độ sâu cuối bước
        was_at_surface = self._at_surface()
        self._move(inp)
        at_surface = self._at_surface()
        if was_at_surface != at_surface:
            events.append(("surface" if at_surface else "dive", {"pos": self.pos.copy()}))
        self._tick_oxygen(at_surface, events)
        if self.done:
            return events
        advance_monsters(self, events)
        if self.hp == 0:
            self._faint("monster", events)
            return events
        # 3. interact: bến trước, rồi hái
        if inp.pressed("interact"):
            if self._in_dock():
                self._finish("docked", events)
                return events
            harvest(self, events)
        # 4. bắt cá
        if inp.pressed("catch"):
            catch_fish(self, events)
        # 5. hết giờ
        if self.time_left_ticks <= 0:
            self._finish("time", events)
        elif self._advance_fish is not None and self.random_fish:
            self._advance_fish(self, self.phase_tick, events)
        return events

    # --- tiện ích ---------------------------------------------------------------
    def _at_surface(self) -> bool:
        return self.pos[1] <= self.t["surface_depth"]

    def _in_dock(self) -> bool:
        return math.dist(self.pos, self.t["dock_pos"]) <= self.t["dock_radius"]

    def _try_add_to_hold(self, kind: str, amount: int) -> bool:
        if len(self.hold) + amount > self.t["hold_capacity"]:
            return False
        self.hold.extend([kind] * amount)
        return True

    def _tick_oxygen(self, at_surface, events):
        if at_surface:
            self.oxygen_ticks = min(
                self.oxygen_max, self.oxygen_ticks + self.t["oxygen_refill_per_tick"]
            )
            self.zero_oxy_ticks = 0
            return

        if self.oxygen_ticks > 0:
            self.zero_oxy_ticks = 0
            self.oxygen_ticks -= 1
            if self.oxygen_ticks > 0:
                return
            events.append(("oxygen_empty", {"oxygen_ticks": 0}))

        self.zero_oxy_ticks += 1
        if self.zero_oxy_ticks < self.t["choke_interval_ticks"]:
            return

        self.zero_oxy_ticks = 0
        self.hp -= 1
        events.append(("choke", {"hp": self.hp}))
        if self.hp == 0:
            self._faint("choke", events)

    def _faint(self, cause, events):
        lost = list(reversed(self.hold))
        self.hold.clear()
        events.append(("faint", {"cause": cause, "lost": lost, "hp": self.hp}))
        self._finish("fainted", events)

    def _finish(self, reason, events):
        self.done = True
        self.reason = reason
        events.append(("gather_end", {"reason": reason, "inventory": {"items": self.inventory_items()}}))

    def _move(self, inp):
        speed = self.t["swim_speed"]
        mx, md = inp.move
        self.vel = ramp_velocity(self, (mx * speed, md * speed), int(self.t["ramp_max_ticks"]))
        if (mx, md) != (0.0, 0.0):
            self.heading = math.degrees(math.atan2(md, mx)) % 360
        b = self.t["bounds"]
        for i, axis in enumerate(AXES):
            self.pos[i] += self.vel[i] / self.tick_hz
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i] = lo
                self.vel[i] = max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i] = hi
                self.vel[i] = min(0.0, self.vel[i])


def _upgrade_value(upgrades, active, kind, field, base):
    level = active.get(kind, 0)
    return next((row[field] for row in upgrades.get(kind, ()) if row["level"] == level), base)
