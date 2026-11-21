# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| 1 | ThanhDao11 | Gemini 3.8 Flash | Triển khai logic Lát 4 Quán (bếp, phục vụ, tiền) & test suite | ~35k tokens | AI đưa nhầm bàn T2 trong fixture test đóng ca, đã sửa lại T1 theo contract |
| 2 | ThanhDao11 | Gemini 3.8 Flash | Triển khai Lát 4: Day loop, Shop upgrades, Pause & runner v1.1 | ~45k tokens | AI viết test pause thiếu release frame gây kẹt held, đã sửa edge rising hợp lệ |
| 2 | Lát 1 (PO) | Codex | Tích hợp manifest v1.1 và cá bơi/sinh theo seed trên main; kiểm kho mới và chạy đủ 5 Ngày | Chưa đo | Dùng các hook Gather và kiểm fixture đã merge. |
| 3 | ThanhDao11 | Gemini 3.8 Flash | Triển khai Day/Shop kho cá thể, runner v1.2, HUD hiển thị độ tươi, test suite Phase 3 | ~40k tokens | AI runner thiếu snapshot cuối khi kết thúc ca, đã bổ sung theo chuẩn Contract B |
| 3 | Lát 1 (PO) | Codex | Adapter kho v1.2, kiểm scenario và giữ độ chính xác của độ tươi trong JSONL | Chưa đo | Giữ manifest mặc định ở v1.1 trong khi các lát tích hợp consumer. |
| 4 | ThanhDao11 | Gemini 3.8 Flash | Nâng cấp Contract v1.3, đồng bộ schema kho cá thể, kiểm thử đóng gói & tài liệu phát hành v1.0.0 | ~42k tokens | AI bỏ quên điểm so cứng v1.2 trong scenario và fish_data, đã sửa thành in ("1.2", "1.3") |
| 4 | Bench/QA | Codex | Benchmark Edge, hồi quy v1.3, sửa JSONL Shop và kiểm gói ứng viên | Chưa đo | Kiểm chính xác giá trị float trong test mới phát hiện làm tròn ở đầu nối Gather → Quán; giữ phân số trong bộ nhớ, chỉ chuyển số lúc xuất. |
