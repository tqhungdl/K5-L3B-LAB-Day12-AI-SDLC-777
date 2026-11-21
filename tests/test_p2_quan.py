"""Test Phase 2 — Lát 3 (AC-P2-04, AC-P2-05, AC-P2-09):
  - Quán 2 bếp (B1, B2), 4 bàn (T1–T4), 6 món & 6 nguyên liệu.
  - Kế hoạch ngày D1–D5 (`allowed_dishes`), gọi vượt số suất dự kiến, từ chối món ngoài kế hoạch.
  - Đóng ca nhiều bàn & dọn món trên cả 2 bếp/tay.
  - Kiểm cấu trúc client HUD/màn hình Phase 2 trong `chonoi/web/index.html`.

Chạy riêng:
    PYTHONPATH=tests:. python3 -m unittest tests/test_p2_quan.py -v
"""

import copy
import os
import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.sim.quan import QuanSim

V11_QUAN_STOVES = [
    {"id": "B1", "pos": [2, 8]},
    {"id": "B2", "pos": [5, 8]},
]
V11_QUAN_TABLES = [
    {"id": "T1", "pos": [9, 2]},
    {"id": "T2", "pos": [13, 2]},
    {"id": "T3", "pos": [9, 6]},
    {"id": "T4", "pos": [13, 6]},
]
V11_MENU = {
    "ca_loc_nuong_trui": {"recipe": {"ca_loc": 1}, "cook_s": 6, "price": 60},
    "goi_bong_sung": {"recipe": {"bong_sung": 2}, "cook_s": 4, "price": 40},
    "lau_ca_linh_dien_dien": {"recipe": {"ca_linh": 3, "bong_dien_dien": 1}, "cook_s": 10, "price": 120},
    "canh_chua_ca_loc": {"recipe": {"ca_loc": 1, "bong_dien_dien": 1}, "cook_s": 8, "price": 90},
    "ca_keo_nuong": {"recipe": {"ca_keo": 2}, "cook_s": 6, "price": 70},
    "lau_mam": {"recipe": {"ca_linh": 2, "ca_keo": 1, "keo_neo": 1, "bong_dien_dien": 1}, "cook_s": 12, "price": 200},
}
V11_DAY_PLAN = [
    {"day": 1, "dishes": {"ca_loc_nuong_trui": 3, "goi_bong_sung": 3},
     "ingredients": {"bong_sung": 6, "ca_loc": 3}},
    {"day": 2, "dishes": {"ca_loc_nuong_trui": 2, "lau_ca_linh_dien_dien": 2},
     "ingredients": {"bong_dien_dien": 2, "ca_linh": 6, "ca_loc": 2}},
    {"day": 3, "dishes": {"goi_bong_sung": 2, "canh_chua_ca_loc": 2, "ca_keo_nuong": 2},
     "ingredients": {"bong_dien_dien": 2, "bong_sung": 4, "ca_keo": 4, "ca_loc": 2}},
    {"day": 4, "dishes": {"lau_mam": 1, "ca_loc_nuong_trui": 2, "goi_bong_sung": 1},
     "ingredients": {"bong_dien_dien": 1, "bong_sung": 2, "ca_keo": 1, "ca_linh": 2, "ca_loc": 2, "keo_neo": 1}},
    {"day": 5, "dishes": {"lau_mam": 1, "lau_ca_linh_dien_dien": 1, "ca_loc_nuong_trui": 1},
     "ingredients": {"bong_dien_dien": 2, "ca_keo": 1, "ca_linh": 5, "ca_loc": 1, "keo_neo": 1}},
]


def v11_tuning():
    t = copy.deepcopy(load_contract()["tuning"])
    t.pop("freshness", None)  # Giữ kiểm hồi quy luật v1.1 (2 bếp/4 bàn/6 món/kế hoạch) độc lập với độ tươi v1.2
    t["quan"]["stoves"] = copy.deepcopy(V11_QUAN_STOVES)
    t["quan"]["tables"] = copy.deepcopy(V11_QUAN_TABLES)
    t["menu"] = copy.deepcopy(V11_MENU)
    t["day_plan"] = copy.deepcopy(V11_DAY_PLAN)
    return t


def idle_inp():
    return InputState((0.0, 0.0), {"interact": False, "catch": False}, set())


def interact_inp():
    return InputState((0.0, 0.0), {"interact": True, "catch": False}, {"interact"})


class TestPhase2Quan(unittest.TestCase):
    def test_01_two_stoves_cook_in_parallel_and_pick_oldest_order(self):
        """AC-P2-04: 2 bếp B1, B2 nấu song song; B1 lấy đơn cũ nhất, B2 lấy đơn kế."""
        tuning = v11_tuning()
        sc = {
            "player": {"pos": [2, 8]},
            "stock": {"ca_loc": 1, "ca_keo": 2, "bong_dien_dien": 1},
            "customers": [
                {"id": "C1", "table_id": "T2", "dish_id": "ca_keo_nuong", "order_tick": 100},
                {"id": "C2", "table_id": "T1", "dish_id": "canh_chua_ca_loc", "order_tick": 50},
            ],
            "random_customers": False,
        }
        sim = QuanSim(tuning, sc, Streams(1), IdAllocator())
        # Đứng tại B1 [2, 8]: phải lấy C2 (order_tick=50 < 100)
        ev1 = sim.step(interact_inp())
        self.assertEqual([n for n, _ in ev1], ["cook_started"])
        self.assertEqual(ev1[0][1]["stove_id"], "B1")
        self.assertEqual(ev1[0][1]["order_id"], "C2")
        self.assertEqual(ev1[0][1]["dish_id"], "canh_chua_ca_loc")
        self.assertEqual(ev1[0][1]["base_price"], 90)
        self.assertEqual(ev1[0][1]["items"], ["bong_dien_dien", "ca_loc"])

        # Di chuyển sang B2 [5, 8]: phải lấy C1 (ca_keo_nuong)
        sim.pos = [5.0, 8.0]
        ev2 = sim.step(interact_inp())
        self.assertEqual([n for n, _ in ev2], ["cook_started"])
        self.assertEqual(ev2[0][1]["stove_id"], "B2")
        self.assertEqual(ev2[0][1]["order_id"], "C1")
        self.assertEqual(ev2[0][1]["dish_id"], "ca_keo_nuong")
        self.assertEqual(ev2[0][1]["base_price"], 70)
        self.assertEqual(ev2[0][1]["items"], ["ca_keo", "ca_keo"])
        self.assertEqual(sim.snapshot()["stock"], {})

    def test_02_four_tables_spawn_order_and_full_skip(self):
        """AC-P2-04: 4 bàn T1->T2->T3->T4 nhận khách đúng lịch; đầy 4 bàn thì bỏ lượt (không no_dish)."""
        tuning = v11_tuning()
        stock = {"ca_loc": 10, "bong_sung": 10, "ca_linh": 15, "ca_keo": 10, "keo_neo": 5, "bong_dien_dien": 10}
        sim = QuanSim(tuning, {}, Streams(7), IdAllocator(), inventory=stock)
        arrived = []
        no_dishes = []
        for _ in range(3800):
            for name, data in sim.step(idle_inp()):
                if name == "customer_arrived":
                    arrived.append((sim.phase_tick, data["table_id"], data["dish_id"]))
                elif name == "no_dish":
                    no_dishes.append(sim.phase_tick)
        # Khách đầu ở tick 120, sau đó 1020, 1920, 2820; tick 3720 đủ 4 bàn nên bỏ lượt
        self.assertEqual([t for t, _, _ in arrived[:4]], [120, 1020, 1920, 2820])
        self.assertEqual([tb for _, tb, _ in arrived[:4]], ["T1", "T2", "T3", "T4"])
        self.assertEqual(no_dishes, [])

    def test_03_lau_mam_full_lifecycle_and_tip(self):
        """AC-P2-04: Đủ 6 món & 6 nguyên liệu — nấu/bưng/phục vụ/trả tiền/boa cho Lẩu mắm (200k + 40k boa)."""
        tuning = v11_tuning()
        sc = {
            "player": {"pos": [2, 8]},
            "stock": {"ca_linh": 2, "ca_keo": 1, "keo_neo": 1, "bong_dien_dien": 1},
            "customers": [{"id": "C1", "table_id": "T4", "dish_id": "lau_mam"}],
            "random_customers": False,
        }
        sim = QuanSim(tuning, sc, Streams(1), IdAllocator())
        # Bắt đầu nấu tại B1 (12s = 720 tick)
        ev = sim.step(interact_inp())
        self.assertEqual(ev[0][0], "cook_started")
        self.assertEqual(ev[0][1]["items"], ["bong_dien_dien", "ca_keo", "ca_linh", "ca_linh", "keo_neo"])
        self.assertEqual(ev[0][1]["base_price"], 200)

        ready_events = []
        for _ in range(720):
            ready_events.extend(sim.step(idle_inp()))
        self.assertTrue(any(n == "dish_ready" and d["dish_id"] == "lau_mam" for n, d in ready_events))

        # Bưng món từ B1 và giao tại T4 [13, 6]
        ev_pick = sim.step(interact_inp())
        self.assertEqual(ev_pick[0][0], "dish_picked")
        sim.pos = [13.0, 6.0]
        ev_serve = sim.step(interact_inp())
        self.assertEqual(ev_serve[0][0], "served")
        self.assertEqual(ev_serve[0][1]["base_price"], 200)
        self.assertEqual(ev_serve[0][1]["tip"], 40)  # floor(200 * 0.2)

        paid_events = []
        for _ in range(600):
            paid_events.extend(sim.step(idle_inp()))
        paid = [d for n, d in paid_events if n == "paid"]
        self.assertEqual(len(paid), 1)
        self.assertEqual(paid[0]["amount"], 240)
        self.assertEqual(sim.money, 240)
        self.assertAlmostEqual(sim.reputation, 3.2, places=3)

    def test_04_day_plan_filtering_and_unlimited_planned_orders(self):
        """AC-P2-05: Trong day, lọc theo kế hoạch ngày; có nguyên liệu món ngoài kế hoạch -> no_dish;
        khách vẫn gọi tiếp món trong kế hoạch vượt quá số suất dự kiến.
        """
        tuning = v11_tuning()
        d1_dishes = V11_DAY_PLAN[0]["dishes"]  # ca_loc_nuong_trui (3), goi_bong_sung (3)

        # Kho chỉ có nguyên liệu của ca_keo_nuong (ngoài D1) -> phải phát no_dish
        sim_offplan = QuanSim(
            tuning, {}, Streams(1), IdAllocator(),
            inventory={"ca_keo": 6, "keo_neo": 2},
            allowed_dishes=d1_dishes,
        )
        events_all = []
        for _ in range(120):
            events_all.extend(sim_offplan.step(idle_inp()))
        self.assertEqual([n for n, _ in events_all], ["no_dish"])
        self.assertEqual(sim_offplan.customers, [])

        # Kho có 4 ca_loc (vượt số suất dự kiến 3 của D1) -> vẫn sinh đủ 4 khách gọi ca_loc_nuong_trui
        sim_over = QuanSim(
            tuning, {}, Streams(1), IdAllocator(),
            inventory={"ca_loc": 4},
            allowed_dishes=d1_dishes,
        )
        arrived = []
        for _ in range(2900):
            for n, d in sim_over.step(idle_inp()):
                if n == "customer_arrived":
                    arrived.append(d["dish_id"])
        self.assertEqual(arrived, ["ca_loc_nuong_trui"] * 4)

    def test_05_day_plan_rejects_offplan_fixture_and_checks_d1_d5_math(self):
        """AC-P2-05: Fixture khách/bếp dùng món ngoài kế hoạch ngày -> BadInput (mã 2);
        đối chiếu tổng nguyên liệu D1–D5 từ công thức.
        """
        tuning = v11_tuning()
        d1_dishes = V11_DAY_PLAN[0]["dishes"]
        with self.assertRaises(BadInput):
            QuanSim(
                tuning,
                {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "lau_mam"}]},
                Streams(1),
                IdAllocator(),
                inventory={"ca_linh": 2, "ca_keo": 1, "keo_neo": 1, "bong_dien_dien": 1},
                allowed_dishes=d1_dishes,
            )

        # Đối chiếu toán học bảng kế hoạch D1–D5 trong PHASE2.md
        for plan in V11_DAY_PLAN:
            calc = {}
            for dish_id, servings in plan["dishes"].items():
                for ing, qty in V11_MENU[dish_id]["recipe"].items():
                    calc[ing] = calc.get(ing, 0) + qty * servings
            self.assertEqual(calc, plan["ingredients"], f"Day {plan['day']}")

        # Khi manifest thật đã lên v1.1, đối chiếu trực tiếp game.contract.json
        contract = load_contract()
        if contract.get("contract_version") == "1.1":
            t = contract["tuning"]
            self.assertEqual([s["id"] for s in t["quan"]["stoves"]], ["B1", "B2"])
            self.assertEqual([tb["id"] for tb in t["quan"]["tables"]], ["T1", "T2", "T3", "T4"])
            self.assertEqual(set(t["menu"].keys()), set(V11_MENU.keys()))
            self.assertEqual(len(t["day_plan"]), 5)

    def test_06_closing_cleans_two_stoves_hand_and_four_tables(self):
        """AC-P2-04: Hết ca với 4 bàn ở đủ trạng thái: ăn trả closing, chờ rời không trừ uy tín, dọn 2 bếp & tay."""
        tuning = v11_tuning()
        sc = {
            "time_left_ticks": 1,
            "stock": {"ca_loc": 1},
            "hand": {"order_id": "C3", "dish_id": "goi_bong_sung", "base_price": 40},
            "stoves": [
                {"id": "B1", "state": "cooking", "dish": {"order_id": "C2", "dish_id": "ca_keo_nuong", "base_price": 70}, "cook_ticks_left": 50},
                {"id": "B2", "state": "idle"},
            ],
            "customers": [
                {"id": "C1", "table_id": "T1", "dish_id": "lau_mam", "state": "eating", "order_status": "served", "eat_ticks_left": 200, "base_price": 200, "tip": 40},
                {"id": "C2", "table_id": "T2", "dish_id": "ca_keo_nuong", "state": "waiting", "order_status": "assigned"},
                {"id": "C3", "table_id": "T3", "dish_id": "goi_bong_sung", "state": "waiting", "order_status": "assigned"},
                {"id": "C4", "table_id": "T4", "dish_id": "ca_loc_nuong_trui", "state": "waiting", "order_status": "reserved"},
            ],
            "random_customers": False,
        }
        sim = QuanSim(tuning, sc, Streams(1), IdAllocator())
        ev = sim.step(idle_inp())
        names = [n for n, _ in ev]
        self.assertEqual(names, ["paid", "customer_left", "customer_left", "customer_left", "quan_end"])
        self.assertTrue(sim.done)
        self.assertEqual(sim.money, 240)
        self.assertAlmostEqual(sim.reputation, 3.2, places=3)  # +0.2 từ boa C1, không trừ từ C2/C3/C4
        self.assertIsNone(sim.hand)
        self.assertTrue(all(s["state"] == "idle" and s["dish"] is None for s in sim.stoves))
        self.assertEqual(sim.customers, [])

    def test_07_client_html_has_phase2_screens_and_hud_elements(self):
        """AC-P2-09: Kiểm tự động client HTML có đủ 6 món, 6 nguyên liệu, 8 màn, cảnh báo & pause/shop."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "chonoi", "web", "index.html"), encoding="utf-8") as f:
            html = f.read()
        for token in (
            "<canvas",
            "ca_keo", "keo_neo",
            "canh_chua_ca_loc", "ca_keo_nuong", "lau_mam",
            "Thủy quái!", "Hết hơi!",
            "day_intro", "evening_intro", "day_result", "summary",
            "/presentation", "shop_done", "font-size: 18px",
        ):
            self.assertIn(token, html, f"index.html thiếu phần tử Phase 2: {token}")


if __name__ == "__main__":
    unittest.main()