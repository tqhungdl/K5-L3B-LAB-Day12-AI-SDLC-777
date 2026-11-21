"""Tuần tra, truy đuổi và va chạm trong ca Gather."""

import math

from ..ids import id_key, sort_by_id


def init_monsters(sim, scenario, day_number):
    config = sim.t.get("monsters", {})
    spawns = scenario.get("monsters")
    if spawns is None:
        spawns = [spawn for spawn in config.get("spawns", ()) if spawn["from_day"] <= day_number]

    monsters = []
    for spawn in sort_by_id(spawns):
        sim.ids.reserve(spawn["id"])
        direction = spawn.get("recoil_dir")
        monsters.append({
            "id": spawn["id"],
            "kind": spawn["kind"],
            "pos": list(spawn["pos"]),
            "waypoints": [list(point) for point in spawn["waypoints"]],
            "target_idx": spawn.get("target_idx", 1),
            "state": spawn.get("state", "patrol"),
            "state_ticks_left": spawn.get("state_ticks_left", 0),
            "recoil_dir": list(direction) if direction is not None else None,
        })
    return monsters


def _unit_direction(origin, target):
    distance = math.dist(origin, target)
    if distance == 0:
        return [1.0, 0.0]
    return [(end - start) / distance for start, end in zip(origin, target)]


def _move_toward(pos, target, distance):
    remaining = math.dist(pos, target)
    if remaining <= distance or math.isclose(remaining, distance):
        return list(target)
    return [coord + delta * distance for coord, delta in zip(pos, _unit_direction(pos, target))]


def _advance_monster(monster, species, player_pos, tick_hz):
    pos = monster["pos"]
    state = monster["state"]
    if state in ("recoil", "stunned"):
        if state == "recoil":
            distance = species["recoil_dist"] / species["recoil_ticks"]
            monster["pos"] = [
                coord + delta * distance for coord, delta in zip(pos, monster["recoil_dir"])
            ]
        monster["state_ticks_left"] -= 1
        if monster["state_ticks_left"] == 0:
            monster["state"] = "patrol"
            monster["recoil_dir"] = None
        return False

    distance = math.dist(pos, player_pos)
    in_depth = player_pos[1] >= species["depths"][0]
    radius = species["exit_radius"] if state == "chase" else species["detect_radius"]
    if in_depth and distance <= radius:
        monster["state"] = "chase"
        monster["pos"] = _move_toward(pos, player_pos, species["chase_speed"] / tick_hz)
    else:
        monster["state"] = "patrol"
        target = monster["waypoints"][monster["target_idx"]]
        monster["pos"] = _move_toward(pos, target, species["patrol_speed"] / tick_hz)
        if monster["pos"] == target:
            monster["target_idx"] = 1 - monster["target_idx"]
    return in_depth


def advance_monsters(sim, events):
    if not sim.monsters:
        return

    config = sim.t["monsters"]
    x_min, x_max = sim.t["bounds"]["x"]
    depth_min, depth_max = sim.t["bounds"]["d"]
    hits = []
    for monster in sort_by_id(sim.monsters):
        species = config["species"][monster["kind"]]
        can_hit = _advance_monster(monster, species, sim.pos, sim.tick_hz)
        x, depth = monster["pos"]
        lo, hi = species["depths"]
        monster["pos"] = [
            min(x_max, max(x_min, x)),
            min(depth_max, hi, max(depth_min, lo, depth)),
        ]
        if can_hit and sim.invuln_ticks == 0:
            distance = math.dist(monster["pos"], sim.pos)
            if distance <= species["hit_radius"]:
                hits.append((distance, id_key(monster["id"]), monster))
    if not hits:
        return

    _, _, monster = min(hits, key=lambda hit: hit[:2])
    species = config["species"][monster["kind"]]
    sim.hp -= 1
    loss_count = math.floor(len(sim.hold) * config["loss_ratio"])
    lost = [sim.hold.pop() for _ in range(loss_count)]
    sim.invuln_ticks = config["invuln_ticks"]
    monster["state"] = "recoil"
    monster["state_ticks_left"] = species["recoil_ticks"]
    monster["recoil_dir"] = _unit_direction(sim.pos, monster["pos"])
    events.append(("monster_hit", {
        "monster_id": monster["id"], "hp": sim.hp, "lost": lost, "pos": sim.pos.copy(),
    }))
