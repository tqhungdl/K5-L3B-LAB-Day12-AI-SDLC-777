"""Quán — vòng đời khách, lịch đến, chọn món theo seed, giữ chỗ, kiên nhẫn (v1.0, v1.1 & v1.2).

Giao diện tích hợp với `chonoi/sim/quan.py` (xem docs/plan/phase-3-integration.md):
  - load_customers(sim, scenario) -> list[dict]
  - tick_customers(sim)
  - oldest_reserved(sim) -> dict | None
  - leave_waiting(sim, customer, reason, events)
  - spawn_customer(sim, phase_tick, events)
  - reconcile_spoiled_reservations(sim, spoiled_ids)
  - item_rows(items) / decay_items(...) / fresh_price(...)
"""

from fractions import Fraction
import math

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from ..inventory import KINDS, KINDS_P1, validate_items

try:
    from ..inventory import (
        decay_items as _inv_decay_items,
        fresh_price as _inv_fresh_price,
        item_rows as _inv_item_rows,
        validate_item_list as _inv_validate_item_list,
    )
except ImportError:
    _inv_decay_items = None
    _inv_fresh_price = None
    _inv_item_rows = None
    _inv_validate_item_list = None

TICK = 60
STOVE_STATES = ("idle", "cooking", "ready")
CUSTOMER_STATES = ("waiting", "eating")
ORDER_STATUSES = ("reserved", "assigned", "unfulfillable", "served")
CUSTOMER_KEYS = {
    "id", "table_id", "dish_id", "order_tick", "state",
    "patience_ticks_left", "eat_ticks_left", "order_status",
    "reserved", "base_price", "tip",
}
DISH_KEYS = {"order_id", "dish_id", "base_price"}
ITEM_KEYS = {"id", "kind", "fresh"}


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _nonneg_int(name: str, v):
    if not _is_int(v) or v < 0:
        raise BadInput(f"{name} phải là số nguyên không âm")
    return v


def _pos_int(name: str, v):
    if not _is_int(v) or v <= 0:
        raise BadInput(f"{name} phải là số nguyên dương")
    return v


def exact_fresh(item: dict) -> Fraction:
    """Trả độ tươi dạng phân số chính xác để tránh sai số float quanh ngưỡng 30 và phép floor."""
    f = item.get("_fresh")
    if isinstance(f, Fraction):
        return f
    return Fraction(str(item["fresh"]))


def _fresh_json_value(frac: Fraction):
    return int(frac) if frac.denominator == 1 else float(frac)


def _attach_exact(row: dict) -> dict:
    frac = exact_fresh(row)
    return {"id": row["id"], "kind": row["kind"], "fresh": _fresh_json_value(frac), "_fresh": frac}


def validate_item_list(rows, kinds=KINDS) -> list[dict]:
    if _inv_validate_item_list is not None:
        validated = _inv_validate_item_list(rows, kinds=kinds)
        return [_attach_exact(r) for r in validated]
    if not isinstance(rows, list):
        raise BadInput("items phải là mảng cá thể [{id,kind,fresh}] ở v1.2")
    seen = set()
    out = []
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            raise BadInput(f"items[{i}] phải là object")
        if set(r.keys()) != ITEM_KEYS:
            raise BadInput(f"items[{i}] phải có đúng 3 khóa id, kind, fresh")
        iid = r["id"]
        if not isinstance(iid, str) or not iid:
            raise BadInput(f"items[{i}].id phải là chuỗi khác rỗng")
        if iid in seen:
            raise BadInput(f"items: id trùng {iid}")
        seen.add(iid)
        kind = r["kind"]
        if kind not in kinds:
            raise BadInput(f"items.{iid}: nguyên liệu lạ {kind!r}")
        fresh = r["fresh"]
        if not _is_num(fresh) or not (0 <= fresh <= 100):
            raise BadInput(f"items.{iid}: fresh phải là số hữu hạn trong [0, 100]")
        out.append(_attach_exact(r))
    return out


def item_rows(items: list[dict]) -> list[dict]:
    if _inv_item_rows is not None:
        return _inv_item_rows(items)
    return [{"id": it["id"], "kind": it["kind"], "fresh": _fresh_json_value(exact_fresh(it))} for it in items]


def decay_items(items: list[dict], decay_per_s, tick_hz, spoiled_below, location: str, events: list) -> set[str]:
    if _inv_decay_items is not None:
        return _inv_decay_items(items, decay_per_s, tick_hz, spoiled_below, location, events)
    step_decay = Fraction(str(decay_per_s)) / Fraction(int(tick_hz))
    threshold = Fraction(str(spoiled_below))
    newly_spoiled = []
    for it in items:
        prev = exact_fresh(it)
        nxt = max(Fraction(0), prev - step_decay)
        it["_fresh"] = nxt
        it["fresh"] = _fresh_json_value(nxt)
        if prev >= threshold and nxt < threshold:
            newly_spoiled.append(it)
    spoiled_ids = set()
    for it in sort_by_id(newly_spoiled):
        spoiled_ids.add(it["id"])
        events.append(("spoiled", {"item_id": it["id"], "kind": it["kind"], "location": location}))
    return spoiled_ids


def fresh_price(list_price: int, items: list[dict]) -> int:
    if _inv_fresh_price is not None:
        return _inv_fresh_price(list_price, items)
    if not items:
        return 0
    total = sum((exact_fresh(it) for it in items), Fraction(0))
    return math.floor(Fraction(int(list_price)) * total / Fraction(100 * len(items)))


def _use_freshness(sim) -> bool:
    return bool(getattr(sim, "use_freshness", False))


def _spoiled_threshold(sim) -> Fraction:
    f = getattr(sim, "freshness", None) or {}
    return Fraction(str(f.get("spoiled_below", 30)))


def _valid_kinds(sim) -> tuple[str, ...]:
    kinds = set(KINDS_P1)
    full_menu = getattr(sim, "full_menu", sim.menu)
    for dish in full_menu.values():
        kinds.update(dish.get("recipe", {}).keys())
    return tuple(sorted(kinds))


def _validate_dish_payload(name: str, dish, menu: dict) -> dict:
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
        raise BadInput(f"{name}.dish_id không thuộc thực đơn hiện hành: {dish['dish_id']!r}")
    _pos_int(f"{name}.base_price", dish["base_price"])
    return dish


def _norm_items(items: dict) -> dict:
    return {k: items[k] for k in sorted(items) if items[k] > 0}


def _all_reserved_ids(sim, exclude_customer_id=None) -> set[str]:
    used = set()
    for c in sim.customers:
        if exclude_customer_id is not None and c["id"] == exclude_customer_id:
            continue
        res = c.get("reserved")
        if isinstance(res, list):
            used.update(res)
    return used


def _pick_freshest_for_recipe(stock_items: list[dict], recipe: dict, used_ids: set[str], threshold: Fraction):
    """Chọn các cá thể chưa ươn tươi nhất (hòa theo id_key) đáp ứng `recipe`. Trả list[str] hoặc None."""
    by_kind = {}
    for it in stock_items:
        if it["id"] in used_ids:
            continue
        if exact_fresh(it) < threshold:
            continue
        by_kind.setdefault(it["kind"], []).append(it)
    picked = []
    for kind in sorted(recipe):
        need = recipe[kind]
        if need <= 0:
            continue
        pool = by_kind.get(kind, [])
        if len(pool) < need:
            return None
        pool.sort(key=lambda it: (-exact_fresh(it), id_key(it["id"])))
        picked.extend(it["id"] for it in pool[:need])
    picked.sort(key=id_key)
    return picked


def available_stock(sim) -> dict:
    """Trả map đếm nguyên liệu khả dụng (chưa giữ chỗ; ở v1.2 chỉ tính cá thể chưa ươn)."""
    if _use_freshness(sim):
        used = _all_reserved_ids(sim)
        threshold = _spoiled_threshold(sim)
        counts = {}
        for it in sim.stock:
            if it["id"] in used or exact_fresh(it) < threshold:
                continue
            counts[it["kind"]] = counts.get(it["kind"], 0) + 1
        return {k: counts[k] for k in sorted(counts) if counts[k] > 0}
    avail = {k: v for k, v in sim.stock.items() if v > 0}
    for c in sim.customers:
        for k, qty in c.get("reserved", {}).items():
            if qty > 0:
                avail[k] = avail.get(k, 0) - qty
    return {k: v for k, v in sorted(avail.items()) if v > 0}


def load_customers(sim, scenario: dict) -> list[dict]:
    """Dựng khách từ scenario, điền mặc định, cấp giữ chỗ còn thiếu và kiểm mâu thuẫn.

    Hỗ trợ cả v1.1 (`stock`/`reserved` là dict đếm) và v1.2 (`stock` là mảng cá thể, `reserved` là mảng ID).
    Ném `BadInput` (mã thoát 2) nếu fixture mâu thuẫn với kho thực, thực đơn, bếp, bàn hoặc tay.
    """
    menu = sim.menu
    valid_kinds = _valid_kinds(sim)
    v12 = _use_freshness(sim)
    threshold = _spoiled_threshold(sim)

    if v12:
        sim.stock = validate_item_list(sim.stock, kinds=valid_kinds)
        stock_by_id = {it["id"]: it for it in sim.stock}
    else:
        sim.stock = _norm_items(validate_items(sim.stock, kinds=valid_kinds))
        stock_by_id = {}

    known_tables = {tb["id"] for tb in sim.tables}
    patience_max = int(round(sim.t["patience_s"] * TICK))

    # 1. Thu thập và kiểm tra tất cả món đang nằm trên bếp và trên tay.
    dishes_by_order = {}
    for s in sim.stoves:
        sid = s.get("id", "?")
        state = s.get("state", "idle")
        if state not in STOVE_STATES:
            raise BadInput(f"stoves.{sid}: state không hợp lệ ({state!r})")
        dish = s.get("dish")
        cook_left = _nonneg_int(f"stoves.{sid}.cook_ticks_left", s.get("cook_ticks_left", 0))
        ready_ticks = _nonneg_int(f"stoves.{sid}.ready_ticks", s.get("ready_ticks", 0))
        if state == "idle":
            if dish is not None or cook_left != 0 or ready_ticks != 0:
                raise BadInput(f"stoves.{sid}: bếp idle không được có món hoặc timer dương")
        elif state == "cooking":
            if dish is None:
                raise BadInput(f"stoves.{sid}: bếp cooking phải có dish")
            _validate_dish_payload(f"stoves.{sid}.dish", dish, menu)
            if cook_left <= 0 or ready_ticks != 0:
                raise BadInput(f"stoves.{sid}: bếp cooking phải có cook_ticks_left > 0 và ready_ticks = 0")
        elif state == "ready":
            if dish is None:
                raise BadInput(f"stoves.{sid}: bếp ready phải có dish")
            _validate_dish_payload(f"stoves.{sid}.dish", dish, menu)
            if cook_left != 0:
                raise BadInput(f"stoves.{sid}: bếp ready phải có cook_ticks_left = 0")
        if dish is not None:
            oid = dish["order_id"]
            if oid in dishes_by_order:
                raise BadInput(f"đơn {oid} xuất hiện trên nhiều bếp")
            dishes_by_order[oid] = dish

    if sim.hand is not None:
        _validate_dish_payload("hand", sim.hand, menu)
        oid = sim.hand["order_id"]
        if oid in dishes_by_order:
            raise BadInput(f"bếp và tay cùng giữ đơn {oid}")
        dishes_by_order[oid] = sim.hand

    # 2. Dựng và kiểm tra từng khách trong scenario.
    raw_customers = scenario.get("customers", [])
    if not isinstance(raw_customers, list):
        raise BadInput("customers phải là mảng")

    seen_ids = set()
    used_tables = set()
    built = []
    explicit_base_price = {}
    auto_reserve_ids = set()
    explicit_reserved_item_ids = set()

    for raw in raw_customers:
        if not isinstance(raw, dict):
            raise BadInput("mỗi phần tử trong customers phải là object")
        extra = set(raw) - CUSTOMER_KEYS
        if extra:
            raise BadInput(f"customers có trường lạ/chưa hỗ trợ: {sorted(extra)}")
        cid = raw.get("id")
        if not isinstance(cid, str) or not cid:
            raise BadInput("customers: mỗi khách cần id (chuỗi khác rỗng)")
        if cid in seen_ids:
            raise BadInput(f"customers: id trùng {cid}")
        seen_ids.add(cid)

        table_id = raw.get("table_id")
        if not isinstance(table_id, str) or table_id not in known_tables:
            raise BadInput(f"customers.{cid}: table_id không tồn tại ({table_id!r})")
        if table_id in used_tables:
            raise BadInput(f"hai khách cùng ngồi bàn {table_id}")
        used_tables.add(table_id)

        dish_id = raw.get("dish_id")
        if not isinstance(dish_id, str) or dish_id not in menu:
            raise BadInput(f"customers.{cid}: dish_id không thuộc thực đơn hiện hành ({dish_id!r})")

        order_tick = _nonneg_int(f"customers.{cid}.order_tick", raw.get("order_tick", 0))
        state = raw.get("state", "waiting")
        if state not in CUSTOMER_STATES:
            raise BadInput(f"customers.{cid}: state không hợp lệ ({state!r})")
        order_status = raw.get("order_status", "reserved")
        if order_status not in ORDER_STATUSES:
            raise BadInput(f"customers.{cid}: order_status không hợp lệ ({order_status!r})")

        patience_left = _nonneg_int(
            f"customers.{cid}.patience_ticks_left",
            raw.get("patience_ticks_left", patience_max),
        )
        eat_left = _nonneg_int(f"customers.{cid}.eat_ticks_left", raw.get("eat_ticks_left", 0))

        recipe = _norm_items(menu[dish_id]["recipe"])
        if v12:
            if "reserved" in raw:
                raw_res = raw["reserved"]
                if not isinstance(raw_res, list):
                    raise BadInput(f"customers.{cid}: reserved phải là mảng ID cá thể ở v1.2")
                res_ids = []
                local_seen = set()
                for iid in raw_res:
                    if not isinstance(iid, str) or not iid:
                        raise BadInput(f"customers.{cid}: id trong reserved phải là chuỗi khác rỗng")
                    if iid in local_seen:
                        raise BadInput(f"customers.{cid}: id trùng trong reserved ({iid})")
                    local_seen.add(iid)
                    res_ids.append(iid)
                if order_status == "reserved":
                    counts = {}
                    for iid in res_ids:
                        if iid not in stock_by_id:
                            raise BadInput(f"customers.{cid}: reserved tham chiếu id không có trong kho ({iid})")
                        if iid in explicit_reserved_item_ids:
                            raise BadInput(f"customers.{cid}: cá thể {iid} bị giữ trùng giữa các đơn")
                        it = stock_by_id[iid]
                        if exact_fresh(it) < threshold:
                            raise BadInput(f"customers.{cid}: cá thể {iid} đã ươn, không thể giữ chỗ")
                        explicit_reserved_item_ids.add(iid)
                        counts[it["kind"]] = counts.get(it["kind"], 0) + 1
                    if _norm_items(counts) != recipe:
                        raise BadInput(f"customers.{cid}: reserved khác công thức món {dish_id}")
                    res = sorted(res_ids, key=id_key)
                else:
                    if res_ids:
                        raise BadInput(f"customers.{cid}: đơn {order_status} phải có reserved rỗng")
                    res = []
            else:
                res = []
                if order_status == "reserved":
                    auto_reserve_ids.add(cid)
        else:
            if "reserved" in raw:
                res = _norm_items(validate_items(raw["reserved"], kinds=valid_kinds))
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
            if "base_price" not in raw or "tip" not in raw:
                raise BadInput(f"customers.{cid}: khách eating phải khai base_price và tip đã chốt")
            base_price = _pos_int(f"customers.{cid}.base_price", raw["base_price"])
            tip = _nonneg_int(f"customers.{cid}.tip", raw["tip"])
        else:
            if order_status == "served":
                raise BadInput(f"customers.{cid}: khách waiting không được có order_status = 'served'")
            if eat_left != 0:
                raise BadInput(f"customers.{cid}: khách waiting phải có eat_ticks_left = 0")
            tip = _nonneg_int(f"customers.{cid}.tip", raw.get("tip", 0))
            if tip != 0:
                raise BadInput(f"customers.{cid}: khách waiting chưa chốt boa (tip phải = 0)")
            if "base_price" in raw:
                base_price = _nonneg_int(f"customers.{cid}.base_price", raw["base_price"])
                explicit_base_price[cid] = True
            else:
                base_price = 0
                explicit_base_price[cid] = False

        built.append({
            "id": cid,
            "table_id": table_id,
            "dish_id": dish_id,
            "order_tick": order_tick,
            "state": state,
            "patience_ticks_left": patience_left,
            "eat_ticks_left": eat_left,
            "order_status": order_status,
            "reserved": res,
            "base_price": base_price,
            "tip": tip,
        })

    # 3. Đối chiếu liên kết giữa món ở bếp/tay và đơn của khách.
    by_id = {c["id"]: c for c in built}
    for oid, dish in dishes_by_order.items():
        if oid not in by_id:
            raise BadInput(f"món trên bếp/tay tham chiếu order_id không tồn tại: {oid}")
        c = by_id[oid]
        if c["state"] != "waiting" or c["order_status"] != "assigned":
            raise BadInput(f"đơn {oid} ở trạng thái ({c['state']}, {c['order_status']}) không được có món trên bếp/tay")
        if dish["dish_id"] != c["dish_id"]:
            raise BadInput(f"món của đơn {oid} không khớp dish_id ({dish['dish_id']} != {c['dish_id']})")
        if explicit_base_price.get(oid):
            if dish["base_price"] != c["base_price"]:
                raise BadInput(f"base_price của món và đơn {oid} không khớp")
        else:
            c["base_price"] = dish["base_price"]

    for c in built:
        if c["order_status"] == "assigned" and c["id"] not in dishes_by_order:
            raise BadInput(f"customers.{c['id']}: đơn assigned phải có đúng một món ở bếp hoặc tay")

    # 4. Cấp giữ chỗ còn thiếu / kiểm tồn kho theo thứ tự (order_tick, id bàn).
    if v12:
        used_item_ids = set(explicit_reserved_item_ids)
        for c in sorted(built, key=lambda x: (x["order_tick"], id_key(x["table_id"]), id_key(x["id"]))):
            if c["id"] not in auto_reserve_ids:
                continue
            recipe = _norm_items(menu[c["dish_id"]]["recipe"])
            picked = _pick_freshest_for_recipe(sim.stock, recipe, used_item_ids, threshold)
            if picked is None:
                raise BadInput(f"customers.{c['id']}: không đủ cá thể chưa ươn để giữ chỗ cho món {c['dish_id']}")
            c["reserved"] = picked
            used_item_ids.update(picked)
    else:
        avail = {k: v for k, v in sim.stock.items() if v > 0}
        for c in sorted(built, key=lambda x: (x["order_tick"], id_key(x["table_id"]), id_key(x["id"]))):
            for k, qty in c["reserved"].items():
                if avail.get(k, 0) < qty:
                    raise BadInput(f"customers.{c['id']}: giữ chỗ {k} vượt tồn kho")
                avail[k] -= qty

    return sort_by_id(built)


def reconcile_spoiled_reservations(sim, spoiled_ids: set[str]):
    """Xử lý các đơn `reserved` bị ảnh hưởng bởi cá thể vừa ươn theo (order_tick, id bàn).

    Với mỗi đơn bị ảnh hưởng: nhả toàn bộ phần giữ hiện có rồi thử giữ lại ĐÚNG MỘT LẦN
    từ hàng chưa ươn tươi nhất theo loại (hòa theo ID). Thiếu -> chuyển `unfulfillable`.
    """
    if not _use_freshness(sim) or not spoiled_ids:
        return
    threshold = _spoiled_threshold(sim)
    affected = [
        c for c in sim.customers
        if c["state"] == "waiting"
        and c["order_status"] == "reserved"
        and any(iid in spoiled_ids for iid in c.get("reserved", []))
    ]
    affected.sort(key=lambda c: (c["order_tick"], id_key(c["table_id"]), id_key(c["id"])))
    for c in affected:
        c["reserved"] = []
        used_ids = _all_reserved_ids(sim, exclude_customer_id=c["id"])
        recipe = _norm_items(sim.menu[c["dish_id"]]["recipe"])
        picked = _pick_freshest_for_recipe(sim.stock, recipe, used_ids, threshold)
        if picked is not None:
            c["reserved"] = picked
        else:
            c["order_status"] = "unfulfillable"


def tick_customers(sim):
    """Giảm kiên nhẫn của khách đang chờ và timer ăn của khách đang ăn (không âm)."""
    for c in sim.customers:
        if c["state"] == "waiting":
            c["patience_ticks_left"] = max(0, c["patience_ticks_left"] - 1)
        elif c["state"] == "eating":
            c["eat_ticks_left"] = max(0, c["eat_ticks_left"] - 1)


def oldest_reserved(sim):
    """Trả khách có đơn `reserved` cũ nhất theo `order_tick`, rồi `id` bàn; None nếu không có."""
    candidates = [c for c in sim.customers if c["state"] == "waiting" and c["order_status"] == "reserved"]
    if not candidates:
        return None
    return min(candidates, key=lambda c: (c["order_tick"], id_key(c["table_id"]), id_key(c["id"])))


def leave_waiting(sim, customer: dict, reason: str, events: list):
    """Nhả phần giữ thô, xóa khách đang chờ, cập nhật uy tín nếu `patience`, phát `customer_left`."""
    customer["reserved"] = [] if _use_freshness(sim) else {}
    sim.customers[:] = [c for c in sim.customers if c["id"] != customer["id"]]
    if reason == "patience":
        rep = sim.reputation + sim.t["left_reputation_delta"]
        sim.reputation = max(sim.t["reputation_min"], min(sim.t["reputation_max"], rep))
    events.append(("customer_left", {
        "order_id": customer["id"],
        "table_id": customer["table_id"],
        "reason": reason,
        "reputation": sim.reputation,
    }))


def spawn_customer(sim, phase_tick: int, events: list):
    """Xét lịch sinh khách, bàn trống, kho khả dụng và `random_customers`."""
    if not getattr(sim, "random_customers", True):
        return None
    first = int(sim.t["first_customer_tick"])
    interval = int(round(sim.t["customer_interval_s"] * TICK))
    if phase_tick < first or (phase_tick - first) % interval != 0:
        return None

    occupied = {c["table_id"] for c in sim.customers}
    free_tables = [tb for tb in sort_by_id(sim.tables) if tb["id"] not in occupied]
    if not free_tables:
        return None
    table = free_tables[0]

    avail = available_stock(sim)
    cookable = [
        dish_id
        for dish_id in sorted(sim.menu.keys())
        if all(avail.get(k, 0) >= need for k, need in sim.menu[dish_id]["recipe"].items())
    ]
    if not cookable:
        events.append(("no_dish", {}))
        return None

    dish_id = sim.rng.get("customer_order").choice(cookable)
    recipe = _norm_items(sim.menu[dish_id]["recipe"])
    if _use_freshness(sim):
        used_ids = _all_reserved_ids(sim)
        reserved = _pick_freshest_for_recipe(sim.stock, recipe, used_ids, _spoiled_threshold(sim))
    else:
        reserved = dict(recipe)

    customer = {
        "id": sim.ids.new("C"),
        "table_id": table["id"],
        "dish_id": dish_id,
        "order_tick": phase_tick,
        "state": "waiting",
        "patience_ticks_left": int(round(sim.t["patience_s"] * TICK)),
        "eat_ticks_left": 0,
        "order_status": "reserved",
        "reserved": reserved,
        "base_price": 0,
        "tip": 0,
    }
    sim.customers.append(customer)
    events.append(("customer_arrived", {
        "order_id": customer["id"],
        "table_id": customer["table_id"],
        "dish_id": customer["dish_id"],
    }))
    return customer