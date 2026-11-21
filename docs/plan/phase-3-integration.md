# Giao diện tích hợp Phase 3 · Test Contract v1.2

[Ticket 03](../../PHASE3.md) thay kho đếm, giữ chỗ theo lượng và giá niêm yết. Các luật còn hiệu lực của [Phase 1](../../PHASE1.md) và [Phase 2](../../PHASE2.md) tiếp tục áp dụng, gồm 6 nguyên liệu, menu/kế hoạch, thứ tự phục vụ, pause và nâng cấp. Mô tả mùa nước nổi không bổ sung giá trị tuning cho cá. Nhóm 4 người chọn làm lõi, giữ phần mở rộng đã có nếu bản tích hợp bật chúng.

## Schema và phiên bản

```json
{"items":[{"id":"I1","kind":"ca_linh","fresh":100},{"id":"I2","kind":"ca_loc","fresh":97.5}]}
```

| Nơi dùng | Dữ liệu | Quy ước |
|---|---|---|
| File kho và `gather_end.data.inventory` | `{"items":[{id,kind,fresh},...]}` | Mảng theo `sort_by_id`, kho rỗng là `{"items":[]}`. Cùng bộ giá trị `id/kind/fresh` ở hai đầu ra. |
| `gather.hold`, snapshot `hold` | Mảng cá thể | Giữ thứ tự vào giỏ để bỏ LIFO, cuối mảng lấy ra trước. Sức chứa chỉ áp lên giỏ. |
| `quan.stock`, snapshot `stock` của Quán/Shop | Mảng cá thể | Snapshot sắp theo ID; kho gồm cả cá thể ươn và cá thể đã giữ chỗ. |
| `customers[].reserved` | Mảng ID, ví dụ `["I1","I8"]` | So công thức bằng `kind` của cá thể được trỏ tới. Mỗi ID chỉ giữ cho một đơn. |
| Sự kiện | `spoiled: {item_id,kind,location}`, `cook_started.items`, `monster_hit.lost`, `faint.lost` | `location` là `hold` hoặc `stock`. `items` của bếp chứa cá thể theo `kind` rồi ID. `lost` chứa cá thể theo LIFO. |

Manifest đặt `contract_version:"1.2"` và thêm `tuning.freshness = {initial:100,gather_decay_per_s:0.5,quan_decay_per_s:0.25,spoiled_below:30}`. Người 1 xử lý version ở điểm đọc: v1.1 giữ schema đếm, v1.2 chỉ nhận mảng cá thể. Mỗi cá thể có đúng ba khóa, ID là chuỗi duy nhất khác rỗng, `kind` thuộc danh mục và `fresh` là số hữu hạn trong `[0,100]`. File đếm, bool làm số, ID trùng và schema sai trả mã 2. Giữ mẫu kho v1.0/v1.1 để làm fixture kiểm từ chối v1.2; dùng ví dụ trên cho schema mới. Khi đổi fixture cũ, mỗi khóa đếm hoặc tên trong giỏ trở thành từng cá thể với ID riêng và `fresh` thích hợp cho mục tiêu test.

Thống nhất chữ ký `load_scenario(path, mode, tuning, *, contract_version="1.1")`, `Session(..., *, contract_version="1.1")` và `run(..., *, contract_version="1.1")` sau các tham số hiện có. Headless/live lấy version từ manifest và truyền rõ tại các điểm gọi. Với sim con, phân nhánh chuyển tiếp bằng `tuning.freshness` do loader v1.2 kiểm bắt buộc và v1.1 không khai.

### API nội bộ cho bốn agent

| Chủ | Giao diện thống nhất |
|---|---|
| **1 · Adapter** | Giữ `read_inventory(path, kinds=KINDS, *, contract_version="1.1")`, `write_inventory(path, items, *, contract_version="1.1")`. Trong `inventory.py` cung cấp `validate_item_list(rows, kinds=KINDS)`, `new_item(ids, kind, initial)`, `decay_items(items, decay_per_s, tick_hz, spoiled_below, location, events) -> set[str]` trả ID vừa qua ngưỡng, `item_rows(items)` trả mảng bản sao chỉ chứa dữ liệu JSON theo thứ tự truyền vào, và `fresh_price(list_price, items) -> int`. Giữ hàm kiểm map đếm cho công thức/kế hoạch. Loader scenario kiểm shape v1.2, giữ dấu hiệu thiếu `reserved`; Quán kiểm ý nghĩa trên kho thực. |
| **2 · Gather** | Giữ `GatherSim.inventory_items()` và `_try_add_to_hold(kind, amount)`. Ở v1.2, `inventory_items()` trả mảng cá thể chuẩn, sắp ID và sao chép; chỉ cấp ID sau khi kiểm đủ chỗ cho cả lượt lấy. Gọi hao tươi ở đầu `step` sau đồng hồ/hồi nút. Snapshot giữ thứ tự nhặt. Dùng cùng biểu diễn sự kiện cho `lost` và `gather_end`. |
| **3 · Quán** | Giữ `QuanSim(..., inventory=None, *, allowed_dishes=None)` với `inventory` là mảng ở v1.2. `quan_customers` tập trung chọn, kiểm và nhả giữ chỗ. Khi bắt đầu nấu, lấy bản sao cá thể đang giữ, chốt giá, xóa đúng ID khỏi kho và đặt `reserved=[]`. Dùng giá đó cho bếp, tay, phục vụ, boa và thanh toán. |
| **4 · Day/HUD** | Tái dùng `IdAllocator` chung của `DaySim` cho toàn lượt. Ngày 1 giữ ID fixture; các Ngày sau sao mẫu với ID mới theo thứ tự mảng và cùng `kind/fresh` ban đầu. Đăng ký ID fixture trước khi cấp ID mới. Khi đổi pha, truyền danh sách cá thể theo giá trị, giữ ID và độ tươi nguyên trạng, đừng ép sang `dict` đếm trong Day hoặc Shop. Truyền version từ manifest tới read/write ở cả headless và live. |

## Trình tự và độ chính xác

- **Hao tươi** dùng nguồn số từ tuning, tính trên giá trị chưa làm tròn. Phương án nội bộ là phân số chính xác cho `fresh` gốc và hao từng tick; cách khác dùng số nguyên đã scale nếu giữ được phần lẻ của fixture. Tránh làm tròn mỗi tick. Chỉ chuyển thành số JSON ở lớp xuất. Writer JSONL hiện làm tròn mọi float tới 3 chữ số, nên cần giữ đủ độ chính xác cho `fresh` để file kho và event bàn giao khớp và giá trị sát 30 không đổi phía khi đọc lại. Giữ quy tắc làm tròn tọa độ.
- **Gather** chỉ giảm độ tươi của hàng đã có ở đầu bước. Hàng mới vào với 100 và bắt đầu hao từ bước sau. Phát `spoiled` đúng một lần khi từ `≥ 30` xuống `< 30`, theo thứ tự ID ngay cả khi hàng bị bỏ hoặc cập bến cùng tick. Cá thể đã ươn từ fixture vẫn giữ trong kho/giỏ. Khi ngất, kho xuất rỗng. Khi CLI dừng do tick limit trước `gather_end`, giữ nguyên file đích. Xuất nguyên tử bằng file tạm cùng thư mục.
- **Quán** giảm tươi cả hàng đang giữ sau timer, phát hết `spoiled` theo ID rồi xét từng đơn bị ảnh hưởng theo `order_tick` và ID bàn. Với mỗi đơn, nhả cả phần giữ rồi giữ lại đúng một lần từ hàng tươi nhất theo loại, hòa theo ID. Nếu thiếu, để `reserved=[]`, chuyển `unfulfillable` và tiếp tục chờ theo timer. Khi dựng fixture, kiểm các ID giữ tường minh và cấp phần thiếu theo thứ tự đơn từ hàng chưa bị giữ. Với ca `day`, kiểm trên kho thật tại bước mở Quán. Khi nấu, tính `floor(giá niêm yết × tổng fresh / (100 × số cá thể))` chính xác trước khi định dạng. Món đang nấu/chín, Shop và pause không hao thêm. Giao đúng tick hết kiên nhẫn hoặc hết ca vẫn được xử lý theo ticket.
- **Day và HUD.** Quán dựng ở cùng tick với `gather_end`, snapshot `phase_tick:0` có đúng hàng bàn giao và Quán bắt đầu hao từ bước kế. Shop nhận kho dư ở cùng tick đóng ca và giữ nguyên độ tươi. HUD hiện tươi hoặc nhãn ươn trong giỏ và kho. Tính số khả dụng từ cá thể chưa ươn và ID chưa giữ; vẫn hiển thị hàng ươn trong tồn. Demo cần cả giá trị ngay tại 30 và dưới 30. Giữ tiền, điểm, nâng cấp và cách đếm ngày của v1.1.

## Smoke sau khi ghép bản v1.2

```bash
p3_tmp=$(mktemp -d)
printf '%s\n' '{"gather":{"hold":[{"id":"I1","kind":"ca_linh","fresh":100}],"random_fish":false,"monsters":[]}}' > "$p3_tmp/gather.json"
printf '%s\n' '{"frames":[{"tick":0,"interact":true}]}' > "$p3_tmp/inputs.json"
python3 -m chonoi.headless --mode gather --seed 42 --scenario "$p3_tmp/gather.json" --inputs "$p3_tmp/inputs.json" --ticks 1 --out "$p3_tmp/gather.jsonl" --inventory-out "$p3_tmp/catch.json"
python3 -m chonoi.headless --mode quan --seed 42 --inventory "$p3_tmp/catch.json" --ticks 0 --out "$p3_tmp/quan.jsonl"
python3 -m chonoi.headless --mode day --days 1 --seed 42 --scenario "$p3_tmp/gather.json" --inputs "$p3_tmp/inputs.json" --ticks 2 --snapshot-every 1 --out "$p3_tmp/day.jsonl"
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
```

So cùng ID, loại và độ tươi ở file, `gather_end` và Quán tick 0; độ tươi bằng `100 − 0.5/60`. Trong `day`, so snapshot Quán tick pha 0 ở tick ngoài 1, rồi kiểm giảm `0.25/60` tại tick ngoài 2. Chạy thêm với `fresh:30` để thấy `spoiled` ở tick 1, và ca hai Ngày đã rút ngắn để kiểm ID mẫu tăng xuyên Ngày. Lưu lệnh và log/trích xuất ở `docs/proof/phase-3/`; dùng đuôi `.txt` cho trích JSONL cần commit vì repo đang ignore `*.jsonl`.
