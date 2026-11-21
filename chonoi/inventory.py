"""File kho (Test Contract): {"items": {id: số nguyên >= 0}}.

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


def read_inventory(path: str, kinds=KINDS) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được file kho {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    return validate_items(data["items"], kinds)


def hold_to_items(hold: list) -> dict:
    """Khoang (mảng id theo thứ tự nhặt) -> object đếm, sắp theo id nguyên liệu."""
    counts = {}
    for k in hold:
        counts[k] = counts.get(k, 0) + 1
    return {k: counts[k] for k in sorted(counts)}


def write_inventory(path: str, items: dict):
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
