# TICKET-04 — Phát hành v1.0.0 (Phase 4)

**30 phút (2:30–3:00) · Test Contract v1.3 · Hạn đẩy tag `phase-4` và công bố GitHub Release `v1.0.0` 3:00.**

Đo hiệu năng của cảnh lặn, kiểm tra cách người chơi nhận cảnh báo, bàn giao bản chạy được từ repo sạch và tổng kết cách nhóm đã làm việc.

---

## 1. Lõi (mọi nhóm)

### Benchmark có render

```bash
<bench_cmd> --seed 42 --duration 30 --out bench.json

```

| Cấu hình          | Giá trị                                                                                         |
| ----------------- | ----------------------------------------------------------------------------------------------- |
| **Cảnh đo**       | Buổi sáng lõi với độ tươi, cá bơi, Cá Sấu Năm Chèo và hiệu ứng mặc định. Út Sen đứng yên ở bến. |
| **Seed**          | `42`.                                                                                           |
| **Cửa sổ**        | `1280×720`.                                                                                     |
| **Làm nóng / đo** | Làm nóng `3 s`, sau đó đo `30 s`.                                                               |

Runner gọi `<bench_cmd> --seed <int> --duration <giây> --out <bench.json>`. Xuất năm trường JSON. Các số sau minh họa định dạng:

```json
{
  "avg_fps": 72,
  "p1_low_fps": 38,
  "frames": 2160,
  "measured_s": 30,
  "load_ms": 2400
}
```

| Trường                 | Cách tính                                                                                                                      |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `frames`, `measured_s` | Số khung hình và số giây thực tế trong khoảng đo sau làm nóng.                                                                 |
| `avg_fps`              | `frames / measured_s`.                                                                                                         |
| `p1_low_fps`           | Chọn `max(1,ceil(0.01 × frames))` khung chậm nhất rồi lấy nghịch đảo thời gian trung bình của chúng, tính thời gian theo giây. |
| `load_ms`              | Mili giây từ lúc khởi chạy đến khung hình đầu tiên của cảnh đo.                                                                |

Điểm phần benchmark dựa trên việc chạy được lệnh và tạo đúng `bench.json`. Mốc `avg ≥ 60 FPS`, `1% low ≥ 30 FPS` và `load ≤ 10 s` dùng để báo cáo. Lưu artifact từ commit nộp trong `docs/proof/phase-4/`.

### Cảnh báo dễ nhận biết

Dùng chữ hoặc biểu tượng để người chơi nhận ra thủy quái gần, oxy sắp hết và khách sắp giận. Thêm chế độ tương phản cao và chơi thử cả ba cảnh báo ở chế độ đó.

### Đóng gói và phát hành

- Từ clone sạch, chạy được bản có giao diện theo `README.md` trong tối đa `3` lệnh trên macOS hoặc Linux. Ghi yêu cầu môi trường, điều khiển, lệnh test, lệnh headless và benchmark.
- Đính kèm bản đóng gói chạy được ở GitHub Release `v1.0.0`. Release notes do nhóm viết, nêu điểm mới, cách chạy và giới hạn đã biết. `CHANGELOG.md` ghi theo từng phase. Rà `CREDITS.md` và `LICENSE` cho tài sản đã dùng.
- Đặt `contract_version:"1.3"`, khai `bench_cmd` và `soak_cmd` ở gốc `game.contract.json`. Gameplay, tuning, kho và JSONL theo `v1.2`.

---

## 2. Soak headless (giảng viên chạy để báo cáo)

```bash
<soak_cmd> --seed 7 --days 10 --out soak.json

```

Lệnh nhận `--seed <int> --days <N> --out <soak.json>`. Giảng viên chạy `10` Ngày trong một tiến trình headless bằng script input hoặc bot tất định. Mỗi Ngày đi qua `gather → quan → shop`. Kế hoạch `D1–D5` lặp ở Ngày `6–10`. Tiền, tổng thu, uy tín, cấp nâng cấp, số Ngày và `id` cá thể tiếp tục xuyên suốt.

- `soak.json` có `days`, `days_completed`, `crashes`, `results`, `duration_s`. Mỗi phần tử `results[]` có `day`, `earned`, `reputation`, `score` tại lúc Shop đóng.
- Phép thử đạt khi `days_completed = days` và `crashes = 0`. So tính lặp ở các trường gameplay, bỏ số đo thời gian thực khi so. Không chấm ngưỡng bộ nhớ.

---

## 3. Mở rộng

Kỳ vọng tính cả buổi lab. Nhóm 4 người không bắt buộc, nhóm 5 hoàn thành ít nhất 1 mục, nhóm 6 ít nhất 2 mục. Nếu làm, ghi vào `README` và lưu bằng chứng.

**Tự do sáng tạo.** Khi lõi đã đúng, nhóm có thể hoàn thiện ý tưởng riêng, như đồ họa, âm nhạc hoặc giao diện. Tắt phần tự thêm ở headless hoặc giữ nguyên kết quả theo Test Contract. Ghi vào mục **“Sáng tạo của nhóm”** trong `README.md`, kèm bằng chứng ngắn cho thấy lõi vẫn đúng.

### Bảng xếp hạng cục bộ (`leaderboard`)

- Khai `leaderboard` trong `extensions`. Lưu bền vững top 10 cục bộ. Chỉ ghi một mục cho mỗi lượt chuẩn đủ `5` Ngày. Sắp điểm giảm dần, hòa thì mục ghi trước đứng trước, kể cả sau khi mở lại.
- `<run_cmd> --export-leaderboard <out.json> [--leaderboard <store.json>]` xuất bảng đã sắp. Mỗi mục có `name`, `score`, `days_completed`, `seed`. Tên Unicode khác rỗng.

```json
{
  "entries": [
    { "name": "Út Sen", "score": 300, "days_completed": 5, "seed": 42 }
  ]
}
```

- Headless mode `day` nhận cặp `--leaderboard <store.json> --player-name <name>`. Ghi đúng một mục khi chạy đủ `5` Ngày chuẩn, không scenario và `reason:"days_complete"`. Thiếu một cờ trong cặp hoặc sai mode thì mã `2`. Chạy test với store riêng. File xếp hạng không đổi JSONL. Soak không ghi xếp hạng.

### Phụ đề SFX

Hiện phụ đề cho các hiệu ứng âm thanh đã triển khai. Chơi thử với âm thanh tắt để kiểm phụ đề có hiện đúng lúc.

---

## 4. Quy trình nhóm

Nhóm tự chọn cách phối hợp và cùng commit vào fork chung bằng tài khoản GitHub của từng người. Ghi `Co-authored-by:` khi cùng làm một commit.

- Lên lại kế hoạch theo việc còn lại. Có thể chia hoặc kiêm các vai dưới đây và ghi phân công ở nơi nhóm tiện theo dõi:

| Vai                    | Việc                                                                                  |
| ---------------------- | ------------------------------------------------------------------------------------- |
| **Đóng gói**           | Thử từ clone sạch, ghi lệnh chạy, tạo bản phát hành.                                  |
| **Bench/QA**           | Chạy bench và regression, lưu artifact và ma trận ở `docs/verification/phase-4.md`.   |
| **Release/Integrator** | Kiểm commit bàn giao, viết release notes, rà `CHANGELOG`, gắn tag và công bố Release. |
| **Điều phối retro**    | Rà hành động đã chốt ở retro P2 và tổng hợp bằng chứng đóng góp.                      |

- Ghi `AC-P4-xx → bằng chứng → kết quả` chạy trên commit bàn giao trong `docs/verification/phase-4.md`. Cập nhật `docs/clarify.md` và `docs/ai-usage-log.md`.
- Mở đầu retro bằng việc rà lại hành động đã chốt ở P2, xem nhóm đã làm gì, còn vướng gì và vì sao. Ghi điều làm tốt, điều cần sửa và hành động tiếp theo trong `docs/retro.md`. Nêu một lỗi AI đã mắc và cách nhóm xác minh.
- Mỗi người viết `docs/members/<handle>.md` (`≤ 200` từ), nêu phần mình làm, đã giúp ai, AI sai ở đâu và bài học. Dẫn commit hoặc bằng chứng liên quan trong repo chung. Đánh giá cá nhân dựa trên bằng chứng đóng góp, phản tư và đánh giá chéo. Số PR và lượt review không dùng để chấm cá nhân.
- Đẩy `phase-4` và công bố Release `v1.0.0` từ cùng commit bàn giao trên `main` trước khi hết giờ build.

### Lịch gợi ý

| Phút trong phase | Việc                                                                                                                                     |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **0–15**         | Đo bench, cập nhật cảnh báo và tương phản, thử clone sạch, chạy regression và chuẩn bị Release song song.                                |
| **15–25**        | Retro và phản tư cá nhân. Phút `20` standup, rà vướng mắc và điều người đã xong sang hỗ trợ. Có thể `pair` chạy smoke trên bản tích hợp. |
| **25–30**        | Dự phòng và kiểm commit, artifact, tag, Release. Hạn đẩy `phase-4` và công bố `v1.0.0` `3:00`.                                           |

---

## Định nghĩa hoàn thành (DoD)

- [ ] Contract `v1.3` khai đúng lệnh. `bench_cmd` chạy cảnh chuẩn và tạo `bench.json` đúng cấu trúc. `soak_cmd` sẵn sàng cho runner lớp.
- [ ] Clone sạch chạy bằng tối đa `3` lệnh. Ba cảnh báo có chữ hoặc biểu tượng và chế độ tương phản cao hoạt động.
- [ ] Regression `P1–P3` còn hiệu lực đạt. `docs/verification/phase-4.md` và bằng chứng khớp commit gắn tag. Ghi chép làm rõ và nhật ký AI đã cập nhật.
- [ ] `CHANGELOG.md`, release notes và bản đóng gói đầy đủ. Tag `phase-4` và GitHub Release `v1.0.0` cùng trỏ tới commit trên `main`, chậm nhất `3:00`.
- [ ] Retro đã rà hành động P2 và chốt việc tiếp theo. Có phản tư cá nhân đủ người và bằng chứng đóng góp của từng người trong repo chung để đánh giá chéo.
- [ ] Nếu làm mở rộng, có bài kiểm và bằng chứng cho từng mục.

---

## Demo sau giờ build

Sau `3:00`, demo trực tiếp hoặc nộp video `.mp4` dưới `5` phút. Cả hai hình thức dùng cùng checklist:

1. Chơi một Ngày từ Lặn & Hái qua Mở Quán đến khi đóng Shop.
2. Chạy test và cho thấy kết quả đạt.
3. Chỉ ra bằng chứng chia việc, phối hợp và đóng góp của từng người trong repo chung.
4. Mở ma trận truy vết và chỉ ra bằng chứng tương ứng.
