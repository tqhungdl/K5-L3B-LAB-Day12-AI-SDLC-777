"""Test Phase 1 — Lát 3: khách Quán (quan_customers.py) và kiểm lỗi scenario (scenario.py).

Chạy riêng:
    PYTHONPATH=tests:. python3 -m unittest tests/test_p1_quan_customers.py -v
"""

import os
import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.ids import IdAllocator
from chonoi.rng import Streams
from chonoi.sim.quan_customers import (
    available_stock,
    leave_waiting,
    load_customers,
    oldest_reserved,
    spawn_customer,
    tick_customers,
)

from helpers import Workdir, run_headless, write_json


def make_sim(
    stock=None,
    tables=None,
    stoves=None,
    hand=None,
    seed=42,
    random_customers=True,
    reputation=None,
):
    """Fixture QuanSim nhẹ để gọi trực tiếp các hàm lát 3 độc lập với lát 4."""
    tuning = load_contract()["tuning"]
    q = tuning["quan"]

    class DummyQuanSim:
        pass

    sim = DummyQuanSim()
    sim.t = q
    sim.menu = tuning["menu"]
    sim.rng = Streams(seed)
    sim.ids = IdAllocator()
    sim.stock = dict(stock or {})
    sim.hand = hand
    sim.random_customers = random_customers
    sim.reputation = q["reputation_initial"] if reputation is None else reputation
    sim.tables = [dict(tb) for tb in (tables if tables is not None else q["tables"])]
    sim.stoves = [
        dict(
            s,
            state=s.get("state", "idle"),
            dish=s.get("dish"),
            cook_ticks_left=s.get("cook_ticks_left", 0),
            ready_ticks=s.get("ready_ticks", 0),
        )
        for s in (stoves if stoves is not None else q["stoves"])
    ]
    sim.customers = []
    return sim


class QuanCustomersUnitTests(unittest.TestCase):
    def test_load_customers_defaults_and_auto_reserve(self):
        sim = make_sim(stock={"ca_loc": 1, "bong_sung": 2})
        customers = load_customers(
            sim,
            {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}]},
        )
        self.assertEqual(len(customers), 1)
        c = customers[0]
        self.assertEqual(c["state"], "waiting")
        self.assertEqual(c["order_tick"], 0)
        self.assertEqual(c["order_status"], "reserved")
        self.assertEqual(c["patience_ticks_left"], int(round(sim.t["patience_s"] * 60)))
        self.assertEqual(c["eat_ticks_left"], 0)
        self.assertEqual(c["reserved"], {"ca_loc": 1})
        self.assertEqual(c["base_price"], 0)
        self.assertEqual(c["tip"], 0)
        sim.customers = customers
        self.assertEqual(available_stock(sim), {"bong_sung": 2})

    def test_load_customers_valid_assigned_eating_and_unfulfillable(self):
        tables = [{"id": "T1", "pos": [2, 2]}, {"id": "T2", "pos": [6, 2]}, {"id": "T3", "pos": [10, 2]}]
        stoves = [{
            "id": "B1",
            "pos": [2, 8],
            "state": "cooking",
            "dish": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
            "cook_ticks_left": 180,
            "ready_ticks": 0,
        }]
        sim = make_sim(stock={}, tables=tables, stoves=stoves)
        customers = load_customers(
            sim,
            {
                "customers": [
                    {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"},
                    {
                        "id": "C2",
                        "table_id": "T2",
                        "dish_id": "goi_bong_sung",
                        "state": "eating",
                        "order_status": "served",
                        "eat_ticks_left": 300,
                        "base_price": 40,
                        "tip": 8,
                    },
                    {"id": "C3", "table_id": "T3", "dish_id": "lau_ca_linh_dien_dien", "order_status": "unfulfillable"},
                ]
            },
        )
        by_id = {c["id"]: c for c in customers}
        self.assertEqual(by_id["C1"]["base_price"], 60)
        self.assertEqual(by_id["C1"]["reserved"], {})
        self.assertEqual(by_id["C2"]["tip"], 8)
        self.assertEqual(by_id["C3"]["order_status"], "unfulfillable")

    def test_load_customers_rejects_contradictions(self):
        # Giữ vượt tồn kho
        with self.assertRaises(BadInput):
            load_customers(
                make_sim(stock={}),
                {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}]},
            )
        # Giữ khác công thức
        with self.assertRaises(BadInput):
            load_customers(
                make_sim(stock={"ca_loc": 2, "bong_sung": 2}),
                {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": {"bong_sung": 1}}]},
            )
        # Đơn assigned thiếu món trên bếp/tay
        with self.assertRaises(BadInput):
            load_customers(
                make_sim(stock={}),
                {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"}]},
            )
        # Bếp và tay cùng giữ một đơn
        dish = {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60}
        with self.assertRaises(BadInput):
            load_customers(
                make_sim(
                    stoves=[{"id": "B1", "pos": [2, 8], "state": "ready", "dish": dish, "cook_ticks_left": 0, "ready_ticks": 5}],
                    hand=dict(dish),
                ),
                {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"}]},
            )
        # Món trên bếp không khớp dish_id đơn
        with self.assertRaises(BadInput):
            load_customers(
                make_sim(
                    stoves=[{
                        "id": "B1",
                        "pos": [2, 8],
                        "state": "cooking",
                        "dish": {"order_id": "C1", "dish_id": "goi_bong_sung", "base_price": 40},
                        "cook_ticks_left": 60,
                        "ready_ticks": 0,
                    }]
                ),
                {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"}]},
            )
        # Khách eating thiếu base_price / tip hoặc eat_ticks_left <= 0 hoặc không phải served
        for bad_c in (
            {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "state": "eating", "order_status": "served", "eat_ticks_left": 60},
            {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "state": "eating", "order_status": "served", "eat_ticks_left": 0, "base_price": 60, "tip": 0},
            {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "state": "eating", "order_status": "reserved", "eat_ticks_left": 60, "base_price": 60, "tip": 0},
        ):
            with self.assertRaises(BadInput, msg=bad_c):
                load_customers(make_sim(stock={"ca_loc": 1}), {"customers": [bad_c]})

    def test_tick_customers_decrements_only_active_timer(self):
        tables = [{"id": "T1", "pos": [2, 2]}, {"id": "T2", "pos": [6, 2]}]
        sim = make_sim(stock={"ca_loc": 1}, tables=tables)
        sim.customers = load_customers(
            sim,
            {
                "customers": [
                    {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "patience_ticks_left": 1},
                    {
                        "id": "C2",
                        "table_id": "T2",
                        "dish_id": "goi_bong_sung",
                        "state": "eating",
                        "order_status": "served",
                        "patience_ticks_left": 500,
                        "eat_ticks_left": 1,
                        "base_price": 40,
                        "tip": 8,
                    },
                ]
            },
        )
        tick_customers(sim)
        self.assertEqual(sim.customers[0]["patience_ticks_left"], 0)
        self.assertEqual(sim.customers[0]["eat_ticks_left"], 0)
        self.assertEqual(sim.customers[1]["patience_ticks_left"], 500)
        self.assertEqual(sim.customers[1]["eat_ticks_left"], 0)
        # Không âm khi giảm tiếp
        tick_customers(sim)
        self.assertEqual(sim.customers[0]["patience_ticks_left"], 0)
        self.assertEqual(sim.customers[1]["eat_ticks_left"], 0)

    def test_oldest_reserved_tiebreaks_by_order_tick_then_table_id(self):
        tables = [{"id": "T10", "pos": [2, 2]}, {"id": "T2", "pos": [6, 2]}, {"id": "T1", "pos": [10, 2]}]
        sim = make_sim(stock={"ca_loc": 3}, tables=tables)
        sim.customers = load_customers(
            sim,
            {
                "customers": [
                    {"id": "C1", "table_id": "T10", "dish_id": "ca_loc_nuong_trui", "order_tick": 120},
                    {"id": "C2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "order_tick": 120},
                    {"id": "C3", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_tick": 200},
                ]
            },
        )
        # T2 phải đứng trước T10 theo id_key khi cùng order_tick = 120
        self.assertEqual(oldest_reserved(sim)["id"], "C2")
        sim.customers[1]["order_status"] = "assigned"
        self.assertEqual(oldest_reserved(sim)["id"], "C1")

    def test_leave_waiting_releases_reserved_and_updates_reputation(self):
        sim = make_sim(stock={"ca_loc": 1}, reputation=0.3)
        sim.customers = load_customers(
            sim,
            {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}]},
        )
        self.assertEqual(available_stock(sim), {})
        events = []
        leave_waiting(sim, sim.customers[0], "patience", events)
        self.assertEqual(sim.customers, [])
        self.assertEqual(available_stock(sim), {"ca_loc": 1})
        self.assertEqual(sim.reputation, 0.0)  # kẹp về reputation_min = 0
        self.assertEqual(
            events,
            [("customer_left", {"order_id": "C1", "table_id": "T1", "reason": "patience", "reputation": 0.0})],
        )

    def test_leave_waiting_closing_does_not_reduce_reputation(self):
        sim = make_sim(stock={"ca_loc": 1}, reputation=3.0)
        sim.customers = load_customers(
            sim,
            {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}]},
        )
        events = []
        leave_waiting(sim, sim.customers[0], "closing", events)
        self.assertEqual(sim.reputation, 3.0)
        self.assertEqual(available_stock(sim), {"ca_loc": 1})
        self.assertEqual(events[0][1]["reason"], "closing")

    def test_spawn_customer_schedule_no_dish_and_full_tables(self):
        first = load_contract()["tuning"]["quan"]["first_customer_tick"]
        interval = int(round(load_contract()["tuning"]["quan"]["customer_interval_s"] * 60))

        # Chưa đến lịch -> không sinh, không phát no_dish
        sim = make_sim(stock={})
        ev = []
        self.assertIsNone(spawn_customer(sim, first - 1, ev))
        self.assertEqual(ev, [])

        # Đúng lịch, có bàn trống, kho rỗng -> phát no_dish
        self.assertIsNone(spawn_customer(sim, first, ev))
        self.assertEqual(ev, [("no_dish", {})])

        # random_customers = False -> không sinh, không phát no_dish
        sim_off = make_sim(stock={"ca_loc": 1}, random_customers=False)
        ev_off = []
        self.assertIsNone(spawn_customer(sim_off, first, ev_off))
        self.assertEqual(ev_off, [])

        # Có nguyên liệu -> sinh khách, giữ chỗ; lượt kế hết bàn -> bỏ lượt (KHÔNG phát no_dish)
        sim2 = make_sim(stock={"ca_loc": 1}, tables=[{"id": "T1", "pos": [9, 2]}])
        ev2 = []
        c = spawn_customer(sim2, first, ev2)
        self.assertIsNotNone(c)
        self.assertEqual(c["id"], "C1")
        self.assertEqual(c["table_id"], "T1")
        self.assertEqual(c["dish_id"], "ca_loc_nuong_trui")
        self.assertEqual(c["order_tick"], first)
        self.assertEqual(c["reserved"], {"ca_loc": 1})
        self.assertEqual(available_stock(sim2), {})
        self.assertEqual(ev2, [("customer_arrived", {"order_id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"})])

        ev3 = []
        self.assertIsNone(spawn_customer(sim2, first + interval, ev3))
        self.assertEqual(ev3, [])

    def test_spawn_customer_deterministic_by_seed_and_table_order(self):
        first = load_contract()["tuning"]["quan"]["first_customer_tick"]
        interval = int(round(load_contract()["tuning"]["quan"]["customer_interval_s"] * 60))
        tables = [{"id": "T10", "pos": [2, 2]}, {"id": "T2", "pos": [6, 2]}, {"id": "T1", "pos": [10, 2]}]
        rich_stock = {"ca_loc": 10, "bong_sung": 10, "ca_linh": 15, "bong_dien_dien": 10}

        def run_seq(seed):
            sim = make_sim(stock=rich_stock, tables=tables, seed=seed)
            sim.ids.reserve("C9")
            picked = []
            for k in range(3):
                ev = []
                c = spawn_customer(sim, first + k * interval, ev)
                picked.append((c["id"], c["table_id"], c["dish_id"]))
            return picked

        seq_a = run_seq(12345)
        seq_b = run_seq(12345)
        self.assertEqual(seq_a, seq_b)
        self.assertEqual([x[0] for x in seq_a], ["C10", "C11", "C12"])
        self.assertEqual([x[1] for x in seq_a], ["T1", "T2", "T10"])


class ScenarioValidationHeadlessTests(unittest.TestCase):
    def test_invalid_quan_scenarios_exit_2_without_writing_output(self):
        dish_c1 = {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60}
        bad_blocks = [
            {"random_customers": "yes"},
            {"reputation": 6.0},
            {"reputation": -0.1},
            {"tables": [{"id": "T99", "pos": [5, 5]}]},
            {"stoves": [{"id": "B99", "pos": [2, 8]}]},
            {"stoves": [{"id": "B1", "state": "cooking", "dish": dish_c1, "cook_ticks_left": 0}]},
            {"stoves": [{"id": "B1", "state": "idle", "cook_ticks_left": 5}]},
            {"stoves": [{"id": "B1", "state": "ready", "dish": dish_c1, "cook_ticks_left": 10}]},
            {"hand": dish_c1},  # orphan dish không có khách C1
            {"stock": {}, "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}]},
            {"stock": {"ca_loc": 1}, "customers": [{"id": "C1", "table_id": "T1", "dish_id": "mon_la"}]},
            {
                "stock": {"ca_loc": 1},
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": {}}],
            },
            {
                "stoves": [{"id": "B1", "state": "ready", "dish": dish_c1, "ready_ticks": 0}],
                "hand": dish_c1,
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"}],
            },
            {
                "customers": [
                    {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "state": "eating", "order_status": "served", "eat_ticks_left": 30}
                ]
            },
            {
                "customers": [
                    {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "unfulfillable", "reserved": {"ca_loc": 1}}
                ]
            },
            {
                "customers": [
                    {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "extra_field": 1}
                ]
            },
        ]
        for block in bad_blocks:
            with Workdir() as w:
                sc = write_json(w.path("sc.json"), {"quan": block})
                out = w.path("out.jsonl")
                code, _ = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--scenario", sc, "--out", out)
                self.assertEqual(code, 2, block)
                self.assertFalse(os.path.exists(out), f"không được tạo file out khi lỗi: {block}")

    def test_invalid_gather_extra_node_or_fish_fields_exit_2(self):
        bad_blocks = [
            {"nodes": [{"id": "N1", "kind": "bong_sung", "pos": [10, 0], "bonus": 1}]},
            {"fish": [{"id": "F1", "kind": "ca_loc", "pos": [10, 5], "speed": 2}]},
        ]
        for block in bad_blocks:
            with Workdir() as w:
                sc = write_json(w.path("sc.json"), {"gather": block})
                out = w.path("out.jsonl")
                code, _ = run_headless("--mode", "gather", "--seed", "1", "--ticks", "0", "--scenario", sc, "--out", out)
                self.assertEqual(code, 2, block)
                self.assertFalse(os.path.exists(out))


if __name__ == "__main__":
    unittest.main()