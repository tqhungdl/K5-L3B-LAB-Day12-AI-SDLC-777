# ThanhDao11 — phản tư cá nhân

## Phase 1
- Tôi đã làm: Triển khai toàn bộ logic Lát 4 Quán (bếp nấu, bưng bê, phục vụ tại bàn, tính tiền, boa, uy tín, đóng ca) trong `chonoi/sim/quan.py`; viết test suite `tests/test_p1_quan_service.py` và tạo bằng chứng `docs/proof/phase-1/nguoi-4/service_proof.txt`.
- Tôi đã review: Rà soát kết nối giao diện tích hợp với Người 3 (`quan_customers.py`) theo kế hoạch tích hợp.
- AI sai ở đâu & phát hiện thế nào: AI ban đầu dùng bàn `T2` trong fixture test đóng ca khi contract v1.0 chỉ có bàn `T1`, khiến runner văng mã lỗi 2; phát hiện qua unittest.

## Phase 2
- Tôi đã làm:
  + Triển khai vòng lặp ngày đa pha `chonoi/sim/day.py` (`DaySim`, `resolve_day_plans`), quản lý chu kỳ Gather -> Quán -> Shop qua 1..5 ngày.
  + Triển khai màn hình nâng cấp `chonoi/sim/shop.py` (`ShopSim`), tính năng tạm dừng (pause/resume), tích hợp CLI `--mode day --days <1..5>`, cập nhật `inputs.py`, `runner.py` theo Test Contract v1.1.
  + Viết bộ test `tests/test_p2_day.py` (5 unit tests) và tạo bằng chứng `docs/proof/phase-2/nguoi-4/day_proof.txt`.
- Tôi đã review:
  + Kiểm tra hợp đồng v1.1 với các nhánh thành viên khác (Người 1, 2, 3), đảm bảo tương thích ngược không phá vỡ headless và deterministic bytes.
- AI sai ở đâu & phát hiện thế nào:
  + AI test pause dùng thiếu frame nhả nút (release frame), làm nút pause bị kẹt ở trạng thái held khiến game không unpause; phát hiện khi test timeout và đã bổ sung rising edge chính xác.

## Phase 3
- Tôi đã làm:
  + Cập nhật `DaySim` (`chonoi/sim/day.py`) và `ShopSim` (`chonoi/sim/shop.py`) sang cấu trúc kho cá thể `{id, kind, fresh}`, duy trì `IdAllocator` liên tục xuyên suốt các Ngày mà không bị trùng lặp ID.
  + Chuẩn hóa `runner.py`: sự kiện `phase_start` mang đúng tên pha và ngày mới; xuất snapshot chuyển pha tại `phase_tick: 0`.
  + Nâng cấp `live.py` hỗ trợ `--mode day --days 1..5` và cập nhật client HUD `index.html` hiển thị trực quan độ tươi, cảnh báo hàng ươn (`fresh < 30`) và kho khả dụng.
  + Viết bộ test `tests/test_p3_day.py` (4 tests), cập nhật `tests/test_live.py` và tạo bằng chứng `docs/proof/phase-3/nguoi-4/day_proof.txt`.
- Tôi đã review:
  + Review chéo với Người 1 (`p3/inventory`) theo kế hoạch tích hợp v1.2, đảm bảo tương thích ngược và 93 unit tests toàn bộ đều pass.
- AI sai ở đâu & phát hiện thế nào:
  + Khi sửa runner, vòng lặp thiếu ghi snapshot cuối (`last_snapped != sess.tick`), khiến test đóng ca kiểm snapshot bị thiếu; phát hiện qua unittest và đã khôi phục đúng quy ước Contract B.
- Điều tôi học được:
  + Quản lý state chuyển đổi mô hình dữ liệu (từ count map sang object list) cần đặc biệt chú ý tính toàn vẹn của snapshot và chu kỳ sống của ID cá thể.
