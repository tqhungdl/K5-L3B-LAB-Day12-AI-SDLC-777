"""File kho đếm v1.1 và file kho cá thể v1.2 với khóa gốc "items".

Đọc: từ chối sai schema / id lạ / số âm (BadInput -> mã 2).
Ghi: bỏ mục bằng 0, qua file tạm cùng thư mục rồi thay thế, byte-ổn-định.
"""

import json
import math
import os
import tempfile
from fractions import Fraction

from .errors import BadInput
from .ids import sort_by_id

KINDS_P1 = ("ca_loc", "ca_linh", "bong_dien_dien", "bong_sung")
FISH_KINDS = ("ca_linh", "ca_loc", "ca_keo")
NODE_KINDS = ("bong_dien_dien", "bong_sung", "keo_neo")
KINDS = FISH_KINDS + NODE_KINDS


def new_item(ids, kind, initial):
    return {"id": ids.new("I"), "kind": kind, "fresh": initial}


def decay_items(items, decay_per_s, tick_hz, spoiled_below, location, events) -> set[str]:
    """Hao tươi chính xác và phát sự kiện theo ID cho hàng vừa qua ngưỡng."""
    decay = Fraction(str(decay_per_s)) / tick_hz
    threshold = Fraction(str(spoiled_below))
    spoiled = set()
    for item in sort_by_id(items):
        before = Fraction(str(item["fresh"]))
        after = max(0, before - decay)
        item["fresh"] = after
        if before >= threshold > after:
            spoiled.add(item["id"])
            events.append(("spoiled", {
                "item_id": item["id"], "kind": item["kind"], "location": location,
            }))
    return spoiled


def item_rows(items):
    """Sao dữ liệu kho sang số JSON, giữ nguyên thứ tự và phía ngưỡng."""
    rows = []
    for item in items:
        fresh = item["fresh"]
        if isinstance(fresh, Fraction):
            value = float(fresh)
            # Làm tròn lên có thể biến hàng vừa ươn thành hàng đúng ngưỡng.
            if Fraction(str(value)) > fresh:
                value = math.nextafter(value, -math.inf)
            fresh = value
        rows.append({"id": item["id"], "kind": item["kind"], "fresh": fresh})
    return rows


def validate_items(items, kinds=KINDS):
    if not isinstance(items, dict):
        raise BadInput("items phải là object")
    out = {}
    for k, v in items.items():
        if k not in kinds:
            raise BadInput(f"nguyên liệu lạ: {k}")
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise BadInput(f"số lượng không hợp lệ cho {k}: {v!r}")
        if v > 0:
            out[k] = v
    return out


def validate_item_list(rows, kinds=KINDS):
    if not isinstance(rows, list):
        raise BadInput("items phải là mảng cá thể")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"id", "kind", "fresh"}:
            raise BadInput("cá thể kho phải có đúng id, kind, fresh")
        ident, kind, fresh = row["id"], row["kind"], row["fresh"]
        if not isinstance(ident, str) or not ident or ident in seen:
            raise BadInput(f"id cá thể rỗng, sai kiểu hoặc trùng: {ident!r}")
        if not isinstance(kind, str) or kind not in kinds:
            raise BadInput(f"nguyên liệu lạ: {kind!r}")
        if type(fresh) not in (int, float) or not 0 <= fresh <= 100:
            raise BadInput(f"fresh phải là số hữu hạn trong [0, 100]: {fresh!r}")
        seen.add(ident)
    return [row.copy() for row in rows]


def new_item(ids, kind, initial):
    return {"id": ids.new("I"), "kind": kind, "fresh": initial}


def decay_items(items, decay_per_s, tick_hz, spoiled_below, location, events) -> set[str]:
    decrement = Fraction(str(decay_per_s)) / tick_hz
    spoiled = []
    for item in items:
        before = Fraction(str(item["fresh"]))
        item["fresh"] = max(0, before - decrement)
        if item["fresh"] < spoiled_below <= before:
            spoiled.append(item)
    for item in sort_by_id(spoiled):
        events.append(("spoiled", {"item_id": item["id"], "kind": item["kind"], "location": location}))
    return {item["id"] for item in spoiled}


def item_rows(items):
    return [
        {"id": item["id"], "kind": item["kind"],
         "fresh": fresh_number(item["fresh"])}
        for item in items
    ]


def fresh_number(value):
    if not isinstance(value, Fraction):
        return value
    number = float(value)
    # Preserve which side of an integral threshold the exact value falls on.
    if number.is_integer() and value < number:
        return math.nextafter(number, -math.inf)
    return number


def fresh_price(list_price, items) -> int:
    total = sum(Fraction(str(item["fresh"])) for item in items)
    return list_price * total // (100 * len(items))


def read_inventory(path: str, kinds=KINDS, *, contract_version="1.1"):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được file kho {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    if contract_version == "1.2":
        return sort_by_id(validate_item_list(data["items"], kinds))
    return validate_items(data["items"], kinds)


def hold_to_items(hold: list) -> dict:
    """Khoang (mảng id theo thứ tự nhặt) -> object đếm, sắp theo id nguyên liệu."""
    counts = {}
    for k in hold:
        counts[k] = counts.get(k, 0) + 1
    return {k: counts[k] for k in sorted(counts)}


def write_inventory(path: str, items, *, contract_version="1.1"):
    if contract_version == "1.2":
        items = sort_by_id(validate_item_list(items))
    else:
        items = {k: items[k] for k in sorted(items) if items[k] > 0}
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".inv-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"items": items}, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
