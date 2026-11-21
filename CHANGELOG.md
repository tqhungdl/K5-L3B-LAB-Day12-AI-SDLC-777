# Changelog

## [Phase 4] - 2026-11-21
### Added & Changed
- **Test Contract v1.3**:
  - Kích hoạt `contract_version: "1.3"` và `tuning.freshness` trong `game.contract.json`.
  - Khai báo chuẩn hóa các lệnh ở gốc manifest: `run_cmd`, `bench_cmd`, `soak_cmd`.
  - Đồng bộ hệ thống schema kho cá thể kế thừa từ v1.2, từ chối file kho đếm với mã lỗi 2.
- **Hiệu năng & Độ bền**:
  - Tích hợp công cụ Benchmark render (`python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json`).
  - Hỗ trợ công cụ Soak Headless 10 ngày trong một tiến trình duy nhất (`python3 -m chonoi.soak --seed 7 --days 10 --out soak.json`).
- **Giao diện & Tiếp cận (Accessible UI)**:
  - Bổ sung chỉ báo cảnh báo trực quan: thủy quái đến gần, oxy dưới 25%, khách chờ sắp mất kiên nhẫn.
  - Hỗ trợ chế độ tương phản cao (High Contrast mode) bật/tắt bằng phím.
- **Đóng gói & Phát hành**:
  - Hoàn thiện tài liệu khởi chạy từ bản sao sạch trong tối đa 3 lệnh.
  - Đóng gói bản phát hành `v1.0.0` và gắn tag `phase-4`.

## [Phase 3] - 2026-11-21
### Breaking Changes
- **Kho cá thể (Test Contract v1.2)**: Chuyển cấu trúc kho từ map đếm sang mảng cá thể `{"items": [{"id": ..., "kind": ..., "fresh": ...}]}`. Ở Contract v1.2, nạp file kho dạng đếm cũ hoặc sai schema sẽ thoát với mã lỗi 2.
- **Cơ chế độ tươi (Freshness & Decay)**:
  - Giỏ (Gather) hao tươi `0.5/s`; kho (Quán) hao tươi `0.25/s`. Kẹp đáy ở 0.
  - Ngưỡng ươn: `fresh < 30` phát sinh sự kiện `spoiled` và không thể dùng để nấu món.
  - Giữ chỗ theo ID tươi nhất và chốt giá món theo độ tươi trung bình: `base_price = floor(giá niêm yết × avg(fresh) / 100)`.

### Added & Changed
- **Day & Shop Loop**: Bàn giao nguyên vẹn danh sách cá thể qua các pha Gather $\rightarrow$ Quán $\rightarrow$ Shop. Duy trì `IdAllocator` liên tục xuyên suốt các Ngày mà không bị trùng lặp ID.
- **Runner**: Chuẩn hóa sự kiện `phase_start` mang đúng tên pha và ngày mới. Snapshot chuyển pha ghi nhận ngay tại `phase_tick: 0`.
- **Live & HUD**: Hỗ trợ lệnh `python -m chonoi.live --mode day --days 1..5`. HUD hiển thị độ tươi theo từng cá thể, nhãn cảnh báo hàng ươn (`fresh < 30`) và tính tồn khả dụng chính xác.

## [Phase 2] - 2026-11-21
### Added
- Vòng lặp ngày đa pha (`--mode day --days 1..5`).
- Màn hình Shop nâng cấp (`oxygen`, `hp`) cuối ngày.
- Cơ chế Pause/Resume đóng băng bộ đếm mô phỏng.

## [Phase 1] - 2026-11-21
### Added
- Khởi tạo trò chơi Quán Ăn Chợ Nổi: Gather và Quán (Contract v1.0).
