"""Buổi tối — Mở Quán (Contract v1.0 & v1.1).

Hỗ trợ 2 bếp (`B1`, `B2`), 4 bàn (`T1`–`T4`), 6 món và lọc thực đơn theo kế hoạch ngày
qua tham số `allowed_dishes` khi chạy trong chế độ `day`.
Giữ nguyên thứ tự xử lý v1.0: giảm timer -> bếp chín -> di chuyển/tương tác -> khách/đóng ca -> sinh khách.
"""

import math

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from .quan_customers import (
    leave_waiting,
    load_customers,
    oldest_reserved,
    spawn_customer,
    tick_customers,
)
from .ramp import ramp_velocity

TICK = 60.0


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None, *, allowed_dishes=None):
        t = tuning["quan"]
        self.t = t
        self.full_menu = dict(tuning["menu"])
        if allowed_dishes is None:
            self.menu = dict(self.full_menu)
        else:
            allowed_list = list(allowed_dishes)
            unknown = [d for d in allowed_list if d not in self.full_menu]
            if unknown:
                raise BadInput(f"kế hoạch ngày chứa món không thuộc thực đơn: {sorted(set(unknown))}")
            allowed_set = set(allowed_list)
            self.menu = {d: self.full_menu[d] for d in sorted(self.full_menu) if d in allowed_set}
        self.allowed_dishes = set(self.menu.keys())
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        # kho: --inventory (hoặc kho bàn giao từ Day) HOẶC scenario.stock
        self.stock = dict(inventory if inventory is not None else scenario.get("stock", {}))
        raw_hand = scenario.get("hand")
        self.hand = dict(raw_hand) if isinstance(raw_hand, dict) else raw_hand
        self.phase_tick = 0
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * 60)))
        self.random_customers = scenario.get("random_customers", True)
        self.reputation = scenario.get("reputation", t["reputation_initial"])
        self.stoves = [
            dict(
                s,
                pos=[float(c) for c in s["pos"]],
                state=s.get("state", "idle"),
                dish=dict(s["dish"]) if isinstance(s.get("dish"), dict) else s.get("dish"),
                cook_ticks_left=s.get("cook_ticks_left", 0),
                ready_ticks=s.get("ready_ticks", 0),
            )
            for s in self._merge(t["stoves"], scenario.get("stoves", []))
        ]
        self.tables = [
            dict(tb, pos=[float(c) for c in tb["pos"]])
            for tb in self._merge(t["tables"], scenario.get("tables", []))
        ]
        self.customers = load_customers(self, scenario)
        for e in self.customers:
            ids.reserve(e["id"])
        self.money = 0
        self.earned = 0
        self.shift_earned = 0
        self.done = False
        self.reason = None

    @staticmethod
    def _merge(defaults, updates):
        by_id = {d["id"]: dict(d) for d in defaults}
        for u in updates:
            if u["id"] not in by_id:
                raise BadInput(f"id bếp/bàn không tồn tại: {u['id']}")
            by_id[u["id"]].update(u)
        return sort_by_id(list(by_id.values()))

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": list(self.pos), "vel": list(self.vel)},
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
            "hand": dict(self.hand) if isinstance(self.hand, dict) else self.hand,
            "stoves": [
                {
                    "id": s["id"],
                    "pos": list(s["pos"]),
                    "state": s["state"],
                    "dish": dict(s["dish"]) if isinstance(s.get("dish"), dict) else s.get("dish"),
                    "cook_ticks_left": s["cook_ticks_left"],
                    "ready_ticks": s["ready_ticks"],
                }
                for s in sort_by_id(self.stoves)
            ],
            "tables": [
                {"id": tb["id"], "pos": list(tb["pos"]), "customer_id": occupied.get(tb["id"])}
                for tb in sort_by_id(self.tables)
            ],
            "customers": [
                dict(c, reserved=dict(c.get("reserved", {})))
                for c in sort_by_id(self.customers)
            ],
        }

    def _clean_order_items(self, order_id):
        if self.hand and self.hand.get("order_id") == order_id:
            self.hand = None
        for s in self.stoves:
            if s.get("dish") and s["dish"].get("order_id") == order_id:
                s["state"] = "idle"
                s["dish"] = None
                s["cook_ticks_left"] = 0
                s["ready_ticks"] = 0

    def step(self, inp):
        events = []
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)

        # 1. Giảm timer nấu, ăn, kiên nhẫn; chỉ tăng ready_ticks cho món đã ready ở đầu bước.
        for s in self.stoves:
            if s["state"] == "ready":
                s["ready_ticks"] = s.get("ready_ticks", 0) + 1
            elif s["state"] == "cooking":
                s["cook_ticks_left"] = max(0, s.get("cook_ticks_left", 0) - 1)

        tick_customers(self)

        # 2. Xét bếp theo id. Món nấu xong chuyển ready với ready_ticks = 0.
        for s in sort_by_id(self.stoves):
            if s["state"] == "cooking" and s["cook_ticks_left"] == 0:
                s["state"] = "ready"
                s["ready_ticks"] = 0
                dish = s["dish"]
                events.append(("dish_ready", {
                    "stove_id": s["id"],
                    "order_id": dish["order_id"],
                    "dish_id": dish["dish_id"],
                }))

        # 3. Di chuyển rồi xét tối đa một interact
        self._move(inp)
        if inp.pressed("interact"):
            self._handle_interact(events)

        # 4. Theo id bàn: thanh toán khách ăn xong, xử lý khách hết kiên nhẫn hoặc đóng ca
        sorted_tables = sort_by_id(self.tables)
        if self.time_left_ticks > 0:
            for tb in sorted_tables:
                c = next((cust for cust in list(self.customers) if cust["table_id"] == tb["id"]), None)
                if not c:
                    continue
                if c.get("state") == "eating" and c.get("eat_ticks_left", 0) == 0:
                    self._collect_payment(c, tb["id"], "finished_eating", events)
                elif c.get("state") == "waiting" and c.get("patience_ticks_left", 0) == 0:
                    self._clean_order_items(c["id"])
                    leave_waiting(self, c, "patience", events)
        else:
            # Hết ca: khách còn ăn trả ngay (kể cả vừa được giao), khách còn chờ rời với closing
            for tb in sorted_tables:
                c = next((cust for cust in list(self.customers) if cust["table_id"] == tb["id"]), None)
                if not c:
                    continue
                if c.get("state") == "eating":
                    self._collect_payment(c, tb["id"], "closing", events)
                elif c.get("state") == "waiting":
                    self._clean_order_items(c["id"])
                    leave_waiting(self, c, "closing", events)

            self.done = True
            self.reason = "time"
            events.append(("quan_end", {
                "reason": "time",
                "money": self.money,
                "earned": self.earned,
                "shift_earned": self.shift_earned,
                "reputation": self.reputation,
            }))

        # 5. Khách mới theo lịch nếu chưa đóng ca
        if not self.done:
            spawn_customer(self, self.phase_tick, events)

        return events

    def _collect_payment(self, customer, table_id, reason, events):
        base_price = customer.get("base_price", 0)
        tip = customer.get("tip", 0)
        amount = base_price + tip
        self.money += amount
        self.earned += amount
        self.shift_earned += amount
        if tip > 0:
            rep = self.reputation + self.t["tip_reputation"]
            self.reputation = max(self.t["reputation_min"], min(self.t["reputation_max"], rep))
        events.append(("paid", {
            "order_id": customer["id"],
            "table_id": table_id,
            "base_price": base_price,
            "tip": tip,
            "amount": amount,
            "reason": reason,
        }))
        self.customers.remove(customer)

    def _handle_interact(self, events):
        r = self.t["interact_radius"]
        candidates = []
        for s in self.stoves:
            d = math.dist(self.pos, s["pos"])
            if d <= r:
                candidates.append((d, 0, id_key(s["id"]), "stove", s))
        for tb in self.tables:
            d = math.dist(self.pos, tb["pos"])
            if d <= r:
                candidates.append((d, 1, id_key(tb["id"]), "table", tb))

        if not candidates:
            return

        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        _, _, _, kind, obj = candidates[0]

        if kind == "stove":
            s = obj
            if s["state"] == "idle":
                c = oldest_reserved(self)
                if c is not None:
                    dish_id = c["dish_id"]
                    recipe = self.menu[dish_id]["recipe"]
                    cook_s = self.menu[dish_id]["cook_s"]
                    price = self.menu[dish_id]["price"]

                    for k, amt in recipe.items():
                        self.stock[k] = self.stock.get(k, 0) - amt

                    c["reserved"] = {}
                    c["order_status"] = "assigned"
                    c["base_price"] = price

                    s["state"] = "cooking"
                    s["cook_ticks_left"] = int(round(cook_s * TICK))
                    s["ready_ticks"] = 0
                    s["dish"] = {
                        "order_id": c["id"],
                        "dish_id": dish_id,
                        "base_price": price,
                    }

                    items = []
                    for k, cnt in recipe.items():
                        items.extend([k] * cnt)
                    items.sort()

                    events.append(("cook_started", {
                        "stove_id": s["id"],
                        "order_id": c["id"],
                        "dish_id": dish_id,
                        "items": items,
                        "base_price": price,
                    }))
            elif s["state"] == "ready":
                if self.hand is None:
                    self.hand = s["dish"]
                    events.append(("dish_picked", {
                        "stove_id": s["id"],
                        "order_id": self.hand["order_id"],
                        "dish_id": self.hand["dish_id"],
                    }))
                    s["state"] = "idle"
                    s["dish"] = None
                    s["ready_ticks"] = 0

        elif kind == "table":
            tb = obj
            c = next((cust for cust in self.customers if cust["table_id"] == tb["id"]), None)
            if c is not None and c.get("state") == "waiting" and self.hand is not None and self.hand.get("order_id") == c["id"]:
                order_id = c["id"]
                dish_id = c["dish_id"]
                base_price = self.hand["base_price"]
                patience_left = c.get("patience_ticks_left", 0)
                total_patience = int(round(self.t["patience_s"] * TICK))
                ratio = patience_left / total_patience if total_patience > 0 else 0.0

                if ratio >= self.t["tip_min_patience_ratio"]:
                    tip = math.floor(base_price * self.t["tip_rate"])
                else:
                    tip = 0

                c["state"] = "eating"
                c["order_status"] = "served"
                c["eat_ticks_left"] = int(round(self.t["eat_s"] * TICK))
                c["base_price"] = base_price
                c["tip"] = tip
                self.hand = None

                events.append(("served", {
                    "order_id": order_id,
                    "table_id": tb["id"],
                    "dish_id": dish_id,
                    "patience_ticks_left": patience_left,
                    "base_price": base_price,
                    "tip": tip,
                }))

    def _move(self, inp):
        speed = self.t["walk_speed"]
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * speed, mz * speed), int(self.t.get("ramp_max_ticks", 6)))
        b = self.t["bounds"]
        for i, axis in enumerate(("x", "z")):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i], self.vel[i] = lo, max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i], self.vel[i] = hi, min(0.0, self.vel[i])