# Kế hoạch Phase 3 · Mùa Nước Nổi

Trong 35 phút, bàn giao kho cá thể và độ tươi theo Test Contract v1.2, qua cả file lẫn `day`. Tag `phase-3` trỏ tới commit bàn giao trên `main`, đẩy trước **2:30**. Kế hoạch dùng starter Python và tập trung vào lõi cho nhóm 4 người. Điền GitHub handle vào [TEAM.md](../../TEAM.md) để gắn người thật với bốn vai.

## Phân công và tác động lên file

| Người / nhánh | Việc sở hữu | File code | Test sở hữu |
|---|---|---|---|
| **1 · Schema/PO** · `p3/inventory` | Adapter đọc/ghi theo version, schema scenario, hợp đồng và dữ liệu độ tươi dùng chung. Thêm kiểm schema trước khi bật v1.2. | `game.contract.json`, `chonoi/{inventory,contract,scenario,headless,jsonl}.py` | `test_p3_inventory.py` (mới), `test_smoke_p1.py`, `test_p2_scenario.py` |
| **2 · Gather** · `p3/gather-freshness` | Cấp ID khi nhặt, hao tươi đúng bước, `spoiled`, LIFO, `gather_end`. Giữ luật cá và Cá Sấu hiện có. | `chonoi/sim/{gather,gather_resources,gather_monsters}.py` | `test_p3_gather.py` (mới), `test_p1_gather_resources.py`, `test_p2_fish_data.py`, `test_p2_gather_monsters.py` |
| **3 · Quán/QA** · `p3/quan-freshness` | Giữ theo ID, chọn tươi nhất, hao cả phần đã giữ, giữ lại khi ươn, tính giá và boa. Kiểm fixture trên kho thực. | `chonoi/sim/{quan,quan_customers}.py` | `test_p3_quan.py` (mới), `test_p1_quan_customers.py`, `test_p1_quan_service.py`, `test_p2_quan.py` |
| **4 · Day/HUD/Integrator** · `p3/day-hud` | Bàn giao qua Day/Shop, ID liên tục, chọn version khi ghi kho, HUD theo cá thể và kho khả dụng. Review, tích hợp và đẩy tag. | `chonoi/{runner,live}.py`, `chonoi/sim/{day,shop}.py`, `chonoi/web/index.html` | `test_p3_day.py` (mới), `test_p2_day.py`, `test_live.py`, `test_python_starter_units.py` |

Mỗi người sửa file test của mình trong `tests/` và lưu bằng chứng ở `docs/proof/phase-3/nguoi-N/`. Người 3 tổng hợp ma trận. Người 1 giữ `docs/clarify.md` và thu nhật ký AI của cả nhóm vào `docs/ai-usage-log.md`. Người 2 ghi retro về lần đổi schema. Người 4 cập nhật `CHANGELOG.md`, `README.md` và `AGENTS.md` khi bàn giao. Nếu cần sửa ngoài lát, gửi yêu cầu cho chủ file. Review chéo **1 ↔ 4**, **2 ↔ 3**.

## Việc cần sửa trên từng nhánh

### `p3/inventory`

- Chuyển các bộ nạp file và scenario từ kho đếm sang kho cá thể khi chạy v1.2. Thêm kiểm ID trùng, loại lạ, `fresh` sai miền và file kho đếm. Giữ kiểm map đếm cho công thức/kế hoạch.
- Sửa `chonoi/jsonl.py` để giữ độ chính xác của `fresh`, nhất là quanh ngưỡng 30 và trong event bàn giao. Kiểm file kho và `gather_end.inventory` cho cùng giá trị số. Chuẩn bị cấu hình v1.2 để ghép cùng các nhánh đọc/ghi tương thích.

### `p3/gather-freshness`

**Mục tiêu lát 2.** Gather giữ từng nguyên liệu với `id`, `kind`, `fresh` từ lúc vào giỏ đến lúc rơi hoặc bàn giao. Người 2 chịu trách nhiệm AC-P3-02 và cung cấp đầu ra Gather cho AC-P3-05/06. Checkout gốc `dbbc504` đang chạy manifest v1.1. Phạm vi sprint này là lõi của nhóm 4 người, theo phân công ở trên.

| Mốc trong Phase 3 | Việc của người 2 | Kết quả trước khi qua mốc |
|---|---|---|
| 0–7 | Đối chiếu API kho với người 1 và cách dùng allocator chung với người 4. Chốt fixture có ID ngoài thứ tự và đầu vào sát ngưỡng 30. | Có dữ liệu mẫu và thống nhất đầu vào/đầu ra cho cả hai bên bàn giao. |
| 7–13 | Đổi biểu diễn giỏ v1.2, đăng ký ID fixture, thêm cá thể khi hái/bắt và xuất snapshot/kho. | Test đủ chỗ và thiếu chỗ, thứ tự nhặt và thứ tự ID đều qua trên bản ghép adapter. |
| 13–20 | Nối hao tươi, `spoiled`, rơi LIFO và snapshot ngất. Chạy test Gather tập trung. | Có log ca qua ngưỡng và ca ngất đủ để gửi review chéo người 3. |
| 20–25 | Pair với Integrator chạy smoke qua file và `day` trên bản ghép v1.2. Sửa lỗi Gather và chuyển lỗi giao diện cho chủ file. | Đã đối chiếu file, event và snapshot Quán. |
| 25–32 | Chạy hồi quy, ghi lý do đổi test, lưu bằng chứng và ghi retro khi có kết quả. | Người 3 có log và SHA để cập nhật ma trận. Người 4 có commit đã review để tích hợp. |

#### Trình tự sửa mã

1. **`chonoi/sim/gather.py` · dựng giỏ.** Chọn biểu diễn theo `tuning.freshness` như giao diện tích hợp. Nhánh có freshness nhận mảng đã qua kiểm schema của lát 1, sao chép từng cá thể để một lượt mô phỏng không làm hao fixture gốc, rồi `ids.reserve` các ID fixture trên allocator được truyền vào. Giữ nguyên thứ tự mảng. Nhánh v1.1 tiếp tục nhận mảng tên nguyên liệu và dùng `hold_to_items` trong thời gian chuyển đổi.
2. **`_try_add_to_hold(kind, amount)` · hái và bắt.** Dùng điểm vào hiện có của `gather_resources.py`. Kiểm đủ chỗ cho toàn lượt trước khi gọi `new_item` của lát 1, cấp một ID cho mỗi cá thể theo thứ tự nhập và lấy độ tươi ban đầu từ tuning. Mọi cá thể đều chiếm ô, kể cả hàng ươn. Khi thiếu chỗ, giữ sự kiện `hold_full` và trạng thái nút/cá/cooldown hiện hành, đồng thời giữ nguyên dãy ID. Giữ payload `gather` và `fish_caught` hiện có. Chỉ chỉnh file tài nguyên nếu cần để giữ giao diện này.
3. **`GatherSim.step` · hao trước hành động.** Gọi `decay_items` ngay sau `tick_resources`, truyền tốc độ và ngưỡng từ `tuning.freshness`, `tick_hz` và `location="hold"`. Dùng helper chung cho tính chính xác, kẹp đáy và thứ tự phát `spoiled`. Hàng có từ đầu bước hao một lần, hàng nhặt trong bước giữ nguyên độ tươi khởi tạo đến bước sau. `Session` đã bỏ qua bước mô phỏng khi pause, nên hao tươi tự dừng ở điểm này. Giữ thứ tự bơi → oxy/ngạt → hit → kiểm bến rồi hái → bắt → xét hết giờ → cá bơi/sinh khi ca còn chạy.
4. **`gather.py` và `gather_monsters.py` · rơi đồ.** Tái dùng thao tác lấy từ cuối giỏ ở hit và xả phần còn lại ở ngất. Đưa cá thể đã hao tươi trong bước vào `lost` bằng `item_rows`, theo đúng thứ tự lấy ra. Nếu hit làm HP về 0, `monster_hit` chứa phần rơi do hit, `faint` chứa phần giỏ còn lại, rồi `gather_end(fainted)` có `{"items":[]}`. Ngất do ngạt bỏ toàn bộ giỏ trước khi xét thủy quái.
5. **Snapshot và bàn giao.** `snapshot()["hold"]` dùng bản sao theo thứ tự nhặt. `inventory_items()` dùng bản sao sắp bằng `sort_by_id` ở v1.2. `gather_end`, writer và `DaySim` lấy từ cùng giao diện; sắp đầu ra không làm đổi thứ tự giỏ. Người 1 sở hữu helper kho, kiểm scenario và độ chính xác JSONL. Người 4 sở hữu truyền version vào writer, bàn giao cùng tick và cấp ID mới cho fixture Ngày sau trên cùng allocator. Trao đổi với chủ file nếu smoke phát hiện lệch ở các điểm đó.

#### Ca kiểm và lý do đổi test

| File / ca | Kỳ vọng |
|---|---|
| `test_p3_gather.py` · ID và sức chứa | Fixture `I10, I2` giữ thứ tự giỏ; kho xuất `I2, I10`. Hái đủ chỗ nhận `I11` ở độ tươi khởi tạo. Bắt đàn nhiều sản lượng cấp một ID cho từng cá thể. Ca thiếu chỗ phát `hold_full`, giữ nút/cá và không bỏ số thứ tự ID. |
| `test_p3_gather.py` · hao và ngưỡng | Với thứ tự giỏ `I10, I2` cùng `fresh:30`, tick 1 phát `spoiled` theo `I2, I10` đúng một lần. Fixture dưới 30 không phát lại, giá trị chạm đáy dừng ở 0. Sau tick đầu, cặp `30.0084` và `30.0083` còn ở hai phía ngưỡng; kiểm cả event và JSONL sau đọc lại. Hàng mới đạt 100 trong bước nhặt và chỉ giảm từ bước sau. Pause giữ nguyên giỏ, bước resume hao đúng một bước. |
| `test_p3_gather.py` · ưu tiên trong bước | Ca hit rồi ngất có tổng `lost` đúng thứ tự nhặt ngược dù ID không tăng theo thứ tự giỏ. `spoiled` đi trước hit/ngạt/cập bến nếu trùng bước. Cập bến ở bước cuối ưu tiên hơn bắt/hết giờ; ngoài bến vẫn nhận hàng bắt/hái hợp lệ ở bước cuối. |
| `test_p1_gather_resources.py` | Giữ assert chọn nút/đàn, bán kính, hồi nút, cooldown và đầy giỏ. Dùng `GatherSim` thật ở ca kiểm giỏ cá thể để fixture override không che lỗi cấp ID. |
| `test_p2_fish_data.py` | Giữ assert seed, phản xạ biên, lượt rẽ, giới hạn sinh cá và kế hoạch Ngày. Đổi assert manifest `1.1` khi cấu hình bàn giao bật v1.2. Đổi fixture và giá trị kho kỳ vọng ở smoke cá kèo và kèo nèo theo schema mới. |
| `test_p2_gather_monsters.py` | Giữ assert chọn quái, patrol/chase/recoil, bất tử và thứ tự ngạt/hit/ngất. Đổi fixture giỏ và assert `lost`/kho sang cá thể ở ca v1.2. Test nào mock `load_contract` cần khai version rõ theo đường đang kiểm. Giữ so từng byte qua hai lượt cùng seed. |

Dùng fixture tuning v1.2 với adapter cho test trực tiếp trước khi manifest được bật. Giữ ca v1.1 dùng fixture chuỗi trong thời gian chuyển tiếp. Với `fresh`, dùng dung sai hợp đồng khi so giá trị quan sát; kiểm chính xác ID, tick, thứ tự sự kiện, phía ngưỡng và dữ liệu giống nhau giữa file, event và snapshot bàn giao.

```bash
PYTHONPATH=tests:. python3 -m unittest test_p3_gather test_p1_gather_resources test_p2_fish_data test_p2_gather_monsters -v
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
```

Chạy [smoke qua file và Day](phase-3-integration.md#smoke-sau-khi-ghép-bản-v12) trên bản tích hợp. Kiểm thêm ngất ghi kho rỗng, tick limit trước `gather_end` giữ nguyên file đích có sẵn và không tạo file mới nếu đích chưa có. Ca qua file cần cùng ID, loại và fresh giữa `gather_end`, file và Quán tick 0. Ca Day cần cùng giá trị ở tick chuyển pha và chỉ hao theo tốc độ Quán từ bước kế.

Baseline tại `dbbc504` chạy đạt 19 test Gather liên quan. Bộ đầy đủ chạy 88 test, với 3 lỗi `PermissionError` khi mở socket Live Server trong sandbox. Lưu lệnh, SHA, kết quả chạy thực tế và trích JSONL đuôi `.txt` tại `docs/proof/phase-3/nguoi-2/` sau khi triển khai. Ghi rõ test đổi vì schema hay luật mới trong commit hoặc bằng chứng. Người 3 review chéo và cập nhật ma trận, người 2 ghi nhận bài học đổi schema vào `docs/retro.md`.

### `p3/quan-freshness`

- Đổi kho và phần giữ chỗ sang cá thể/ID. Hao kho thô trước tương tác, phát hết `spoiled` rồi xử lý từng đơn bị ảnh hưởng. Kiểm giữ lại thành công/thất bại, ID trùng giữa đơn và phần giữ sai công thức.
- Tiêu đúng ID lúc nấu, xuất cá thể trong `cook_started.items` và dùng giá đã chốt cho boa/thanh toán. Sửa fixture cũ nhưng giữ kiểm thứ tự chọn bếp/bàn, giao món đúng hạn và đóng ca.

### `p3/day-hud`

- Bỏ chuyển kho sang map đếm ở Day/Shop. Giữ ID và độ tươi qua chuyển pha, tạo ID mới cho giỏ mẫu của Ngày sau. Sửa lỗi kế thừa từ v1.1 ở `runner.py` và `day.py`: `phase_start` mang pha/Ngày mới; snapshot pha mới có `phase_tick:0` kể cả ngoài nhịp lấy mẫu. Kiểm lại với nhịp snapshot mặc định.
- Đổi HUD và fixture demo sang kho cá thể, kể cả màn nhập kho và Shop. Sửa phần kế thừa ở `live.py` để lệnh `--mode day --days 1` khởi chạy, nối input Shop/pause và luồng màn hình Day với client. Ghi bằng chứng trực tiếp trên máy mở được socket; ghi riêng các màn chỉ kiểm bằng demo.
- Kiểm tag các phase trước trên fork và ghi breaking change trong `CHANGELOG.md` khi bàn giao. Chạy smoke hai tiến trình và `day` trên commit tích hợp rồi mới đẩy tag Phase 3.

## Tích hợp theo thứ tự

1. **Phút 0–7.** Chọn commit gốc chung và xác nhận tag các phase trước trên fork. Commit `PHASE3.md` cùng tài liệu phân công vào nhánh tích hợp để cả nhóm có cùng bản ticket. Thông báo cả nhóm về thay đổi kho, manifest và các file starter cần sửa. Mỗi người mở clone/worktree riêng và dùng đúng nhánh trong bảng. Đọc [giao diện v1.2](phase-3-integration.md) trước khi giao việc cho agent.
2. **Phút 7–20.** Người 1 gửi commit adapter/kiểm schema trước, vẫn chạy được với manifest v1.1. Trong lúc đó, người 2 và 3 dựng test từ mảng cá thể mẫu; người 4 làm Day/Shop bằng fixture ca ngắn và làm HUD bằng `?demo=gather`, `?demo=quan` và `?demo=shop`. Ghép các consumer trên nhánh tích hợp, bật v1.2 tại đó khi đã nối đủ các điểm đọc/ghi. Chạy smoke qua file vào phút 20 và lưu log.
3. **Phút 20–32.** Standup 2–3 phút, xử lý lỗi nối kho trước. Chạy smoke qua file và `day`, hồi quy P1–P2 và kiểm HUD. Đưa cấu hình v1.2 lên `main` cùng các consumer tương thích để không có commit bàn giao chỉ đổi manifest. Ghi breaking change, cách đổi fixture và lý do đổi test. Điền [ma trận kiểm chứng](../verification/phase-3.md), ghi commit có bằng chứng và gắn tag.
4. **Phút 32–35.** Đẩy tag trước 2:30. Ghi trung thực các AC chưa đạt. Chạy thử HUD trên máy mở được socket; nếu backend Day live vẫn thiếu, ghi bằng chứng demo HUD và trạng thái kiểm chứng luồng live riêng.
