"""Nạp fixture cho ca độc lập hoặc các mẫu khởi tạo của một lượt Ngày."""

import json
import math

from .errors import BadInput
from .ids import id_key
from .inventory import validate_items

GATHER_KEYS = {"player", "hold", "nodes", "fish", "random_fish", "monsters", "time_left_ticks"}
DAY_KEYS = {"money", "earned", "reputation", "upgrades", "day_plan"}
GATHER_PLAYER_KEYS = {"pos", "vel", "heading_deg", "hp", "oxygen_ticks", "zero_oxy_ticks",
                      "invuln_ticks", "catch_cd_ticks"}
NODE_KEYS = {"id", "kind", "pos", "regrow_ticks"}
FISH_KEYS = {"id", "kind", "pos", "heading_deg", "age_ticks"}
MONSTER_KEYS = {"id", "kind", "pos", "waypoints", "target_idx", "state", "state_ticks_left", "recoil_dir"}
QUAN_PLAYER_KEYS = {"pos", "vel"}
QUAN_KEYS = {"player", "stock", "hand", "stoves", "tables", "customers", "random_customers",
             "reputation", "time_left_ticks"}
STOVE_KEYS = {"id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks"}
TABLE_KEYS = {"id", "pos"}
CUSTOMER_KEYS = {"id", "table_id", "dish_id", "order_tick", "state", "patience_ticks_left",
                 "eat_ticks_left", "order_status", "reserved", "base_price", "tip"}
DISH_KEYS = {"order_id", "dish_id", "base_price"}
STOVE_STATES = ("idle", "cooking", "ready")
CUSTOMER_STATES = ("waiting", "eating")
ORDER_STATUSES = ("reserved", "assigned", "unfulfillable", "served")


def _check_ids(name, arr):
    if not isinstance(arr, list):
        raise BadInput(f"{name} phải là mảng")
    seen = set()
    for e in arr:
        if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not e["id"]:
            raise BadInput(f"{name}: mỗi phần tử cần id (chuỗi khác rỗng)")
        if e["id"] in seen:
            raise BadInput(f"{name}: id trùng {e['id']}")
        seen.add(e["id"])


def load_scenario(path, mode: str, tuning: dict) -> dict:
    data = {}
    if path is not None:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            raise BadInput(f"không đọc được scenario {path}: {e}") from e

    modes = ("day", "gather", "quan") if mode == "day" else (mode,)
    if not isinstance(data, dict) or set(data) - set(modes):
        raise BadInput(f"khối sai mode: --mode {mode} chỉ nhận {', '.join(modes)}")
    blocks = {name: data.get(name, {}) for name in modes}
    if mode == "day":
        _validate_day(blocks["day"], tuning)
        _validate_shift("gather", blocks["gather"], tuning, in_day=True)
        _validate_shift("quan", blocks["quan"], tuning, in_day=True)
        return blocks
    _validate_shift(mode, blocks[mode], tuning)
    return blocks[mode]


def _check_keys(name, block, allowed):
    if not isinstance(block, dict):
        raise BadInput(f"{name} phải là object")
    extra = set(block) - allowed
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong {name}: {sorted(extra)}")


def _validate_shift(mode, block, tuning, *, in_day=False):
    allowed = GATHER_KEYS if mode == "gather" else QUAN_KEYS
    if mode == "quan" and in_day:
        allowed = allowed - {"stock", "reputation"}
    _check_keys(mode, block, allowed)
    dur = round(tuning[mode]["duration_s"] * tuning["tick_hz"])
    if "time_left_ticks" in block:
        t = block["time_left_ticks"]
        if isinstance(t, bool) or not isinstance(t, int) or not (1 <= t <= dur):
            raise BadInput(f"time_left_ticks phải là số nguyên trong [1, {dur}]")
    if mode == "gather":
        _validate_gather(block, tuning, in_day=in_day)
    else:
        _validate_quan(block, tuning, in_day=in_day)


def _validate_day(block, tuning):
    _check_keys("day", block, DAY_KEYS)
    money = block.get("money", 0)
    earned = block.get("earned", 0)
    _nonneg_int("day.money", money)
    _nonneg_int("day.earned", earned)
    if money > earned:
        raise BadInput("day.money không được vượt day.earned")
    if "reputation" in block:
        _validate_reputation("day.reputation", block["reputation"], tuning["quan"])
    upgrades = tuning.get("shop", {}).get("upgrades", {})
    active = block.get("upgrades", {})
    _check_keys("day.upgrades", active, upgrades.keys())
    for kind, level in active.items():
        _nonneg_int(f"day.upgrades.{kind}", level)
        if level != 0 and all(row["level"] != level for row in upgrades[kind]):
            raise BadInput(f"day.upgrades.{kind}: cấp không tồn tại ({level})")
    # DaySim dùng resolve_day_plans cho cả preset và override.


def _num(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    try:
        return math.isfinite(v)
    except OverflowError:
        return False


def _nonneg_int(name, v):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise BadInput(f"{name} phải là số nguyên không âm")
def _pos_int(name, v):
    if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
        raise BadInput(f"{name} phải là số nguyên dương")
def _pos(name, pos, bounds, axes=("x", "d")):
    if not (isinstance(pos, list) and len(pos) == 2 and all(_num(c) for c in pos)):
        raise BadInput(f"{name} phải là [{axes[0]}, {axes[1]}]")
    for c, axis in zip(pos, axes):
        lo, hi = bounds[axis]
        if not (lo <= c <= hi):
            raise BadInput(f"{name} nằm ngoài miền hợp lệ ({axis} ∈ [{lo}, {hi}])")
def _validate_dish(name, dish, menu):
    if not isinstance(dish, dict):
        raise BadInput(f"{name} phải là object món")
    extra = set(dish) - DISH_KEYS
    if extra:
        raise BadInput(f"{name} có trường lạ: {sorted(extra)}")
    missing = DISH_KEYS - set(dish)
    if missing:
        raise BadInput(f"{name} thiếu trường: {sorted(missing)}")
    if not isinstance(dish["order_id"], str) or not dish["order_id"]:
        raise BadInput(f"{name}.order_id phải là chuỗi khác rỗng")
    if not isinstance(dish["dish_id"], str) or dish["dish_id"] not in menu:
        raise BadInput(f"{name}.dish_id không thuộc thực đơn: {dish['dish_id']!r}")
    _pos_int(f"{name}.base_price", dish["base_price"])
def _norm_items(items: dict) -> dict:
    return {k: items[k] for k in sorted(items) if items[k] > 0}
def validate_gather_player_limits(player, oxygen_max, hp_max):
    if "oxygen_ticks" in player:
        oxygen = player["oxygen_ticks"]
        _nonneg_int("player.oxygen_ticks", oxygen)
        if oxygen_max is not None and oxygen > oxygen_max:
            raise BadInput("player.oxygen_ticks vượt oxy tối đa")
    if "hp" in player:
        hp = player["hp"]
        _pos_int("player.hp", hp)
        if hp_max is not None and hp > hp_max:
            raise BadInput("player.hp phải trong [1, hp_max]")


def _node_kinds(gather):
    return {node["kind"] for node in gather["nodes"]}


def _validate_gather(b, tuning, *, in_day=False):
    g = tuning["gather"]
    bounds = g["bounds"]
    node_kinds = _node_kinds(g)
    kinds = node_kinds | g["fish_yield"].keys()
    for arr in ("nodes", "fish", "monsters"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "random_fish" in b and not isinstance(b["random_fish"], bool):
        raise BadInput("random_fish phải là boolean")
    if "hold" in b:
        h = b["hold"]
        if not isinstance(h, list) or any(not isinstance(k, str) or k not in kinds for k in h):
            raise BadInput("hold phải là mảng id nguyên liệu hợp lệ")
        if len(h) > g["hold_capacity"]:
            raise BadInput("hold vượt sức chứa")
    p = b.get("player", {})
    if not isinstance(p, dict):
        raise BadInput("player phải là object")
    extra = set(p) - GATHER_PLAYER_KEYS
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong gather.player: {sorted(extra)}")
    if "pos" in p:
        _pos("player.pos", p["pos"], bounds)
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, d]")
    if "heading_deg" in p and not _num(p["heading_deg"]):
        raise BadInput("player.heading_deg phải là số")
    for key in ("invuln_ticks", "catch_cd_ticks", "zero_oxy_ticks"):
        if key in p:
            _nonneg_int(f"player.{key}", p[key])
    if in_day:
        validate_gather_player_limits(p, None, None)
    else:
        validate_gather_player_limits(p, round(g["oxygen_max_s"] * tuning["tick_hz"]), g["hp_max"])
    if "zero_oxy_ticks" in p:
        pos = p.get("pos", g["start_pos"])
        oxy = p.get("oxygen_ticks")
        max_zero = g["choke_interval_ticks"] - 1
        if p["zero_oxy_ticks"] > max_zero:
            raise BadInput(f"player.zero_oxy_ticks phải trong [0, {max_zero}]")
        if p["zero_oxy_ticks"] > 0 and not (oxy == 0 and pos[1] > g["surface_depth"]):
            raise BadInput("player.zero_oxy_ticks > 0 chỉ khi oxy = 0 và đang dưới nước")
    for n in b.get("nodes", []):
        extra_n = set(n) - NODE_KEYS
        if extra_n:
            raise BadInput(f"nodes.{n['id']}: trường lạ {sorted(extra_n)}")
        if not isinstance(n.get("kind"), str) or n["kind"] not in node_kinds:
            raise BadInput(f"nodes.{n['id']}: kind phải là một trong {sorted(node_kinds)}")
        _pos(f"nodes.{n['id']}.pos", n.get("pos"), bounds)
        if n["pos"][1] != 0:
            raise BadInput(f"nodes.{n['id']}: nút hái nằm ở mặt nước (d = 0)")
        if "regrow_ticks" in n:
            _nonneg_int(f"nodes.{n['id']}.regrow_ticks", n["regrow_ticks"])
    for f in b.get("fish", []):
        extra_f = set(f) - FISH_KEYS
        if extra_f:
            raise BadInput(f"fish.{f['id']}: trường lạ {sorted(extra_f)}")
        if not isinstance(f.get("kind"), str) or f["kind"] not in g["fish_yield"]:
            raise BadInput(f"fish.{f['id']}: kind phải thuộc fish_yield")
        fish_bounds = bounds
        if b.get("random_fish", True) and "fish_depths" in g:
            fish_bounds = {"x": g["fish_x"], "d": g["fish_depths"][f["kind"]]}
        _pos(f"fish.{f['id']}.pos", f.get("pos"), fish_bounds)
        if f["pos"][1] <= g["surface_depth"]:
            raise BadInput(f"fish.{f['id']}: đàn cá phải ở dưới nước")
        if "heading_deg" in f and not _num(f["heading_deg"]):
            raise BadInput(f"fish.{f['id']}.heading_deg phải là số")
        _nonneg_int(f"fish.{f['id']}.age_ticks", f.get("age_ticks", 0))
    for monster in b.get("monsters", []):
        _validate_monster(monster, tuning)


def _validate_monster(monster, tuning):
    name = f"monsters.{monster['id']}"
    _check_keys(name, monster, MONSTER_KEYS)
    g = tuning["gather"]
    species = g.get("monsters", {}).get("species", {})
    kind = monster.get("kind")
    if not isinstance(kind, str) or kind not in species:
        raise BadInput(f"{name}.kind: loài không có trong tuning")
    lo, hi = species[kind]["depths"]
    depth_min, depth_max = g["bounds"]["d"]
    bounds = {"x": g["bounds"]["x"], "d": (max(lo, depth_min), min(hi, depth_max))}
    _pos(f"{name}.pos", monster.get("pos"), bounds)
    points = monster.get("waypoints")
    if not isinstance(points, list) or len(points) != 2:
        raise BadInput(f"{name}.waypoints phải có đúng hai tọa độ")
    for point in points:
        _pos(f"{name}.waypoints", point, bounds)
    target = monster.get("target_idx", 1)
    _nonneg_int(f"{name}.target_idx", target)
    if target > 1:
        raise BadInput(f"{name}.target_idx phải là 0 hoặc 1")

    states = ("patrol", "chase", "recoil")
    if "weapon" in tuning.get("shop", {}).get("upgrades", {}):
        states += ("stunned",)
    state = monster.get("state", "patrol")
    if state not in states:
        raise BadInput(f"{name}.state không hợp lệ ({state!r})")
    remaining = monster.get("state_ticks_left", 0)
    _nonneg_int(f"{name}.state_ticks_left", remaining)
    if (remaining > 0) != (state in ("recoil", "stunned")):
        raise BadInput(f"{name}.state_ticks_left chỉ dương khi recoil hoặc stunned")

    direction = monster.get("recoil_dir")
    if state == "recoil":
        _pos(f"{name}.recoil_dir", direction, {"x": (-1, 1), "d": (-1, 1)})
        if not math.isclose(math.hypot(*direction), 1.0):
            raise BadInput(f"{name}.recoil_dir phải là vector đơn vị")
    elif direction is not None:
        raise BadInput(f"{name}.recoil_dir chỉ có giá trị khi recoil")


def _validate_reputation(name, value, quan):
    lo, hi = quan["reputation_min"], quan["reputation_max"]
    if not _num(value) or not lo <= value <= hi:
        raise BadInput(f"{name} phải trong [{lo}, {hi}]")


def _validate_quan(b, tuning, *, in_day=False):
    q = tuning["quan"]
    menu = tuning["menu"]
    qb = q["bounds"]
    known_stoves = {s["id"] for s in q["stoves"]}
    gather = tuning["gather"]
    kinds = _node_kinds(gather) | gather["fish_yield"].keys()
    known_tables = {t["id"] for t in q["tables"]}
    for arr in ("stoves", "tables", "customers"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "random_customers" in b and not isinstance(b["random_customers"], bool):
        raise BadInput("random_customers phải là boolean")
    if "reputation" in b:
        _validate_reputation("reputation", b["reputation"], q)
    if "stock" in b:
        validate_items(b["stock"], kinds)
    p = b.get("player", {})
    if not isinstance(p, dict) or set(p) - QUAN_PLAYER_KEYS:
        raise BadInput("quan.player chỉ có pos và vel")
    if "pos" in p:
        _pos("player.pos", p["pos"], qb, axes=("x", "z"))
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, z]")
    for tb in b.get("tables", []):
        extra_t = set(tb) - TABLE_KEYS
        if extra_t:
            raise BadInput(f"tables.{tb['id']}: trường lạ {sorted(extra_t)}")
        if tb["id"] not in known_tables:
            raise BadInput(f"tables: id bàn cập nhật không tồn tại ({tb['id']})")
        if "pos" in tb:
            _pos(f"tables.{tb['id']}.pos", tb["pos"], qb, axes=("x", "z"))
    for s in b.get("stoves", []):
        sid = s["id"]
        _check_keys(f"stoves.{sid}", s, STOVE_KEYS)
        if sid not in known_stoves:
            raise BadInput(f"stoves: id bếp cập nhật không tồn tại ({sid})")
        if "pos" in s:
            _pos(f"stoves.{sid}.pos", s["pos"], qb, axes=("x", "z"))
    for customer in b.get("customers", []):
        _check_keys(f"customers.{customer['id']}", customer, CUSTOMER_KEYS)
    if in_day:
        # QuanSim kiểm món và đơn khi đã có menu và tồn kho của ca thực tế.
        return

    dishes_by_order = {}
    for s in b.get("stoves", []):
        sid = s["id"]
        state = s.get("state", "idle")
        if state not in STOVE_STATES:
            raise BadInput(f"stoves.{sid}: state không hợp lệ ({state!r})")
        dish = s.get("dish")
        cook_left = s.get("cook_ticks_left", 0)
        ready_ticks = s.get("ready_ticks", 0)
        _nonneg_int(f"stoves.{sid}.cook_ticks_left", cook_left)
        _nonneg_int(f"stoves.{sid}.ready_ticks", ready_ticks)
        if state == "idle":
            if dish is not None or cook_left != 0 or ready_ticks != 0:
                raise BadInput(f"stoves.{sid}: bếp idle không được có món hoặc timer dương")
        elif state == "cooking":
            if dish is None:
                raise BadInput(f"stoves.{sid}: bếp cooking phải có dish")
            _validate_dish(f"stoves.{sid}.dish", dish, menu)
            if cook_left <= 0 or ready_ticks != 0:
                raise BadInput(f"stoves.{sid}: bếp cooking phải có cook_ticks_left > 0 và ready_ticks = 0")
        elif state == "ready":
            if dish is None:
                raise BadInput(f"stoves.{sid}: bếp ready phải có dish")
            _validate_dish(f"stoves.{sid}.dish", dish, menu)
            if cook_left != 0:
                raise BadInput(f"stoves.{sid}: bếp ready phải có cook_ticks_left = 0")
        if dish is not None:
            oid = dish["order_id"]
            if oid in dishes_by_order:
                raise BadInput(f"đơn {oid} xuất hiện trên nhiều bếp")
            dishes_by_order[oid] = dish
    hand = b.get("hand")
    if hand is not None:
        _validate_dish("hand", hand, menu)
        oid = hand["order_id"]
        if oid in dishes_by_order:
            raise BadInput(f"bếp và tay cùng giữ đơn {oid}")
        dishes_by_order[oid] = hand
    used_tables = set()
    customers_by_id = {}
    reserved_entries = []
    for c in b.get("customers", []):
        cid = c["id"]
        table_id = c.get("table_id")
        if not isinstance(table_id, str) or table_id not in known_tables:
            raise BadInput(f"customers.{cid}: table_id phải là bàn có thật")
        if table_id in used_tables:
            raise BadInput("hai khách cùng bàn")
        used_tables.add(table_id)
        dish_id = c.get("dish_id")
        if not isinstance(dish_id, str) or dish_id not in menu:
            raise BadInput(f"customers.{cid}: dish_id không thuộc thực đơn ({dish_id!r})")
        order_tick = c.get("order_tick", 0)
        _nonneg_int(f"customers.{cid}.order_tick", order_tick)
        state = c.get("state", "waiting")
        if state not in CUSTOMER_STATES:
            raise BadInput(f"customers.{cid}: state không hợp lệ ({state!r})")
        order_status = c.get("order_status", "reserved")
        if order_status not in ORDER_STATUSES:
            raise BadInput(f"customers.{cid}: order_status không hợp lệ ({order_status!r})")
        if "patience_ticks_left" in c:
            _nonneg_int(f"customers.{cid}.patience_ticks_left", c["patience_ticks_left"])
        eat_left = c.get("eat_ticks_left", 0)
        _nonneg_int(f"customers.{cid}.eat_ticks_left", eat_left)
        recipe = _norm_items(menu[dish_id]["recipe"])
        if "reserved" in c:
            res = _norm_items(validate_items(c["reserved"], kinds))
            if order_status == "reserved":
                if res != recipe:
                    raise BadInput(f"customers.{cid}: reserved khác công thức món {dish_id}")
            elif res:
                raise BadInput(f"customers.{cid}: đơn {order_status} phải có reserved rỗng")
        else:
            res = dict(recipe) if order_status == "reserved" else {}
        if state == "eating":
            if order_status != "served":
                raise BadInput(f"customers.{cid}: khách eating phải có order_status = 'served'")
            if eat_left <= 0:
                raise BadInput(f"customers.{cid}: khách eating phải có eat_ticks_left > 0")
            if "base_price" not in c or "tip" not in c:
                raise BadInput(f"customers.{cid}: khách eating phải khai base_price và tip đã chốt")
            _pos_int(f"customers.{cid}.base_price", c["base_price"])
            _nonneg_int(f"customers.{cid}.tip", c["tip"])
        else:
            if order_status == "served":
                raise BadInput(f"customers.{cid}: khách waiting không được có order_status = 'served'")
            if eat_left != 0:
                raise BadInput(f"customers.{cid}: khách waiting phải có eat_ticks_left = 0")
            if "tip" in c:
                _nonneg_int(f"customers.{cid}.tip", c["tip"])
                if c["tip"] != 0:
                    raise BadInput(f"customers.{cid}: khách waiting phải có tip = 0")
            if "base_price" in c:
                _nonneg_int(f"customers.{cid}.base_price", c["base_price"])
        customers_by_id[cid] = (c, state, order_status, dish_id)
        if res:
            reserved_entries.append((order_tick, id_key(table_id), id_key(cid), cid, res))
    for oid, dish in dishes_by_order.items():
        if oid not in customers_by_id:
            raise BadInput(f"món trên bếp/tay tham chiếu order_id không tồn tại: {oid}")
        raw_c, state, order_status, dish_id = customers_by_id[oid]
        if state != "waiting" or order_status != "assigned":
            raise BadInput(f"đơn {oid} ở trạng thái ({state}, {order_status}) không được có món trên bếp/tay")
        if dish["dish_id"] != dish_id:
            raise BadInput(f"món của đơn {oid} không khớp dish_id")
        if "base_price" in raw_c and dish["base_price"] != raw_c["base_price"]:
            raise BadInput(f"base_price của món và đơn {oid} không khớp")
    for cid, (_, _, order_status, _) in customers_by_id.items():
        if order_status == "assigned" and cid not in dishes_by_order:
            raise BadInput(f"customers.{cid}: đơn assigned phải có đúng một món ở bếp hoặc tay")
    # Chỉ kiểm tra giữ chỗ với `stock` khi scenario tự khai `stock` (nếu thiếu `stock`, `--inventory` có thể cấp kho).
    if "stock" in b:
        avail = validate_items(b["stock"], kinds)
        for _, _, _, cid, res in sorted(reserved_entries):
            for k, qty in res.items():
                if avail.get(k, 0) < qty:
                    raise BadInput(f"customers.{cid}: giữ chỗ {k} vượt tồn kho")
                avail[k] -= qty
