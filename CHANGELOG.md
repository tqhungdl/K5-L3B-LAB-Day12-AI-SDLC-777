# Changelog

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
