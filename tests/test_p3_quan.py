"""Test Phase 3 — Lát 3 (AC-P3-03, AC-P3-04): Quán kho cá thể, độ tươi, giữ chỗ lại & giá theo tươi.

Chạy riêng:
    PYTHONPATH=tests:. python3 -m unittest tests/test_p3_quan.py -v
"""

import copy
import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.sim.quan import QuanSim


def v12_tuning():
    t = copy.deepcopy(load_contract()["tuning"])
    t["freshness"] = {
        "initial": 100,
        "gather_decay_per_s": 0.5,
        "quan_decay_per_s": 0.25,
        "spoiled_below": 30,
    }
    return t


def idle_inp():
    return InputState((0.0, 0.0), {"interact": False, "catch": False}, set())


def interact_inp():
    return InputState((0.0, 0.0), {"interact": True, "catch": False}, {"interact"})


class TestPhase3QuanFreshness(unittest.TestCase):
    def test_01_auto_reserve_picks_freshest_and_tiebreaks_by_id(self):
        """AC-P3-03: Giữ cá thể chưa ươn tươi nhất; hòa fresh chọn ID nhỏ (I2 trước I10); bỏ qua hàng < 30."""
        tuning = v12_tuning()
        stock = [
            {"id": "I1", "kind": "ca_loc", "fresh": 29.9},  # đã ươn -> bỏ qua
            {"id": "I10", "kind": "ca_loc", "fresh": 85},
            {"id": "I2", "kind": "ca_loc", "fresh": 85},    # hòa 85 với I10 -> chọn I2 trước
            {"id": "I3", "kind": "ca_loc", "fresh": 60},
        ]
        sc = {
            "stock": stock,
            "customers": [
                {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_tick": 10},
                {"id": "C2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "order_tick": 20},
            ],
            "random_customers": False,
        }
        sim = QuanSim(tuning, sc, Streams(1), IdAllocator())
        by_id = {c["id"]: c for c in sim.snapshot()["customers"]}
        self.assertEqual(by_id["C1"]["reserved"], ["I2"])
        self.assertEqual(by_id["C2"]["reserved"], ["I10"])

    def test_02_fresh_30_spoils_at_tick_1_and_competing_orders_re_reserve(self):
        """AC-P3-03: Hai cá thể fresh=30 cùng ươn ở tick 1 -> phát hết `spoiled` theo ID (I2 trước I10),
        sau đó xử lý đơn theo (order_tick, table_id): đơn cũ hơn giữ lại được cá thể dự phòng, đơn sau -> unfulfillable.
        """
        tuning = v12_tuning()
        stock = [
            {"id": "I10", "kind": "ca_loc", "fresh": 30},
            {"id": "I2", "kind": "ca_loc", "fresh": 30},
            {"id": "I5", "kind": "ca_loc", "fresh": 90},  # chỉ đủ 1 con dự phòng
        ]
        sc = {
            "stock": stock,
            "customers": [
                {"id": "C1", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "order_tick": 50, "reserved": ["I10"]},
                {"id": "C2", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_tick": 50, "reserved": ["I2"]},
            ],
            "random_customers": False,
        }
        sim = QuanSim(tuning, sc, Streams(1), IdAllocator())
        ev = sim.step(idle_inp())

        # Phát hết `spoiled` theo thứ tự ID: I2 trước I10
        self.assertEqual(ev, [
            ("spoiled", {"item_id": "I2", "kind": "ca_loc", "location": "stock"}),
            ("spoiled", {"item_id": "I10", "kind": "ca_loc", "location": "stock"}),
        ])
        # C2 (T1) có table_id nhỏ hơn C1 (T2) ở cùng order_tick=50 -> C2 lấy I5, C1 -> unfulfillable
        by_id = {c["id"]: c for c in sim.snapshot()["customers"]}
        self.assertEqual(by_id["C2"]["order_status"], "reserved")
        self.assertEqual(by_id["C2"]["reserved"], ["I5"])
        self.assertEqual(by_id["C1"]["order_status"], "unfulfillable")
        self.assertEqual(by_id["C1"]["reserved"], [])

        # Tick 2: không phát `spoiled` lần thứ 2 cho I2/I10
        ev2 = sim.step(idle_inp())
        self.assertEqual(ev2, [])

    def test_03_re_reserve_releases_unspoiled_part_when_order_becomes_unfulfillable(self):
        """AC-P3-03: Đơn 2 nguyên liệu mất 1 món ươn -> nhả toàn bộ phần còn tươi để đơn sau kịp giữ lại."""
        tuning = v12_tuning()
        stock = [
            {"id": "I1", "kind": "ca_loc", "fresh": 80},          # C1 đang giữ cho canh chua
            {"id": "I2", "kind": "bong_dien_dien", "fresh": 30},  # ươn ở tick 1 (hết bông điên điển thay thế)
            {"id": "I3", "kind": "ca_loc", "fresh": 30},          # C2 đang giữ cho cá lóc nướng trui -> ươn ở tick 1
        ]
        sc = {
            "stock": stock,
            "customers": [
                {"id": "C1", "table_id": "T1", "dish_id": "canh_chua_ca_loc", "order_tick": 10, "reserved": ["I1", "I2"]},
                {"id": "C2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "order_tick": 20, "reserved": ["I3"]},
            ],
            "random_customers": False,
        }
        sim = QuanSim(tuning, sc, Streams(1), IdAllocator())
        ev = sim.step(idle_inp())
        self.assertEqual([d["item_id"] for n, d in ev if n == "spoiled"], ["I2", "I3"])
        by_id = {c["id"]: c for c in sim.snapshot()["customers"]}
        # C1 thất bại -> nhả I1 và chuyển unfulfillable; C2 sau đó giữ được I1!
        self.assertEqual(by_id["C1"]["order_status"], "unfulfillable")
        self.assertEqual(by_id["C1"]["reserved"], [])
        self.assertEqual(by_id["C2"]["order_status"], "reserved")
        self.assertEqual(by_id["C2"]["reserved"], ["I1"])

    def test_04_cook_consumes_exact_ids_and_locks_fresh_price_and_tip_floor(self):
        """AC-P3-04: Nấu tiêu đúng ID giữ, `cook_started.items` sắp (kind, id), giá làm tròn xuống hai phía biên & boa."""
        tuning = v12_tuning()
        # Gỏi bông súng giá niêm yết 40, cần 2 bong_sung.
        # Sau 1 bước ở Quán, mỗi cá thể giảm 1/240.
        # Trường hợp 1: fresh ban đầu [100, 50 + 2/240] -> sau 1 tick tổng = 150 -> 40*150/200 = 30 (chẵn)
        # Trường hợp 2: fresh ban đầu [100, 50] -> sau 1 tick tổng = 150 - 2/240 -> 40*total/200 < 30 -> floor = 29!
        sc_below = {
            "player": {"pos": [2, 8]},
            "stock": [
                {"id": "I10", "kind": "bong_sung", "fresh": 100},
                {"id": "I2", "kind": "bong_sung", "fresh": 50},
                {"id": "I9", "kind": "bong_sung", "fresh": 40},  # giữ lại không bị tiêu
            ],
            "customers": [
                {"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung", "reserved": ["I2", "I10"]},
            ],
            "random_customers": False,
        }
        sim = QuanSim(tuning, sc_below, Streams(1), IdAllocator())
        ev = sim.step(interact_inp())
        self.assertEqual(ev[0][0], "cook_started")
        data = ev[0][1]
        self.assertEqual(data["base_price"], 29)  # dưới biên 30 -> làm tròn xuống 29
        self.assertEqual([it["id"] for it in data["items"]], ["I2", "I10"])
        self.assertEqual([it["id"] for it in sim.snapshot()["stock"]], ["I9"])

        # Nấu xong (4s = 240 tick), bưng món (không hao tươi sau khi nấu), phục vụ & trả tiền
        for _ in range(240):
            sim.step(idle_inp())
        self.assertEqual(sim.step(interact_inp())[0][0], "dish_picked")
        sim.pos = [9.0, 2.0]
        serve_ev = sim.step(interact_inp())
        self.assertEqual(serve_ev[0][0], "served")
        self.assertEqual(serve_ev[0][1]["base_price"], 29)
        self.assertEqual(serve_ev[0][1]["tip"], 5)  # floor(29 * 0.2) = floor(5.8) = 5

        paid = []
        for _ in range(600):
            paid.extend(d for n, d in sim.step(idle_inp()) if n == "paid")
        self.assertEqual(len(paid), 1)
        self.assertEqual(paid[0]["amount"], 34)
        self.assertEqual(sim.money, 34)
        self.assertEqual(sim.earned, 34)
        self.assertAlmostEqual(sim.reputation, 3.2, places=3)

    def test_05_cook_started_items_sorted_by_kind_then_id_and_exact_upper_edge(self):
        """AC-P3-04: `cook_started.items` của Lẩu cá linh (4 cá thể) sắp theo kind rồi id; đúng biên chẵn giữ nguyên."""
        tuning = v12_tuning()
        # 4 cá thể đều bắt đầu 100 -> sau 1 tick ở Quán tổng = 4*(100 - 1/240), 120 * avg / 100 = 119.995 -> floor = 119
        # Kiểm thêm 1 ca biên chẵn với giá 120, fresh=50 + 1/240 không giảm qua 50 -> exact 60!
        sc = {
            "player": {"pos": [2, 8]},
            "stock": [
                {"id": "I10", "kind": "ca_linh", "fresh": 100},
                {"id": "I2", "kind": "ca_linh", "fresh": 100},
                {"id": "I5", "kind": "ca_linh", "fresh": 100},
                {"id": "I9", "kind": "bong_dien_dien", "fresh": 100},
            ],
            "customers": [{"id": "C1", "table_id": "T1", "dish_id": "lau_ca_linh_dien_dien"}],
            "random_customers": False,
        }
        sim = QuanSim(tuning, sc, Streams(1), IdAllocator())
        ev = sim.step(interact_inp())
        self.assertEqual(ev[0][0], "cook_started")
        items = ev[0][1]["items"]
        self.assertEqual([(it["kind"], it["id"]) for it in items], [
            ("bong_dien_dien", "I9"),
            ("ca_linh", "I2"),
            ("ca_linh", "I5"),
            ("ca_linh", "I10"),
        ])
        self.assertEqual(ev[0][1]["base_price"], 119)

    def test_06_rejects_v12_fixture_contradictions(self):
        """AC-P3-03: Từ chối kho đếm v1.1, ID giữ trùng giữa 2 đơn, giữ hàng ươn, sai công thức -> BadInput (mã 2)."""
        tuning = v12_tuning()
        # Kho đếm kiểu cũ ở v1.2 -> lỗi
        with self.assertRaises(BadInput):
            QuanSim(tuning, {"stock": {"ca_loc": 1}}, Streams(1), IdAllocator())
        # Hai đơn giữ trùng 1 cá thể I1 -> lỗi
        with self.assertRaises(BadInput):
            QuanSim(
                tuning,
                {
                    "stock": [{"id": "I1", "kind": "ca_loc", "fresh": 90}],
                    "customers": [
                        {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]},
                        {"id": "C2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]},
                    ],
                },
                Streams(1),
                IdAllocator(),
            )
        # Giữ cá thể đã ươn (fresh < 30) -> lỗi
        with self.assertRaises(BadInput):
            QuanSim(
                tuning,
                {
                    "stock": [{"id": "I1", "kind": "ca_loc", "fresh": 29.5}],
                    "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]}],
                },
                Streams(1),
                IdAllocator(),
            )
        # Giữ sai công thức -> lỗi
        with self.assertRaises(BadInput):
            QuanSim(
                tuning,
                {
                    "stock": [{"id": "I1", "kind": "bong_sung", "fresh": 90}],
                    "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]}],
                },
                Streams(1),
                IdAllocator(),
            )

    def test_07_spawn_customer_skips_spoiled_items_and_emits_no_dish(self):
        """AC-P3-03: Kho chỉ có cá thể đã ươn (< 30) -> không tính vào kho khả dụng, phát `no_dish`."""
        tuning = v12_tuning()
        sim = QuanSim(
            tuning,
            {"stock": [{"id": "I1", "kind": "ca_loc", "fresh": 20}]},
            Streams(1),
            IdAllocator(),
        )
        events_all = []
        for _ in range(120):
            events_all.extend(sim.step(idle_inp()))
        self.assertEqual(events_all, [("no_dish", {})])
        self.assertEqual(sim.customers, [])


if __name__ == "__main__":
    unittest.main()