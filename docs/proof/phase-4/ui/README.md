# Bàn giao Phase 4 · Lát 2 UI/Live

- Nhánh `p4/accessible-ui`. Commit chứa mã đã kiểm `f49728b618b98cbd75da9f9bead2038f168b5b38`.
- Hồi quy trên manifest của nhánh và fixture kho cá thể v1.2 trong test Live. Chrome 157 headless có render canvas ở 1280×720 trên Linux x86_64, dùng manifest v1.2 tạm thời với cấu hình độ tươi Phase 3.
- `chonoi/live.py` được sửa để nối màn trình bày vào phiên chơi và xuất kho cá thể ở Shop qua `item_rows()`. Trở về menu dựng lại lượt với cùng seed và scenario. Chơi lại ở Day mở màn giới thiệu Ngày 1. Tương phản cao mặc định tắt mỗi lần tải trang.

| AC | Đã kiểm trên nhánh UI | Bằng chứng |
|---|---|---|
| AC-P4-02 | Gather thật, seed 42, đứng ở bến, hook trả các timestamp hữu hạn và tăng dần. Hook im lặng ở demo, menu, intro và sau khi vào Quán. | [Log Chrome](browser.log) |
| AC-P4-03 | Bật/tắt bằng Tab, Enter và Space. Tương phản chữ trên Live lần lượt 12,16:1 cho thủy quái, 11,22:1 cho oxy và 9,02:1 cho khách sắp giận. Demo kiểm mốc 25%, oxy cạn/hồi và khách ngừng chờ. | [Gather thường](gather-default.png) · [Gather tương phản cao](gather-contrast.png) · [Quán tương phản cao](quan-contrast.png) |
| AC-P4-07 | Chơi một Ngày trên Live qua cả hai ca, kết quả, đóng Shop và Tổng kết. Test HTTP kiểm thời gian đứng yên ở màn chờ, số liệu phục vụ, boa, uy tín và kho cá thể. | [Tổng kết](day-summary.png) · [Log Chrome](browser.log) · [114/114 test](unittest.log) |

Bố cục Gather vừa cửa sổ 1280×720 và giữ cảnh báo trong cảnh chơi ở 390×844.

Chạy lại hồi quy từ gốc repo.

```bash
PYTHONPATH=tests:. python3 -m unittest test_live -v
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
```

Ca Chrome dùng hai fixture Live. Gather bắt đầu ở `[58,22]` với 420 tick oxy và Cá Sấu ở `[64,22]`. Day bắt đầu ở bến, mang một cá lóc tươi và hai bông súng, trong đó một cá thể đã ươn. Cập bến bằng E, màn nhập kho hiện cả hai bông súng nhưng chỉ báo món cá lóc đủ nguyên liệu. Ca Quán dài 480 tick với một khách chờ 600 tick ở T1 để bắt cảnh báo rồi đóng Shop.

Trên bản ghép, người 1 chạy benchmark 30 giây và ghi bằng chứng vào ma trận. Người 4 bật manifest v1.3 để kiểm lại một Ngày qua giao diện với kho cá thể. Số đo benchmark và kiểm tra manifest v1.3 còn chờ bản ghép.

**Ca tái hiện cho Headless/Release.** Trên commit bàn giao, gọi `runner.run()` ở mode `day` với cấu hình v1.2 và fixture dưới đây. Chạy 5 tick, `snapshot_every=1`. Khi Quán chuyển sang Shop và còn kho cá thể, ghi JSONL gặp `TypeError: Object of type Fraction is not JSON serializable`. Snapshot Shop lộ trường nội bộ `stock[0]._fresh`. Live đã chuẩn hóa stock ở đầu ra HTTP. Cần kiểm lại ca tương ứng ở Headless trên bản ghép.

```json
{
  "gather": {
    "time_left_ticks": 1,
    "hold": [{"id": "I1", "kind": "ca_loc", "fresh": 95}]
  },
  "quan": {"time_left_ticks": 2, "random_customers": false}
}
```
