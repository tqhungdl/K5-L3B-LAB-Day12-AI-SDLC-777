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
- **Rà lại hành động Phase 2 (đã làm chưa? vì sao?):**
  - Hành động chốt ở Phase 2: *"Phase 3, Scrum/Release chuẩn bị fixture bàn giao có vật phẩm mới ngay lúc kickoff. Integrator chạy qua CLI và lưu kết quả theo SHA ở mốc standup."*
  - Kết quả thực tế: **Mới đạt một phần.** Ở Phase 3, nhóm đã dựng fixture kho cá thể (`items: [{id, kind, fresh}]`) cho Gather/Quán/Day và lưu log kiểm thử theo từng lát (`docs/proof/phase-3/nguoi-{1,2,4}/`, `docs/verification/phase-3.md`). Tuy nhiên, manifest `game.contract.json` trên `main` cuối Phase 3 vẫn giữ `"contract_version": "1.1"` (chưa bật `1.2` + `tuning.freshness`) và fork chưa gắn tag/smoke tích hợp chung theo đúng SHA ở mốc standup phút 20 vì các nhánh lát tập trung hoàn thiện test đơn lẻ sát giờ. Phần đồng bộ manifest `v1.3` và kiểm smoke kho cá thể trên manifest thật được xử lý dứt điểm ở Phase 4 (`p4/release-contract` phối hợp với `p4/headless-soak`).
- **Điều tốt / điều tệ:**
  - *Điều tốt:* Phân chia phạm vi ghi rõ theo file ở `docs/plan/phase-{1..4}.md` và tài liệu giao diện tích hợp giảm mạnh xung đột git; toàn bộ unit test `P1–P3` chạy tất định, nhanh; tách riêng lối gọi `allow_extended_days=True` cho `chonoi/soak.py` giúp giữ nguyên ràng buộc `1..5` Ngày của CLI thường mà vẫn soak được 10 Ngày trên một `Session`/`DaySim`.
  - *Điều tệ:* Chưa bật manifest mới (`1.2`) sớm ngay khi tích hợp Phase 3 khiến nhiều test phải dựng fixture `tuning.freshness` cục bộ thay vì kiểm trực tiếp với `game.contract.json`; việc cập nhật `docs/ai-usage-log.md` và gắn tag cuối phase chưa đều giữa tất cả thành viên.
- **Số liệu (tính tại `git shortlog -sn --all` trước mốc tích hợp Phase 4 và `docs/ai-usage-log.md`):**
  - *Số commit theo tác giả trong lịch sử repo (`git shortlog -sn --all`):* `chesschillchill`: 20, `Hai Duong`: 9, `tqhungdl`: 8, `nguyenquanghuy091204`: 4, `Dao Nguyen Quang Thanh`: 2, `ThanhDao11`: 1 (tổng 44 commit trên các nhánh đã đồng bộ).
  - *Cách đọc code của nhau:* Chia review chéo theo cặp giao diện (`1 ↔ 2` cho hook render/UI, `3 ↔ 4` cho soak/contract & release), đối chiếu trực tiếp diff theo phạm vi file trong kế hoạch phase và chạy lại bộ `unittest` trên bản tích hợp trước khi merge.
  - *Token theo người (ghi nhận hiện có trong `docs/ai-usage-log.md`):* `ThanhDao11`: ~120k tokens qua 3 phase (P1 ~35k, P2 ~45k, P3 ~40k với Gemini 3.8 Flash); `Lát 1 (PO)`: Codex (chưa đo định lượng token ở P2–P3); các thành viên còn lại bổ sung định lượng cuối vào `docs/ai-usage-log.md` khi nộp `docs/members/<handle>.md`.
- **Một lần AI sai và cách nhóm phát hiện:**
  - Ở Phase 3, AI triển khai `chonoi/runner.py` bỏ sót snapshot cuối khi kết thúc ca và chưa đảm bảo snapshot `phase_tick: 0` ngay lúc chuyển pha trong chế độ `day` (ghi nhận trong `docs/ai-usage-log.md`). Nhóm phát hiện khi đối chiếu trực tiếp Contract B và chạy kiểm tra JSONL trong `tests/test_p3_day.py` (`test_04_phase_transition_snapshot_at_phase_tick_zero`), từ đó bổ sung ghi snapshot ngay khi đổi pha và snapshot cuối trước dòng `end`.
  - Ngoài ra ở Phase 2, AI sinh fixture test `pause` thiếu frame nhả nút (`false`) khiến `InputPlayer` giữ trạng thái `held` và không tạo cạnh lên; lỗi bị chặn ngay khi chạy `unittest` và sửa lại thành chuỗi `true -> false -> true`.
- **Nếu làm lại, đổi gì:**
  - Đóng băng và bật `contract_version` mới trên nhánh tích hợp sớm ngay giữa phase (phút 15–20) rồi chạy 1 lệnh smoke CLI gắn SHA để không lệch giữa unit test dùng fixture và manifest thật.
  - Cập nhật `docs/ai-usage-log.md` và `docs/verification/phase-X.md` ngay trong cùng PR hoàn thành lát thay vì dồn sang cuối phase.
