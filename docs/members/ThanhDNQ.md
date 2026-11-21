# ThanhDNQ — phản tư cá nhân

## Phase 1
- Tôi đã làm: Triển khai toàn bộ logic Lát 4 Quán (bếp nấu, bưng bê, phục vụ tại bàn, tính tiền, boa, uy tín, đóng ca) trong `chonoi/sim/quan.py`; viết test suite `tests/test_p1_quan_service.py` và tạo bằng chứng `docs/proof/phase-1/nguoi-4/service_proof.txt`.
- Tôi đã review: Rà soát kết nối giao diện tích hợp với Người 3 (`quan_customers.py`) theo kế hoạch tích hợp.
- AI sai ở đâu & phát hiện thế nào: AI ban đầu dùng bàn `T2` trong fixture test đóng ca khi contract v1.0 chỉ có bàn `T1`, khiến runner văng mã lỗi 2; phát hiện qua unittest.

## Phase 2
- Tôi đã làm:
  + Triển khai vòng lặp ngày đa pha `chonoi/sim/day.py` (`DaySim`, `resolve_day_plans`), quản lý chu kỳ Gather -> Quán -> Shop qua 1..5 ngày.
  + Triển khai màn hình nâng cấp `chonoi/sim/shop.py` (`ShopSim`), tính năng tạm dừng (pause/resume), tích hợp CLI `--mode day --days <1..5>`, cập nhật `inputs.py`, `runner.py`, `scenario.py` theo Test Contract v1.1.
  + Viết bộ test `tests/test_p2_day.py` (5 unit tests) và tạo bằng chứng `docs/proof/phase-2/nguoi-4/day_proof.txt`.
- Tôi đã review:
  + Kiểm tra hợp đồng v1.1 với các nhánh thành viên khác (Người 1, 2, 3), đảm bảo tương thích ngược không phá vỡ headless và deterministic bytes.
- AI sai ở đâu & phát hiện thế nào:
  + AI test pause dùng thiếu frame nhả nút (release frame), làm nút pause bị kẹt ở trạng thái held khiến game không unpause; phát hiện khi test timeout và đã bổ sung rising edge chính xác.
- Điều tôi học được:
  + Quản lý kiến trúc đa trạng thái phân tầng (Day/Phase/Sim) cùng hợp đồng sự kiện v1.1 giúp mở rộng tính năng phức tạp một cách độc lập và bảo đảm tính tiền định (determinism).
