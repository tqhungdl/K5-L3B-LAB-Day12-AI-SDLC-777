"""Buổi đêm — Cửa hàng Má Tư (Shop). (Phase 2 & Phase 3 - Test Contract v1.1 & v1.2)

Quản lý nâng cấp cuối ngày:
- Mua nâng cấp: 'oxygen', 'hp' (theo cấp tăng dần 1 -> 2).
- Trừ money, giữ nguyên earned và score.
- Đóng Shop: nhận phím 'shop_done' hoặc hết giờ (600 tick).
- Khi đóng Shop, kho dư từ buổi tối bị bỏ.
- Hỗ trợ cả kho cá thể (v1.2: mảng) và kho đếm (v1.1: dict).
"""

from ..ids import sort_by_id

DEFAULT_UPGRADES = {
    "oxygen": [
        {"level": 1, "price": 200, "oxygen_max_s": 45},
        {"level": 2, "price": 400, "oxygen_max_s": 60},
    ],
    "hp": [
        {"level": 1, "price": 250, "hp_max": 4},
        {"level": 2, "price": 500, "hp_max": 5},
    ]
}


class ShopSim:
    mode = "shop"
    phase = "shop"

    def __init__(self, tuning, stock, money, earned, reputation, upgrades=None):
        self.tuning = tuning
        shop_tuning = tuning.get("shop", {})
        self.max_ticks = int(shop_tuning.get("max_ticks", 600))
        self.time_left_ticks = self.max_ticks
        self.upgrades_config = shop_tuning.get("upgrades", DEFAULT_UPGRADES)

        if isinstance(stock, list):
            self.stock = [dict(it) for it in stock]
        else:
            self.stock = dict(stock or {})

        self.money = int(money)
        self.earned = int(earned)
        self.reputation = float(reputation)
        self.upgrades = dict(upgrades or {})  # map {upgrade_id: level}

        self.done = False
        self.reason = None

    def snapshot(self) -> dict:
        if isinstance(self.stock, list):
            stock_data = sort_by_id([dict(it) for it in self.stock])
        else:
            stock_data = {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0}
        return {
            "stock": stock_data,
            "time_left_ticks": self.time_left_ticks,
            "money": self.money,
            "upgrades": dict(self.upgrades)
        }

    def step(self, inp):
        events = []
        if self.done:
            return events

        self.time_left_ticks = max(0, self.time_left_ticks - 1)

        # 1. Xử lý lệnh buy nếu có (trước shop_done)
        buy_cmd = getattr(inp, "buy", None)
        if buy_cmd:
            self._handle_buy(buy_cmd, events)

        # 2. Xử lý đóng shop: nút shop_done hoặc hết giờ
        if inp.pressed("shop_done"):
            self.done = True
            self.reason = "done"
            events.append(("shop_end", {"reason": "done"}))
        elif self.time_left_ticks <= 0:
            self.done = True
            self.reason = "time"
            events.append(("shop_end", {"reason": "time"}))

        return events

    def _handle_buy(self, item: str, events):
        if item not in self.upgrades_config:
            events.append(("buy_failed", {"action": item, "reason": "unknown"}))
            return

        current_level = self.upgrades.get(item, 0)
        levels = self.upgrades_config[item]
        if current_level >= len(levels):
            events.append(("buy_failed", {"action": item, "reason": "max_level"}))
            return

        next_cfg = levels[current_level]
        price = next_cfg["price"]
        next_level = next_cfg["level"]

        if self.money < price:
            events.append(("buy_failed", {"action": item, "reason": "funds"}))
            return

        self.money -= price
        self.upgrades[item] = next_level
        events.append(("bought", {
            "upgrade": item,
            "level": next_level,
            "price": price,
            "money": self.money
        }))
