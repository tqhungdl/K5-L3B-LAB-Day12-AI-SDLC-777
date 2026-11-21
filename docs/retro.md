# Retro nhóm

## Phase 1 — Ghi nhận từ lát 2

- Test trực tiếp module tài nguyên và dùng fixture HUD giúp kiểm được lát 2 trước khi các lát nối vào nhau. Smoke hai tiến trình xác nhận kho được bàn giao đúng.
- Test live cần quyền mở cổng localhost. Chạy với quyền đó đã đạt cả 38 test.
- Khi tích hợp, chạy lại một lượt có nguyên liệu thực sự được hái hoặc bắt và một lượt Quán từ nấu đến thu tiền. Gắn kết quả với SHA bàn giao.

## Phase 2 (nhanh)
- Fixture tắt cá động giúp lát 2 kiểm được Cá Sấu và thứ tự ngạt, hit, ngất trước khi nối các lát.
- Manifest hiện còn v1.0. Kiểm chuyển sang Quán trên hai sim đã chạy, còn smoke `--mode day` và kho có nguyên liệu mới cần chạy lại sau khi tích hợp.
- Phase 3, Scrum/Release chuẩn bị fixture bàn giao có vật phẩm mới ngay lúc kickoff. Integrator chạy qua CLI và lưu kết quả theo SHA ở mốc standup.

## Phase 3 — Lát 2 Gather

- Fixture có ID ngoài thứ tự nhặt giúp kiểm đồng thời thứ tự giỏ, thứ tự rơi LIFO và thứ tự xuất kho theo ID.
- Test sát ngưỡng 30 cần kiểm cả event lẫn số sau khi đọc JSON. Khi tích hợp, chạy ca này qua writer thật và đối chiếu với file kho để phát hiện hao chính xác trong sim nhưng sai ở đầu ra.

## Phase 4 (cuối)
- Rà lại hành động Phase 2: đã làm chưa? vì sao?
- Điều tốt / điều tệ:
- Số liệu: số commit theo người, cách đọc code của nhau, token theo người:
- Một lần AI sai và cách nhóm phát hiện:
- Nếu làm lại, đổi gì:
