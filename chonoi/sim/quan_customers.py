"""Quán — vòng đời khách, lịch đến, chọn món theo seed, giữ chỗ, kiên nhẫn (Phase 1 & Phase 2).

Giao diện tích hợp với `chonoi/sim/quan.py` (xem docs/plan/phase-2-integration.md):
  - load_customers(sim, scenario) -> list[dict]
  - tick_customers(sim)
  - oldest_reserved(sim) -> dict | None
  - leave_waiting(sim, customer, reason, events)
  - spawn_customer(sim, phase_tick, events)
"""

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from ..inventory import KINDS_P1, validate_items

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


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _nonneg_int(name: str, v):
    if not _is_int(v) or v < 0:
        raise BadInput(f"{name} phải là số nguyên không âm")
    return v


def _pos_int(name: str, v):
    if not _is_int(v) or v <= 0:
        raise BadInput(f"{name} phải là số nguyên dương")
    return v


def _valid_kinds(sim) -> tuple[str, ...]:
    """Tập ID nguyên liệu hợp lệ theo thực đơn toàn cục (4 loại v1.0 hoặc 6 loại v1.1)."""
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


def available_stock(sim) -> dict:
    """Kho khả dụng = tồn vật lý (`sim.stock`) trừ tổng phần giữ (`reserved`) của mọi khách."""
    avail = {k: v for k, v in sim.stock.items() if v > 0}
    for c in sim.customers:
        for k, qty in c.get("reserved", {}).items():
            if qty > 0:
                avail[k] = avail.get(k, 0) - qty
    return {k: v for k, v in sorted(avail.items()) if v > 0}


def load_customers(sim, scenario: dict) -> list[dict]:
    """Dựng khách từ scenario, điền mặc định, cấp giữ chỗ còn thiếu và kiểm mâu thuẫn.

    Yêu cầu: `sim.menu` (đã lọc theo kế hoạch ngày nếu có), `sim.stoves`, `sim.tables`,
    `sim.stock`, `sim.hand` đã được dựng trước khi gọi.
    Ném `BadInput` (mã thoát 2) nếu fixture mâu thuẫn với kho thực, thực đơn, bếp, bàn hoặc tay.
    """
    menu = sim.menu
    valid_kinds = _valid_kinds(sim)
    sim.stock = _norm_items(validate_items(sim.stock, kinds=valid_kinds))
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

    # 4. Kiểm tra giữ chỗ theo thứ tự (order_tick, id bàn) không vượt tồn vật lý.
    avail = {k: v for k, v in sim.stock.items() if v > 0}
    for c in sorted(built, key=lambda x: (x["order_tick"], id_key(x["table_id"]), id_key(x["id"]))):
        for k, qty in c["reserved"].items():
            if avail.get(k, 0) < qty:
                raise BadInput(f"customers.{c['id']}: giữ chỗ {k} vượt tồn kho")
            avail[k] -= qty

    return sort_by_id(built)


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
    customer["reserved"] = {}
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
    """Xét lịch sinh khách, bàn trống, kho khả dụng và `random_customers`.

    - Không tới lịch hoặc `random_customers` tắt hoặc hết bàn trống -> bỏ lượt (không phát `no_dish`).
    - Có bàn trống nhưng không đủ nguyên liệu cho món nào trong `sim.menu` -> phát `no_dish` (`{}`).
    - Chọn đều theo seed (`Streams.get("customer_order")`) trong các món đủ nguyên liệu (sắp Unicode),
      giữ đúng công thức ngay và phát `customer_arrived`.
    """
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
    customer = {
        "id": sim.ids.new("C"),
        "table_id": table["id"],
        "dish_id": dish_id,
        "order_tick": phase_tick,
        "state": "waiting",
        "patience_ticks_left": int(round(sim.t["patience_s"] * TICK)),
        "eat_ticks_left": 0,
        "order_status": "reserved",
        "reserved": dict(recipe),
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