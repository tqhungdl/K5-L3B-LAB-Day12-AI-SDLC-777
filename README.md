# Day 12 — AI SDLC: Quán Ăn Chợ Nổi

> **Làm theo nhóm 4–6 người** · Dùng AI để xây game 2D qua **4 phase** trong **3 giờ**: Út Sen lặn bắt cá, hái rau trên mặt nước rồi tối mở quán phục vụ khách.
> **Yêu cầu từng phase mở đúng mốc giờ tại lab board:** **[Chợ Nổi Lab](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg)** (cần đăng nhập claude.ai; có trợ giảng AI cho từng phase).

## Bắt buộc (chỉ có thế)

Cách làm việc kỹ thuật là **tự do** (push thẳng, nhánh + PR, pair, có hay không CI…). Cái bắt buộc:

1. **Một repo chung:** trưởng nhóm **fork** repo này, đặt tên `K5-L3B-LAB-Day12-AI-SDLC-<ten-nhom>`, thêm mọi thành viên làm collaborator (*Settings → Collaborators*, quyền Write) và để repo **public** (giảng viên xem được, không cần mời).
2. **Cả nhóm cùng commit** bằng tài khoản GitHub của mình, mỗi người **≥ 3 commit có nội dung** (làm cặp thì ghi `Co-authored-by:`).
3. **Điền [`TEAM.md`](TEAM.md):** danh sách thành viên + thỏa thuận làm việc nhóm; sửa `team_size` trong [`game.contract.json`](game.contract.json). Commit của người không có trong `TEAM.md` không được tính.
4. **Gắn tag** `phase-1` … `phase-4` đúng hạn; chạy được tại từng tag.
5. **Ghi chép tối thiểu:** `docs/verification/phase-n.md`, `docs/clarify.md`, `docs/ai-usage-log.md`, `docs/retro.md`, `docs/members/<handle>.md`.

## Bắt đầu nhanh (Khởi chạy từ clone sạch ≤ 3 lệnh)

Yêu cầu môi trường: **Python 3.10+** (macOS, Linux hoặc Windows). Trò chơi chỉ sử dụng thư viện chuẩn của Python, không yêu cầu cài thêm thư viện ngoài để chơi và kiểm thử lõi.

Khởi chạy trong tối đa 3 lệnh:
```bash
git clone 'https://github.com/tqhungdl/K5-L3B-LAB-Day12-AI-SDLC-777.git' cho-noi && cd cho-noi
python3 -m unittest discover -s tests -v
python3 -m chonoi.live --mode day --days 5
```
Mở trình duyệt tại địa chỉ được in trong terminal (mặc định `http://127.0.0.1:8000`) để trải nghiệm toàn bộ chu trình 5 Ngày (Lặn & Hái $\rightarrow$ Mở Quán $\rightarrow$ Cửa hàng Má Tư).

### Các lệnh CLI chính (Test Contract v1.3)
- **Chơi trực tiếp (Live)**:
  - Vòng ngày chuẩn (5 ngày): `python3 -m chonoi.live --mode day --days 5`
  - Ca Lặn & Hái độc lập: `python3 -m chonoi.live --mode gather --inventory-out catch.json`
  - Ca Mở Quán độc lập: `python3 -m chonoi.live --mode quan --inventory catch.json`
- **Mô phỏng không giao diện (Headless)**:
  - `python3 -m chonoi.headless --mode day --days 5 --seed 42 --ticks 1800 --out day.jsonl`
  - `python3 -m chonoi.headless --mode gather --seed 42 --ticks 600 --out gather.jsonl`
  - `python3 -m chonoi.headless --mode quan --seed 42 --ticks 600 --inventory catch.json --out quan.jsonl`
- **Đo hiệu năng render (Benchmark)**:
  - Cài riêng cho benchmark: `python3 -m pip install playwright` và `python3 -m playwright install chromium`.
  - `python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json`
  - Có thể đặt biến môi trường `CHONOI_BENCH_CHANNEL=msedge` hoặc `chrome` để dùng trình duyệt tương ứng đã cài.
- **Kiểm tra độ bền 10 ngày (Soak Headless)**:
  - `python3 -m chonoi.soak --seed 7 --days 10 --out soak.json`
- **Bộ kiểm thử tự động (Test Suite)**:
  - `python3 -m unittest discover -s tests -v`

### Điều khiển
- **Di chuyển**: `W`, `A`, `S`, `D` hoặc phím mũi tên (bơi khi lặn, đi lại trong quán).
- **Tương tác**: `E` để hái rau, cập bến, bắt đầu nấu tại bếp hoặc bưng món phục vụ khách tại bàn.
- **Bắt cá**: `Space` khi lặn để phóng vợt bắt cá trong tầm.
- **Tạm dừng**: `P` để đóng băng bộ đếm mô phỏng.
- **Chơi lại**: `R` để reset lại ca chơi.
- **Chế độ tương phản cao**: Nút bật/tắt trên giao diện HUD hoặc bấm phím để tăng độ tương phản hiển thị.

## Bàn giao kho cá thể & Độ tươi (Test Contract v1.2 & v1.3)

File kho lưu trữ danh sách cá thể `{id, kind, fresh}`:
```json
{
  "items": [
    {"id": "I1", "kind": "ca_loc", "fresh": 100.0},
    {"id": "I2", "kind": "bong_sung", "fresh": 98.5}
  ]
}
```
- Độ tươi ban đầu: 100. Hao tươi ở giỏ (Gather): `0.5/s`; hao tươi ở kho (Quán): `0.25/s`.
- Ngưỡng ươn: `fresh < 30` phát sinh sự kiện `spoiled` và không thể nấu món.
- Test Contract v1.3 từ chối file kho đếm cũ với mã lỗi 2.

## Tính năng nổi bật Phase 4 (v1.0.0)
- **Accessible UI**: Cảnh báo trực quan bằng nhãn và biểu tượng cho thủy quái đến gần, oxy dưới 25%, và khách chờ sắp hết kiên nhẫn (< 25%).
- **High Contrast Mode**: Chế độ tương phản cao hỗ trợ người dùng khiếm thị màu.
- **Hiệu năng & Độ bền**: Hỗ trợ đầy đủ bộ công cụ đo benchmark render và soak headless 10 ngày liên tục không dừng tiến trình.

## Tự do sáng tạo

Ngoài phần đề yêu cầu, nhóm được **thêm** nhân vật, loài cá/cây, sinh vật, món, bản đồ, cơ chế, câu chuyện, đồ họa, âm nhạc… với ba điều kiện: **không phá phần cố định** (tắt ở headless), ghi mục **"Sáng tạo của nhóm"** trong README của nhóm, và **làm lõi đúng trước**.

## Lịch 3 giờ

| Mốc | Phase | Hạn tag |
|---|---|---|
| 0:00 | Phase 1 (PRD-0) | `phase-1` trước 1:00 |
| 1:00 | Phase 2 | `phase-2` trước 1:55 |
| 1:55 | Phase 3 | `phase-3` trước 2:30 |
| 2:30 | Phase 4 | `phase-4` + Release `v1.0.0` trước 3:00 |

Hết giờ mỗi phase thì gắn tag rồi đi tiếp; chỗ chưa xong ghi trung thực trong bằng chứng.

## Đánh giá (100 điểm)

| Hạng mục | Điểm |
|---|---|
| Test tự động ẩn (headless, gồm kiểm tra lại phase trước) | 25 |
| Làm việc nhóm (một repo chung, chia việc, tích hợp, đổi yêu cầu) | 25 |
| Kiểm chứng & bằng chứng | 15 |
| Harness AI (AGENTS.md, skill, nhật ký dùng AI) | 10 |
| Đánh giá & retro | 10 |
| Chất lượng sản phẩm (đúng yêu cầu, mở rộng/sáng tạo) | 10 |
| Demo | 5 |

## Quy định

- Dùng AI thoải mái; **không sao chép repo của nhóm khác**; bằng chứng phải thật.
- Nhân vật, bối cảnh là bản gốc của lab; asset ngoài chỉ dùng CC0/CC-BY/MIT hoặc tự tạo, ghi nguồn trong `CREDITS.md`. Không commit API key, token, `.env`.
