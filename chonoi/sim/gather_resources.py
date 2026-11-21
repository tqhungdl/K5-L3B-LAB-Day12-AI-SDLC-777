"""Hái, bắt cá và hồi tài nguyên trong ca Gather."""

import math

from .. import TICK_HZ
from ..ids import id_key, sort_by_id


def _spawn_points(tuning):
    return {
        kind: [(x, depth) for x in tuning["fish_spawn_x"] for depth in tuning["fish_spawn_depths"][kind]]
        for kind in sorted(tuning["fish_weights"])
    }


def _new_school(sim, rng, points):
    kinds = [kind for kind, positions in points.items() if positions]
    if not kinds:
        return None
    weights = [sim.t["fish_weights"][kind] for kind in kinds]
    kind = rng.choices(kinds, weights=weights, k=1)[0]
    return {
        "id": sim.ids.new("F"), "kind": kind, "pos": list(rng.choice(points[kind])),
        "heading_deg": rng.random() * 360, "age_ticks": 0,
    }


def init_fish(sim, scenario):
    if "fish" in scenario:
        schools = [
            dict(fish, pos=list(fish["pos"]), heading_deg=fish.get("heading_deg", 0),
                 age_ticks=fish.get("age_ticks", 0))
            for fish in scenario["fish"]
        ]
        for school in schools:
            sim.ids.reserve(school["id"])
        return sort_by_id(schools)
    if not scenario.get("random_fish", True):
        return []

    rng = sim.rng.get("fish_initial")
    points = _spawn_points(sim.t)
    schools = []
    for _ in range(sim.t["fish_initial"]):
        school = _new_school(sim, rng, points)
        schools.append(school)
        occupied = tuple(school["pos"])
        for positions in points.values():
            if occupied in positions:
                positions.remove(occupied)
    return schools


def _reflect(position, delta, bounds):
    low, high = bounds
    position += delta
    if delta < 0 and position <= low:
        return 2 * low - position, -delta
    if delta > 0 and position >= high:
        return 2 * high - position, -delta
    return position, delta


def advance_fish(sim, phase_tick, events):
    if not sim.random_fish:
        return
    tuning = sim.t
    step = tuning["fish_speed"] / TICK_HZ
    turns = sim.rng.get("fish_turn")
    for school in sort_by_id(sim.fish):
        school["age_ticks"] += 1
        if school["age_ticks"] % tuning["fish_turn_ticks"] == 0:
            school["heading_deg"] = turns.random() * 360
        heading = math.radians(school["heading_deg"])
        dx, depth_delta = step * math.cos(heading), step * math.sin(heading)
        x, reflected_x = _reflect(school["pos"][0], dx, tuning["fish_x"])
        depth, reflected_depth = _reflect(
            school["pos"][1], depth_delta, tuning["fish_depths"][school["kind"]]
        )
        school["pos"] = [x, depth]
        if reflected_x != dx or reflected_depth != depth_delta:
            school["heading_deg"] = math.degrees(math.atan2(reflected_depth, reflected_x)) % 360

    if phase_tick <= 0 or phase_tick % tuning["fish_spawn_ticks"] or len(sim.fish) >= tuning["fish_max"]:
        return
    clearance = tuning["fish_spawn_clearance"]
    points = {
        kind: [pos for pos in positions if all(math.dist(pos, fish["pos"]) > clearance for fish in sim.fish)]
        for kind, positions in _spawn_points(tuning).items()
    }
    school = _new_school(sim, sim.rng.get("fish_spawn"), points)
    if school is not None:
        sim.fish.append(school)
        events.append(("fish_spawned", {"id": school["id"], "kind": school["kind"], "pos": school["pos"].copy()}))


def _nearest(pos, candidates, radius):
    ranked = ((math.dist(pos, entity["pos"]), id_key(entity["id"]), entity)
              for entity in candidates)
    nearest = min(ranked, default=None)
    if nearest is not None and nearest[0] <= radius:
        return nearest[2]
    return None


def tick_resources(sim, events):
    sim.catch_cd_ticks = max(0, sim.catch_cd_ticks - 1)
    for node in sort_by_id(sim.nodes):
        if node["regrow_ticks"] > 0:
            node["regrow_ticks"] -= 1
            if node["regrow_ticks"] == 0:
                events.append(("node_regrown", {"node_id": node["id"]}))


def harvest(sim, events):
    if not sim._at_surface():
        return
    ready = (node for node in sim.nodes if node["regrow_ticks"] == 0)
    node = _nearest(sim.pos, ready, sim.t["interact_radius"])
    if node is None:
        return

    amount = sim.t["node_yield"]
    if not sim._try_add_to_hold(node["kind"], amount):
        events.append(("hold_full", {"action": "gather", "node_id": node["id"],
                                     "required": amount, "free": sim.t["hold_capacity"] - len(sim.hold)}))
        return

    node["regrow_ticks"] = round(sim.t["regrow_s"] * TICK_HZ)
    events.append(("gather", {"node_id": node["id"], "kind": node["kind"], "amount": amount}))


def catch_fish(sim, events):
    if sim.catch_cd_ticks > 0 or sim._at_surface():
        return
    fish = _nearest(sim.pos, sim.fish, sim.t["catch_radius"])
    if fish is None:
        return

    amount = sim.t["fish_yield"][fish["kind"]]
    if not sim._try_add_to_hold(fish["kind"], amount):
        events.append(("hold_full", {"action": "catch", "fish_id": fish["id"],
                                     "required": amount, "free": sim.t["hold_capacity"] - len(sim.hold)}))
        return

    sim.fish.remove(fish)
    sim.catch_cd_ticks = round(sim.t["catch_cooldown_s"] * TICK_HZ)
    events.append(("fish_caught", {"fish_id": fish["id"], "kind": fish["kind"], "yield": amount}))
