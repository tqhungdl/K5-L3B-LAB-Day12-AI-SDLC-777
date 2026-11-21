"""Điều phối trọn vẹn Vòng Ngày (mode: day) — Phase 2 (Test Contract v1.1).

Chu trình mỗi ngày:
    DayIntro/day_start -> day_plan -> gather -> quan -> shop -> (lặp lại hoặc kết thúc)

Hỗ trợ chạy từ 1 đến 5 ngày (--days 1..5).
Giữ tiền, uy tín, nâng cấp qua ngày.
"""

from .gather import GatherSim
from .quan import QuanSim
from .shop import ShopSim

DEFAULT_DAY_DISHES = {
    1: {"ca_loc_nuong_trui": 3, "goi_bong_sung": 3},
    2: {"ca_loc_nuong_trui": 2, "lau_ca_linh_dien_dien": 2},
    3: {"goi_bong_sung": 2, "canh_chua_ca_loc": 2, "ca_keo_nuong": 2},
    4: {"lau_mam": 1, "ca_loc_nuong_trui": 2, "goi_bong_sung": 1},
    5: {"lau_mam": 1, "lau_ca_linh_dien_dien": 1, "ca_loc_nuong_trui": 1},
}


def resolve_day_plans(tuning, overrides=None) -> dict:
    """Tính kế hoạch ngày (D1..D5): dishes và ingredients tính từ công thức."""
    menu = tuning.get("menu", {})
    plans = {}
    overrides = overrides or {}

    for d in range(1, 6):
        if d in overrides and "dishes" in overrides[d]:
            dishes = overrides[d]["dishes"]
        elif d in DEFAULT_DAY_DISHES:
            dishes = DEFAULT_DAY_DISHES[d]
        else:
            dishes = {}

        ingredients = {}
        for dish_id, count in dishes.items():
            dish_info = menu.get(dish_id, {})
            recipe = dish_info.get("recipe", {})
            for ing, req in recipe.items():
                ingredients[ing] = ingredients.get(ing, 0) + req * count

        plans[d] = {
            "dishes": dict(dishes),
            "ingredients": ingredients
        }
    return plans


class DaySim:
    mode = "day"

    def __init__(self, tuning, scenario, streams, ids, days=1):
        self.tuning = tuning
        self.scenario = scenario or {}
        self.streams = streams
        self.ids = ids
        self.days = max(1, min(5, int(days)))

        scenario_day = self.scenario.get("day", {})
        self.day = 1
        self.days_completed = 0
        self.money = scenario_day.get("money", 0)
        self.earned = scenario_day.get("earned", 0)
        self.reputation = scenario_day.get("reputation", tuning["quan"]["reputation_initial"])
        self.upgrades = dict(scenario_day.get("upgrades", {}))
        self.active_upgrades = dict(self.upgrades)

        self.plans = resolve_day_plans(tuning, scenario_day.get("day_plan"))
        self.day_plan = self.plans.get(self.day, {})

        self.phase = "gather"
        self.phase_tick = 0
        self.sim_tick = 0
        self.done = False
        self.reason = None

        # Khởi tạo pha Gather ngày 1
        self.current_sim = self._build_gather_sim()
        self._initial_events = [
            ("day_start", {}),
            ("day_plan", self.day_plan),
            ("phase_start", {})
        ]

    def flush_initial_events(self) -> list:
        evs = self._initial_events
        self._initial_events = []
        return evs

    @property
    def time_left_ticks(self) -> int:
        return getattr(self.current_sim, "time_left_ticks", 0)

    def _build_gather_sim(self):
        sc_gather = dict(self.scenario.get("gather", {}))
        # Truyền day_number và active_upgrades
        try:
            return GatherSim(self.tuning, sc_gather, self.streams, self.ids,
                             day_number=self.day, active_upgrades=self.active_upgrades)
        except TypeError:
            return GatherSim(self.tuning, sc_gather, self.streams, self.ids)

    def _build_quan_sim(self, inventory_items):
        sc_quan = dict(self.scenario.get("quan", {}))
        allowed_dishes = set(self.day_plan.get("dishes", {}).keys())
        try:
            sim = QuanSim(self.tuning, sc_quan, self.streams, self.ids,
                          inventory=inventory_items, allowed_dishes=allowed_dishes)
        except TypeError:
            sim = QuanSim(self.tuning, sc_quan, self.streams, self.ids,
                          inventory=inventory_items)
        sim.money = self.money
        sim.earned = self.earned
        sim.reputation = self.reputation
        return sim

    def _build_shop_sim(self, stock):
        return ShopSim(self.tuning, stock, self.money, self.earned, self.reputation, upgrades=self.upgrades)

    def snapshot(self) -> dict:
        snap = {
            "day": self.day,
            "day_plan": self.day_plan,
            "upgrades": dict(self.upgrades),
            "active_upgrades": dict(self.active_upgrades),
        }
        snap.update(self.current_sim.snapshot())
        return snap

    def step(self, inp):
        events = []
        if self.done:
            return events

        self.phase_tick += 1
        self.sim_tick += 1

        sub_events = self.current_sim.step(inp)
        events.extend(sub_events)

        if self.current_sim.done:
            if self.phase == "gather":
                hold_items = self.current_sim.inventory_items()
                self.phase = "quan"
                self.phase_tick = 0
                events.append(("phase_start", {}))
                self.current_sim = self._build_quan_sim(hold_items)

            elif self.phase == "quan":
                self.money = self.current_sim.money
                self.earned = self.current_sim.earned
                self.reputation = self.current_sim.reputation
                surplus_stock = dict(self.current_sim.stock)

                self.phase = "shop"
                self.phase_tick = 0
                events.append(("phase_start", {}))
                self.current_sim = self._build_shop_sim(surplus_stock)

            elif self.phase == "shop":
                self.money = self.current_sim.money
                self.upgrades = dict(self.current_sim.upgrades)
                self.days_completed += 1

                if self.days_completed < self.days:
                    # Bắt đầu Ngày tiếp theo ngay tại tick này
                    self.day += 1
                    self.active_upgrades = dict(self.upgrades)
                    self.day_plan = self.plans.get(self.day, {})
                    self.phase = "gather"
                    self.phase_tick = 0
                    events.append(("day_start", {}))
                    events.append(("day_plan", self.day_plan))
                    events.append(("phase_start", {}))
                    self.current_sim = self._build_gather_sim()
                else:
                    self.done = True
                    self.reason = "days_complete"

        return events
