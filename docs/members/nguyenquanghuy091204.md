# nguyenquanghuy091204 — phản tư cá nhân

- **Tôi đã làm (kèm link commit):**
  - P1: khách, giữ nguyên liệu Quán & `scenario.py` ([`232bdcb`](https://github.com/tqhungdl/K5-L3B-LAB-Day12-AI-SDLC-777/commit/232bdcb)).
  - P2: 2 bếp/4 bàn, 6 món, lọc kế hoạch ngày & giao diện Quán ([`1fdd183`](https://github.com/tqhungdl/K5-L3B-LAB-Day12-AI-SDLC-777/commit/1fdd183)).
  - P3: kho cá thể, hao tươi, giá theo tươi Quán ([`ce58224`](https://github.com/tqhungdl/K5-L3B-LAB-Day12-AI-SDLC-777/commit/ce58224)) và chạy thật ma trận kiểm chứng P1–P3 ([`9813650`](https://github.com/tqhungdl/K5-L3B-LAB-Day12-AI-SDLC-777/commit/9813650)).
  - P4 (`p4/headless-soak`): `chonoi/soak.py`, mở rộng `DaySim`/`Session` 10 Ngày, `tests/test_p4_soak.py`, `docs/retro.md`, bằng chứng `docs/proof/phase-4/soak*`.
- **Tôi đã review & hỗ trợ:** Phối hợp giao diện Quán/Day với `ThanhDao11` ([PR #9](https://github.com/tqhungdl/K5-L3B-LAB-Day12-AI-SDLC-777/pull/9)), bổ sung bằng chứng P1–P3 ([`9813650`](https://github.com/tqhungdl/K5-L3B-LAB-Day12-AI-SDLC-777/commit/9813650)), và rà chéo cặp `p4/headless-soak` ↔ `p4/release-contract` (giữ `headless --days 6` mã `2`).
- **AI sai ở đâu và tôi phát hiện thế nào:** Trên Windows, AI dùng `Set-Content -Encoding utf8` tạo UTF-8 BOM làm `json.load` báo lỗi đọc fixture/proof; tôi phát hiện khi chạy thật `unittest` và smoke CLI, sửa sang ghi UTF-8 không BOM qua Python.
- **Điều tôi học được:** Luôn đối chiếu Test Contract, chạy thật lệnh kiểm chứng thay vì đoán kết quả, và khóa ranh giới file rõ theo lát để tránh xung đột git.
