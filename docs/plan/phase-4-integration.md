# Giao diện tích hợp Phase 4 · Test Contract v1.3

[Ticket 04](../../PHASE4.md) thêm benchmark, soak, khả năng nhận biết cảnh báo và quy trình phát hành. Gameplay, tuning, kho cá thể và JSONL tiếp tục theo [Ticket 03](../../PHASE3.md). v1.3 vẫn từ chối file kho đếm với mã 2. Lệnh chơi và headless thường giữ giới hạn 5 Ngày; lệnh soak có lộ trình riêng. Bảng xếp hạng và phụ đề SFX là mở rộng.

## Manifest và giao diện dùng chung

| Trường ở gốc `game.contract.json` | Giá trị |
|---|---|
| `contract_version` | `"1.3"` |
| `run_cmd` | `python3 -m chonoi.live --mode day --days 5` |
| `bench_cmd` | `python3 -m chonoi.bench` |
| `soak_cmd` | `python3 -m chonoi.soak` |

Người 4 bật lại `tuning.freshness = {initial:100,gather_decay_per_s:0.5,quan_decay_per_s:0.25,spoiled_below:30}` và kiểm mọi đường chọn schema trong `contract.py`, `scenario.py` và `inventory.py` để v1.2 và v1.3 đều chọn kho cá thể. V1.1 vẫn phục vụ các test lịch sử đọc schema riêng. Cùng fixture tại v1.2 và v1.3 phải có cùng gameplay và JSONL. Quán độc lập trong README cần ví dụ file dạng `{"items":[{"id":"I1","kind":"ca_loc","fresh":100}]}`.

## Benchmark render · Người 1 và 2

```bash
python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json
```

- Benchmark khởi động bản live chuẩn với seed yêu cầu, mở Gather mặc định ở viewport **1280×720**, để Út Sen đứng ở bến. Dùng browser có render thực và cùng canvas, hiệu ứng, cá, Cá Sấu và dữ liệu v1.3 như lúc chơi. Không dùng dữ liệu demo trong phép đo chuẩn. Chốt sớm backend đo, ví dụ Playwright với Chromium, và công bố phụ thuộc benchmark riêng với phụ thuộc chơi game.
- Người 2 gọi hook tùy chọn `window.__chonoiBenchFrame?.(now)` **sau khi cập nhật UI và vẽ xong** mỗi khung Gather thật đã có snapshot. Người 1 cài hook trước khi tải trang và thu thời điểm từng khung theo đồng hồ browser. Thời gian đến khung đầu tính từ lúc khởi chạy lệnh, dùng mốc thời gian cùng hệ quy chiếu. Chờ sau khung đầu **3 giây** để làm nóng, sau đó đo theo thời lượng CLI và dùng thời gian thực qua khung đo cuối.
- `bench.json` có đúng `{avg_fps,p1_low_fps,frames,measured_s,load_ms}`. `frames` nguyên dương, các trường còn lại là số hữu hạn theo đơn vị của ticket. `avg_fps = frames/measured_s`. Xếp các frame time giảm dần, lấy `max(1,ceil(0.01 × frames))` mẫu chậm nhất, tính `p1_low_fps = 1/mean(frame_time_s)` trên nhóm đó. Không lấy percentile của FPS trung bình từng giây. Đóng browser và server sau khi đo.
- Báo cáo mốc **60 FPS trung bình**, **30 FPS 1% low**, **tải ≤ 10 giây** cùng cấu hình máy và chế độ render. Điểm benchmark dựa trên khả năng chạy lệnh và tạo JSON đúng cấu trúc. Test tính số liệu bằng timestamp fixture; benchmark thật dùng khung đo thật.

## Cảnh báo, tương phản và Day live · Người 2

- Dùng cùng dữ liệu HUD hiện có để xác định **thủy quái gần**, **oxy dưới 25%** và **khách còn dưới 25% kiên nhẫn khi đang chờ**. Dùng nhãn chữ hoặc biểu tượng nhận biết riêng, chẳng hạn “Thủy quái!”, “Oxy sắp hết”, “Khách sắp giận”. Chỉ dùng thay đổi màu như tín hiệu bổ sung.
- Chế độ tương phản cao là cài đặt browser, mặc định tắt. Có nút bật/tắt dùng được bằng bàn phím và trạng thái nút rõ ràng. Có thể lưu boolean dưới khóa `chonoi.highContrast` nếu lưu qua lần mở lại. Cài đặt và hook render không can thiệp tick, input headless, scenario hay JSONL.
- `GET /state` dùng `presentation.screen` đã chốt từ Phase 2; `POST /presentation` xử lý `advance` và `menu`. Kiểm luồng thật đi qua intro, hai ca, kết quả, Shop và Tổng kết. Các màn trình bày không làm trôi gameplay timer. Dùng demo snapshot để kiểm cảnh báo trước khi chờ backend.

## Soak headless · Người 3

```bash
python3 -m chonoi.soak --seed 7 --days 10 --out soak.json
```

- Dùng **một Session/DaySim** cho toàn tiến trình. Cho phép số Ngày mở rộng qua điểm vào soak, giữ kiểm giới hạn `1..5` ở CLI thường. Kế hoạch lấy theo `1 + ((day - 1) % 5)`, còn số Ngày snapshot, event và kết quả vẫn tăng tới 10. Giữ tiền, tổng thu, uy tín, nâng cấp, RNG và `IdAllocator` chung. Không dựng tiến trình hoặc DaySim mới theo từng Ngày.
- Bot hoặc script dùng input tất định, chỉ dựa trên tick, seed và trạng thái mô phỏng. Có thể bắt đầu bằng kịch bản chờ qua ba pha rồi thêm fixture kiểm tính liên tục. Chỉ lấy kết quả **một lần khi có `shop_end`**, kể cả Shop cuối. Dùng số Ngày từ event kết Shop nếu sim đã dựng Ngày kế trong cùng bước.
- `soak.json` có `{days,days_completed,crashes,results,duration_s}`. Mỗi phần tử `results[] = {day,earned,reputation,score}` theo Ngày tăng dần, tại thời điểm Shop đóng. `duration_s` là thời gian thực và loại khỏi phép so tất định. Lượt đạt khi `days_completed == days`, `crashes == 0` và đủ một kết quả/Ngày. Kiểm hai lượt seed 7 có cùng dữ liệu gameplay. Nếu lỗi, giữ số Ngày thật sự đã đóng và báo lỗi rõ ràng.

## Hồ sơ và bản đóng gói · Người 4

- README nêu môi trường, mở game từ clone sạch trong tối đa **3 lệnh**, điều khiển, CLI headless, test, benchmark và soak. Kiểm gói zip hoặc tar.gz gồm source đã bàn giao, manifest, browser client và dữ liệu cần chạy. Tạo từ commit bàn giao, giải nén vào thư mục mới rồi chạy theo README. Rà nguồn tài sản trong CREDITS và xác nhận giấy phép đã có hoặc được phép dùng trước khi bổ sung LICENSE.
- Lưu bằng chứng bên dưới `docs/proof/phase-4/`. Dẫn số đo từ đúng code đã bàn giao và ghi commit đo; khi bổ sung proof sau lần chạy, đối chiếu file gameplay/manifest và kiểm lại trên commit cuối nếu có thay đổi. Ghi `CHANGELOG.md` theo từng phase. Release notes nêu điểm mới, cách chạy gói và giới hạn đã biết.
- Chốt một SHA trên `main`, đặt tag `phase-4` và `v1.0.0` cùng SHA, công bố GitHub Release `v1.0.0` và đính kèm file chạy đã thử. Kiểm quyền tạo Release và tag trên fork trước khi sát hạn.
