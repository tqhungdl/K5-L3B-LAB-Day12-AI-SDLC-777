# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| 1 | ThanhDNQ | Gemini 3.8 Flash | Triển khai logic Lát 4 Quán (bếp, phục vụ, tiền) & test suite | ~35k tokens | AI đưa nhầm bàn T2 trong fixture test đóng ca, đã sửa lại T1 theo contract |
| 2 | ThanhDNQ | Gemini 3.8 Flash | Triển khai Lát 4: Day loop, Shop upgrades, Pause & runner v1.1 | ~45k tokens | AI viết test pause thiếu release frame gây kẹt held, đã sửa edge rising hợp lệ |
| 2 | Lát 1 (PO) | Codex | Tích hợp manifest v1.1 và cá bơi/sinh theo seed trên main; kiểm kho mới và chạy đủ 5 Ngày | Chưa đo | Dùng các hook Gather và kiểm fixture đã merge. |
