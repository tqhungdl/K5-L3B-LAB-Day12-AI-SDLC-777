# Kế hoạch Phase 4 · Phát hành v1.0.0

Trong 30 phút, hoàn thành Contract v1.3, benchmark có render, soak 10 Ngày, cảnh báo dễ nhận biết và bản phát hành. Hạn đẩy `phase-4` và công bố GitHub Release `v1.0.0` là **3:00**. Cả hai trỏ tới cùng commit bàn giao trên `main`. Nhóm 4 người tập trung phần lõi.

## Việc cần sửa trên từng nhánh

| Người / nhánh | Phần phụ trách | Phạm vi ghi |
|---|---|---|
| **1 · Bench/QA** · `p4/render-bench` | Dựng lệnh benchmark bằng trình duyệt thật và cảnh Gather mặc định. Đo khung thực, kiểm phép tính 1% low và lưu artifact. Chạy regression cuối, tổng hợp ma trận từ bằng chứng cả nhóm. | `chonoi/bench.py` (mới), file phụ thuộc benchmark nếu cần, `tests/test_p4_bench.py`, `docs/verification/phase-4.md`, `docs/proof/phase-4/bench*` |
| **2 · UI/Live** · `p4/accessible-ui` | Thêm chữ/biểu tượng cho thủy quái gần, oxy thấp và khách sắp giận. Thêm chế độ tương phản cao và kiểm cả ba cảnh. Nối hook đo khung cho người 1. Sửa lỗi kế thừa `/presentation` đang trả OK nhưng bỏ qua hành động để demo được một Ngày thật. | `chonoi/web/index.html`, `chonoi/live.py`, `tests/test_live.py`, `docs/proof/phase-4/ui/` |
| **3 · Soak/Retro** · `p4/headless-soak` | Viết lệnh soak với một Session, giữ trạng thái xuyên 10 Ngày và ghi kết quả lúc Shop đóng. Sửa giới hạn nội bộ của Day theo lối gọi riêng. Rà hành động đã chốt ở retro P2, tổng hợp lỗi AI thực tế và phản tư. | `chonoi/soak.py` (mới), `chonoi/runner.py`, `chonoi/sim/day.py`, `tests/test_p4_soak.py`, `tests/test_p3_day.py`, `docs/retro.md`, `docs/proof/phase-4/soak*` |
| **4 · Đóng gói/Release** · `p4/release-contract` | Bật v1.3 với tuning độ tươi Phase 3, sửa các điểm còn so cứng version v1.2, khai lệnh bench/soak. Thử clone sạch và gói đã giải nén. Chốt hồ sơ, tích hợp, gắn tag và công bố Release. | `game.contract.json`, `chonoi/{contract,inventory,scenario,headless}.py`, `tests/test_p3_inventory.py`, `tests/test_p4_contract.py`, `PHASE4.md`, `README.md`, `CHANGELOG.md`, `CREDITS.md`, `LICENSE` nếu đã xác định quyền, `AGENTS.md`, `TEAM.md`, `docs/{clarify,ai-usage-log}.md`, `docs/proof/phase-4/release/` |

Người 1 và 2 thống nhất hook render trước khi sửa file. Người 3 và 4 thống nhất tên lệnh, phiên bản và đường gọi soak. Review chéo **1 ↔ 2**, **3 ↔ 4**. Mỗi người dùng clone/worktree riêng từ cùng commit gốc và chỉ ghi file đã phân công. Tạo thư mục bằng `mkdir -p docs/proof/phase-4` trước khi ghi kết quả. Chủ feature gửi kết quả và đường dẫn bằng chứng cho người 1 để cập nhật ma trận.

### `p4/render-bench`

- [ ] Tạo `chonoi/bench.py`. Nhận `--seed`, `--duration` và `--out`; mở cảnh Gather thật, mặc định đứng ở bến, cửa sổ 1280×720. Nhận timestamp từ hook `window.__chonoiBenchFrame` sau khung Gather do nhánh UI cung cấp.
- [ ] Đo thời gian tới khung đầu, làm nóng 3 giây và đo theo thời lượng CLI. Tính `avg_fps` và `p1_low_fps` từ thời gian khung thực. Thêm test dùng timestamp cố định để kiểm số khung và nhóm 1% khung chậm nhất.
- [ ] Chạy `python3 -m chonoi.bench --seed 42 --duration 30 --out docs/proof/phase-4/bench.json` trên bản đã ghép với manifest v1.3. Lưu cấu hình máy, chế độ render và kết quả so với ba mốc báo cáo. Tổng hợp regression và dẫn bằng chứng vào ma trận.

### `p4/accessible-ui`

- [ ] Trong `chonoi/web/index.html`, thêm nhãn hoặc biểu tượng cho **thủy quái gần**, **oxy dưới 25%** và **khách đang chờ còn dưới 25% kiên nhẫn**. Thêm nút tương phản cao dùng được bằng bàn phím. Kiểm ba cảnh báo ở chế độ đó và lưu bằng chứng.
- [ ] Gọi hook benchmark sau khi vẽ xong mỗi khung Gather thật có snapshot. Để nhánh Bench kiểm hợp đồng timestamp; UI giữ quyền sửa `index.html`.
- [ ] Sửa lỗi có sẵn trong `chonoi/live.py`: `GET /state` cần trả trạng thái `presentation`, `POST /presentation` cần xử lý `advance` và `menu`. Kiểm trong `tests/test_live.py` và chơi lại một Ngày qua intro, Gather, Quán, kết quả, Shop và Tổng kết. Kiểm timer dừng khi chờ màn giới thiệu.

### `p4/headless-soak`

- [ ] Tạo `chonoi/soak.py` nhận `--seed`, `--days` và `--out`. Sửa giới hạn trong `runner.py` và `sim/day.py` để đường soak chạy 10 Ngày bằng một Session. CLI chơi và headless thường vẫn dùng 1–5 Ngày.
- [ ] Lặp kế hoạch D1–D5 ở Ngày 6–10 trong khi bộ đếm Ngày, tiền, tổng thu, uy tín, nâng cấp, RNG và ID cá thể tiếp tục. Ghi một kết quả cho đúng Ngày có `shop_end`, kể cả bước vừa dựng Ngày sau.
- [ ] Chạy `python3 -m chonoi.soak --seed 7 --days 10 --out docs/proof/phase-4/soak.json`. Kiểm `days_completed=10`, `crashes=0`, đủ 10 kết quả và so dữ liệu gameplay giữa hai lượt cùng seed. Rà việc còn lại trong retro Phase 2 và ghi một lỗi AI thực tế cùng cách phát hiện.

### `p4/release-contract`

- [ ] Bật `contract_version:"1.3"` và `tuning.freshness` trong manifest đang là v1.1. Sửa các điểm chọn schema trong `contract.py`, `inventory.py`, `scenario.py` và đường gọi CLI liên quan để v1.3 dùng kho cá thể. Khai `run_cmd`, `bench_cmd` và `soak_cmd` sau khi ghép.
- [ ] Kiểm với manifest thật: fixture độ tươi 30 phát `spoiled` ở tick 1, kho cá thể bàn giao đúng qua file và Day, kho đếm trả mã 2 và JSONL khớp v1.2 cho cùng fixture. Giữ kiểm lịch sử v1.1 theo fixture riêng.
- [ ] Hoàn thiện hướng dẫn clone sạch, cập nhật ví dụ kho cá thể và chạy thử gói zip/tar.gz đã giải nén. Bổ sung dữ liệu thật cho `TEAM.md`, `CREDITS.md`, nhật ký AI và changelog. Xác minh quyền trước khi thêm `LICENSE`, rà bằng chứng các mốc trước vì fork chưa có tag. Chốt SHA và công bố `phase-4` cùng Release `v1.0.0` có gói tải về.

## Quy tắc xử lý xung đột

1. **Luật giữa các phase.** Áp dụng ticket mới nhất cho đúng điều khoản đã đổi. Phase 4 thêm benchmark, soak và phát hành theo v1.3. Gameplay, kho cá thể và JSONL vẫn theo v1.2. Khi test cũ khác ticket mới, dẫn mục cụ thể rồi sửa đúng kỳ vọng đã đổi. Giữ các test hồi quy còn hiệu lực.
2. **File hoặc giao diện dùng chung.** Chủ file trong bảng là đầu mối sửa. Nhánh cần thay đổi gửi cho chủ file và Integrator: file hoặc giao diện, hành vi cũ/mới, nhánh bị ảnh hưởng và cách kiểm. Chốt cùng bên gọi trước khi đổi schema, hook, manifest hoặc lệnh CLI. Nhánh còn lại tiếp tục bằng fixture dựa trên giao diện đã thống nhất.
3. **Git báo conflict.** Giải quyết trên nhánh tích hợp hoặc nhánh đang làm. Dùng `git status` và `git diff --name-only --diff-filter=U` để xác định file. Chủ file và người có thay đổi cùng rà hai phía, giữ hành vi cần thiết của cả hai và chạy test phần bị ảnh hưởng. Tránh chọn toàn bộ “ours/theirs” hoặc force-push lên `main`. Integrator ghép vào `main` sau khi kiểm phần giao nhau.
4. **Chưa thống nhất cách xử lý.** Integrator chốt quyết định kỹ thuật với các chủ nhánh và ghi ngắn trong PR hoặc kế hoạch. PO chỉ hỏi khách hàng khi còn mơ hồ về trải nghiệm hay luật chơi. Nếu vướng cách bộ chấm hiểu Test Contract, hỏi giảng viên về đúng điều khoản. Ghi câu hỏi thực tế vào `docs/clarify.md`.
5. **Kiểm sau khi ghép.** Ghi quyết định, SHA, lệnh chạy, kết quả và người review trong PR hoặc ma trận. Trước khi đưa lên `main`, chạy regression và smoke cho điểm vừa đổi. Nếu vẫn lỗi, giữ thay đổi trên nhánh và ghi rõ tiêu chí chưa đạt.

Hai điểm cần rà cùng nhau khi ghép:

- `p4/render-bench` ↔ `p4/accessible-ui`: UI sở hữu `index.html`. Hai bên kiểm hook chỉ ghi timestamp sau khi khung Gather đã vẽ xong.
- `p4/headless-soak` ↔ `p4/release-contract`: Soak sở hữu vòng chạy 10 Ngày, Release sở hữu manifest và CLI thường. Kiểm cả `soak --days 10` và `headless --mode day --days 6` (trả mã 2), rồi smoke kho cá thể với manifest thật.

## Tích hợp và bàn giao

1. **Phút 0–15.** Đưa ticket và kế hoạch lên fork chung, chia nhánh. Người 2 có thể dùng demo snapshot để làm cảnh báo ngay; người 1 thử phép tính FPS độc lập; người 3 thử 6/10 Ngày với ca ngắn; người 4 chuẩn bị cấu hình và gói. Báo nhóm trước khi sửa manifest và các điểm kiểm schema.
2. **Phút 15–25.** Ghép hook render với bench và ghép soak với manifest v1.3 trên nhánh tích hợp. Standup phút 20. Trên bản ghép, kiểm kho cá thể, ca Day thật và clone sạch, chạy `bench`, `soak` và regression. Lưu log, ảnh, `bench.json` và `soak.json` cùng SHA. Rà retro P2, ghi một lỗi AI có thật và cách nhóm phát hiện. Mỗi người viết `docs/members/<handle>.md` **≤ 200 từ**, dẫn commit/bằng chứng và gửi nhật ký AI cho người 4. Điền đủ handle và đối chiếu tối thiểu 3 commit có nội dung mỗi người cho cả lab.
3. **Phút 25–30.** Người 1 chốt [ma trận kiểm chứng](../verification/phase-4.md). Người 4 chốt SHA bàn giao, tạo gói từ SHA đó, thử chạy gói sau khi giải nén, đẩy `phase-4` và tạo Release `v1.0.0` có asset. Release notes ghi điểm mới, lệnh chạy và giới hạn đã biết. Kiểm hai tag cùng SHA trên fork.
4. **Sau 3:00.** Demo trực tiếp hoặc video MP4 dưới 5 phút. Chơi một Ngày từ Gather tới đóng Shop, chạy test, chỉ ra đóng góp của bốn người và mở ma trận truy vết có bằng chứng.

Chi tiết giao diện, cách đếm và bàn giao nằm trong [giao diện tích hợp Phase 4](phase-4-integration.md).
