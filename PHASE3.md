# TICKET-03 — Change Request “Mùa Nước Nổi” (Phase 3)

**35 phút (1:55–2:30) · Test Contract v1.2 · Hạn đẩy tag `phase-3` 2:30.**

Tháng Tám âm lịch, nước lũ về, cá linh nhiều. Trời nóng làm nguyên liệu mau ươn. Khách hàng muốn biết độ tươi của từng nguyên liệu, từ lúc Út Sen lấy được đến khi đưa vào bếp. **`[THAY THẾ]`** đánh dấu các luật đổi so với bản đang chạy.

---

## 1. Lõi (mọi nhóm) — Độ tươi

### `[THAY THẾ]` Kho đếm theo loại → kho cá thể

```json
{
  "items": [
    { "id": "I1", "kind": "ca_linh", "fresh": 100 },
    { "id": "I2", "kind": "ca_loc", "fresh": 97.5 }
  ]
}
```

- File có đúng khóa gốc `items`, giá trị là mảng cá thể `{id,kind,fresh}`. Kho rỗng là `{"items":[]}`. `id` là chuỗi duy nhất, khác rỗng, `kind` thuộc danh mục nguyên liệu, `fresh` hữu hạn trong `[0,100]`. Cấp `I1,I2,…` theo thứ tự vào giỏ, tiếp tục tăng xuyên pha và Ngày, kể cả khi cá thể trước đó đã dùng hoặc bỏ. LIFO khi mất hàng vẫn theo thứ tự vào giỏ.
- Bên đọc chọn schema theo `contract_version`. Contract v1.2 trả mã `2` cho file kho đếm hoặc sai schema, `kind` lạ, `id` trùng, `fresh` ngoài miền. Kho quán nhận nguyên số lượng, `id` và độ tươi, kể cả hàng ươn. Sức chứa giỏ chỉ áp lên giỏ.
- `gather --inventory-out` ghi đúng một lần khi có `gather_end`. Dùng file tạm cùng thư mục rồi thay thế nguyên tử. Ngất ghi kho rỗng. Nếu chạm giới hạn `--ticks` trước `gather_end`, giữ nguyên đường dẫn đích. Xuất file theo `id`, đủ độ chính xác khi đọc lại để giữ giá trị và nhánh ở ngưỡng `30`. `gather_end.data.inventory` theo cùng schema.
- Trong `day`, bàn giao trong cùng tick chuyển pha, hàng không hao thêm, ca quán chạy từ bước sau. Nếu có Chợ Chú Sáu, hàng mua nhập riêng vào kho quán Ngày kế với `fresh:100`, tách khỏi `gather_end.inventory` và dùng `id` mới. Hàng thô ở Shop hoặc chờ nhập không hao tươi. Khi người chơi bán, lấy cá thể chưa ươn tươi nhất của loại, hòa theo `id`.

### Độ tươi, giữ chỗ và giá

| Quy tắc                                         | Cách xử lý                                                                                                                                                                                                                                                                                         |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Hàng mới**                                    | `fresh = 100` lúc bắt/hái, bắt đầu hao từ bước sau.                                                                                                                                                                                                                                                |
| **Hao tươi**                                    | Giỏ giảm `0.5/s`, kho quán giảm `0.25/s` kể cả hàng đang giữ chỗ. Mỗi giây `60` tick, kẹp đáy `0`. Pause dừng hao tươi. Món chín không hao.                                                                                                                                                        |
| **Ươn**                                         | `fresh < 30`, vẫn chiếm ô, không dùng nấu. Phát `spoiled` đúng một lần khi đi từ `≥ 30` xuống `< 30`. Nếu nhiều cá thể cùng vượt ngưỡng, phát theo `id`. So ngưỡng trước làm tròn.                                                                                                                 |
| **`[THAY THẾ]` Giữ theo lượng → giữ theo `id**` | Mỗi loại trong công thức lấy các cá thể khả dụng tươi nhất, hòa theo `id`. Nếu phần giữ có cá thể vừa ươn, nhả toàn bộ phần giữ của đơn và thử giữ lại đúng một lần. Xử lý các đơn bị ảnh hưởng theo `order_tick` rồi `id` bàn. Không đủ thì đơn thường chuyển `unfulfillable`, khách chờ tới hạn. |
| **`[THAY THẾ]` Giá niêm yết → giá theo tươi**   | Khi bắt đầu nấu, tiêu đúng các `id` đang giữ và chốt `base_price = floor(giá niêm yết × trung bình fresh của các cá thể dùng / 100)`. Nếu đủ điều kiện boa, áp `floor(tiền món × 0.2)` trên giá đã chốt. Điểm vẫn là `earned + 100 × floor(reputation)`.                                           |
| **HUD**                                         | Cho người chơi đọc được độ tươi hoặc nhận ra hàng ươn bằng số, thanh, nhãn hoặc biểu tượng.                                                                                                                                                                                                        |

Dùng phép tính đủ chính xác ở ngưỡng `30` và phép `floor`. Ví dụ có thể dùng `240` đơn vị mỗi điểm tươi với các fixture biểu diễn chính xác, trừ `2` đơn vị/tick ở `gather` và `1` đơn vị/tick ở `quan`.

### Thứ tự trong tick

- **Gather.** Đồng hồ, cooldown, hồi nút và độ tươi của hàng có sẵn ở đầu bước → lịch dòng lũ nếu bật → bơi, oxy và ngạt → Lao nếu có, rồi thủy quái/hit → bến trước hái → bắt cá rồi ảnh nếu có → xét hết giờ, nếu còn giờ mới cập nhật cá và sinh thêm. Rơi hàng theo LIFO. Khi ngất, bỏ toàn bộ phần còn lại theo LIFO rồi phát `faint`, `gather_end(fainted)`.
- **Quán.** Đồng hồ và timer → hao tươi kho thô, phát hết `spoiled` theo `id` rồi mới xử lý giữ chỗ bị ươn → xét món chín/cháy nếu có theo `id` bếp → di chuyển và tối đa một tương tác → thanh toán, kiên nhẫn/đóng ca → nếu còn giờ, xử lý đặt trước nếu có rồi tới khách thường. Giao đúng tick kiên nhẫn chạm `0` vẫn hợp lệ. Giao đúng tick kết thúc ca được trả ngay.

### Contract v1.2

- **`[THAY THẾ]`** Đặt `contract_version:"1.2"`. Thêm `freshness` `{initial,gather_decay_per_s,quan_decay_per_s,spoiled_below}` với các giá trị lần lượt `100`, `0.5`, `0.25` và `30`.
- **Scenario.** `gather.hold` và `quan.stock` là mảng cá thể. Trong `day`, Ngày đầu giữ nguyên `id` trong mẫu `gather.hold`, các Ngày kế cấp `id` mới theo thứ tự mảng với `kind`/`fresh` ban đầu. `customers[].reserved` là mảng `id` cá thể. `id` vật lý duy nhất giữa các nơi chứa. Phần giữ phải trỏ tới cá thể chưa ươn trong kho, đủ công thức và không dùng chung với đơn khác. Bỏ `reserved` cho đơn `reserved` thì cấp theo `order_tick` rồi `id` bàn, lấy tươi nhất rồi `id` nhỏ. Sai hoặc mâu thuẫn → mã `2`. Payload món giữ cấu trúc, `base_price` là giá đã chốt theo `fresh`.
- **JSONL.** Snapshot `hold`, `stock` (quán và Shop) và `customers[].reserved` theo schema trên. `cook_started.data.items` là mảng cá thể sắp theo `kind` rồi `id`. `lost` trong `monster_hit`/`faint` là mảng cá thể theo thứ tự bỏ LIFO. Event mới `spoiled` có `item_id`,`kind`,`location` (`hold`/`stock`). Dung sai quan sát độ tươi `±0.01`. Dùng trạng thái/event để kiểm nhánh ở ngưỡng. Tick của event biên phải chính xác.

Dùng scenario sau để kiểm ngưỡng khi chạy `gather` một bước không input. Cá thể bắt đầu đúng `fresh 30` nên ươn ở bước đầu:

```json
{
  "gather": {
    "hold": [{ "id": "I1", "kind": "ca_linh", "fresh": 30 }],
    "random_fish": false,
    "monsters": []
  }
}
```

```json
{
  "type": "event",
  "tick": 1,
  "phase": "gather",
  "name": "spoiled",
  "data": { "item_id": "I1", "kind": "ca_linh", "location": "hold" }
}
```

Để smoke bàn giao file, dùng cùng mẫu trên với `fresh:100` và `interact:true` ở frame `0` để cập bến. Mở `quan --inventory` với file vừa ghi và `--ticks 0`. So chính xác `id`, `kind` và độ tươi của snapshot quán với file sau lần hao ở bước `gather`.

---

## 2. Mở rộng

Kỳ vọng tính cả buổi lab. Nhóm 4 người không bắt buộc, nhóm 5 hoàn thành ít nhất 1 mục, nhóm 6 ít nhất 2 mục. Chọn sau khi độ tươi và bàn giao kho đã chạy ổn. Nếu làm, khai mã trong `extensions` và ghi test/bằng chứng trong `README`.

**Tự do sáng tạo.** Khi lõi đã đúng, nhóm có thể thêm ý tưởng riêng, như khu vực hoặc sự kiện. Tắt phần tự thêm ở headless hoặc giữ nguyên kết quả theo Test Contract. Ghi vào mục **“Sáng tạo của nhóm”** trong `README.md`, kèm bằng chứng ngắn cho thấy lõi vẫn đúng.

### Dòng nước lũ (`current`)

| Quy tắc          | Cách xử lý                                                                                                                                                                                                                                                     |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Lịch**         | Với `t = 1800·k` (`k ≥ 1`), báo trước ở `t−120` bằng chữ, biểu tượng và âm thanh. Bắt đầu trước di chuyển ở `t` và kéo dài `480` tick (`8 s`), từ `t` đến `t+479`.                                                                                             |
| **Hướng và lực** | Chọn đều `+x` hoặc `−x` theo seed khi bắt đầu. Cộng `1.5 m/s` vào người chơi nếu `d` đầu bước `≥ 10`, rồi chặn mép. Đàn cá và thủy quái giữ chuyển động riêng, lực dòng không tích lũy vào `player.vel`.                                                       |
| **Kết thúc**     | Phát `current_end(elapsed)` trước di chuyển ở `t+480`. Nếu ca kết thúc trước, phát `current_end(phase_end)` trước `faint` nếu có và trước `gather_end`. Bước bắt đầu dòng trùng bước cuối ca vẫn có lực. Giới hạn CLI chỉ cắt mô phỏng tại trạng thái hiện có. |

- Manifest thêm `gather.current` `{interval_ticks,duration_ticks,warning_ticks,min_depth,speed}`. Scenario nhận `gather.random_current:false` để tắt lịch hoặc `current_direction:-1/1` để khóa hướng khi chạy lịch. Snapshot `gather` có `current:null` hoặc `{direction,ticks_left}`, đếm cả tick hoạt động vừa chụp.
- **Event `data`:**
- `current_warning`: `starts_at_phase_tick`.
- `current_start`: `direction`, `duration_ticks`.
- `current_end`: `direction`, `reason` (`elapsed`/`phase_end`).

### Khách đặt trước (`reservations`)

- Mỗi Ngày công bố 2 đơn `R1,R2` sau `phase_start(gather)` theo `id`. HUD sáng hiện hai đơn. Chọn hai bàn khác nhau, món trong kế hoạch, tick đến theo seed trong `[1800,10799]`, có thể cùng tick. Quán độc lập công bố lúc dựng pha và dùng menu đầy đủ.
- Trạng thái `scheduled → holding → waiting → served` hoặc `failed`. Giữ bàn từ `max(0, arrival_tick − 1800)`. Nếu giữ từ tick `0`, thể hiện ngay trong snapshot dựng quán. Khách thường đang ngồi có thể ở lại, khách mới không ngồi bàn giữ. Khi còn giờ, cập nhật giữ bàn và xử lý khách đặt theo `id` trước lượt khách thường.
- Đến giờ mà bàn còn khách thì fail `occupied`. Bàn trống nhưng thiếu kho thì fail `stock`. Đến thành công giữ nguyên liệu ngay, phát `reservation_arrived` rồi `customer_arrived`. Kiên nhẫn `60 s`. Giá cuối `floor(giá đã chốt theo fresh × 1.5)`, rồi mới tính boa. Giao thành công phát `served` rồi `reservation_served`.
- Lỡ đơn do `stock`, `occupied`, `burnt`, `patience` hoặc `closing` thì nhả hàng/bàn, hủy món, uy tín `−1` đúng một lần. `reservation_failed` thay nhánh rời do thất bại, không cộng phạt khách thường. Nếu phần giữ vừa ươn và giữ lại không đủ thì fail `stock`. Nếu món cháy, phát `dish_burnt` với `order_status:"failed"` trước `reservation_failed`. Khi đóng ca, fail các đơn chưa phục vụ/chưa fail theo `id` đặt. `served` và `failed` là trạng thái cuối.
- Manifest thêm `reservations` `{count,table_hold_s,price_multiplier,failed_reputation_delta}` lần lượt `2`, `30`, `1.5`, `−1`. Scenario nhận `quan.reservations[]` `{id,table_id,dish_id,arrival_tick}`. Mảng tường minh thay toàn bộ danh sách, tối đa hai đơn, bàn khác nhau, tick đến nguyên dương nhỏ hơn thời lượng ca chuẩn, có thể sau giờ đóng nếu fixture rút ngắn ca. `quan.random_reservations:false` tắt tự sinh. Snapshot `gather` trong `day` và `quan` có `reservations[]` kèm `state`. Snapshot `quan` thêm `customers[].reservation_id` và `tables[].reservation_id`, dùng `null` khi không có.
- **Event `data`:**
- `reservation_announced`: `reservation_id`, `table_id`, `dish_id`, `arrival_tick`.
- `reservation_arrived`: `reservation_id`, `order_id`.
- `reservation_served`: `reservation_id`, `order_id`, `base_price` đã nhân hệ số và làm tròn xuống.
- `reservation_failed`: `reservation_id`, `reason`, `reputation`.

---

## 3. Quy trình nhóm

Nhóm tự chọn cách phối hợp và cùng commit vào fork chung bằng tài khoản GitHub của từng người. Ghi `Co-authored-by:` khi cùng làm một commit.

1. Gợi ý dùng 7 phút đầu để lên lại kế hoạch và chia lát. Phân tích tác động lên module, file và test. Ghi quyết định đổi schema kho, cách chuyển và thứ tự tích hợp để `main` vẫn chạy được. Có thể ghi trong `README.md`, `docs/clarify.md`, ADR hoặc nơi khác trong repo chung. Dưới đây là mẫu ghi tác động:

| Module                                 | File cần đổi     | Test bị ảnh hưởng           | Người phụ trách |
| -------------------------------------- | ---------------- | --------------------------- | --------------- |
| Adapter, Lặn, Quán, `day`, HUD hoặc QA | Ghi file thực tế | Ghi test giữ, đổi hoặc thêm | Ghi người nhận  |

2. Gợi ý tích hợp schema/adapter và test migration trước. Làm Lặn, Quán và HUD song song theo schema đã chốt. Có thể hỗ trợ hai phiên bản nội bộ trong lúc chuyển và bật v1.2 khi cả hai đầu bàn giao đã sẵn sàng. Khi chạy v1.2, file kho đếm trả mã `2`.
3. Gợi ý chạy smoke bàn giao kho trên bản tích hợp ở phút `20`, có thể `pair`. Standup 2–3 phút để điều người đã xong sang lát đang trễ. Nếu có retro nhanh, ghi điều rút ra từ lần đổi kho trong `docs/retro.md`.
4. Ghi breaking change, schema mới và cách cập nhật fixture vào `CHANGELOG.md`. Trên `main`, kiểm cả file và `day`, rồi chạy lại regression P1–P2 còn hiệu lực. Ghi lý do nếu test cũ bị thay bởi luật mới. Lưu bằng chứng trong `docs/proof/phase-3/` và ghi `AC-P3-xx → bằng chứng → kết quả` trong `docs/verification/phase-3.md`. Cập nhật `docs/clarify.md` và `docs/ai-usage-log.md`.

### Lịch gợi ý

| Phút trong phase | Việc                                                                                                                                |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **0–7**          | Phân tích tác động, ghi quyết định đổi schema, chốt thứ tự tích hợp và chia lại việc.                                               |
| **7–25**         | Viết schema/adapter, Lặn, Quán và HUD song song. Tích hợp theo thứ tự đã chốt. Phút `20` chạy smoke kho, standup và hỗ trợ lát trễ. |
| **25–32**        | Bật v1.2 trên bản tích hợp, smoke hai tiến trình và `day`, chạy regression, chốt `CHANGELOG`, bằng chứng và tag. Retro nhanh.       |
| **32–35**        | Dự phòng. Đẩy tag `phase-3` chậm nhất `2:30`.                                                                                       |

---

## Định nghĩa hoàn thành (DoD)

- [ ] Contract v1.2 bàn giao kho cá thể qua file và trong `day`. Kho đếm trả mã `2`. `id`, độ tươi, hàng ươn, giữ chỗ, giá và JSONL đúng luật.
- [ ] HUD cho thấy độ tươi hoặc hàng ươn. Có test qua ngưỡng, thử giữ lại khi hàng vừa ươn, chốt giá và bàn giao.
- [ ] Có ghi tác động, quyết định đổi schema và thứ tự tích hợp giữ `main` chạy được. Các lát đã tích hợp trong fork chung, có bằng chứng đóng góp của từng người.
- [ ] `CHANGELOG.md` ghi breaking change, regression còn hiệu lực đạt, test thay đổi có lý do. `docs/verification/phase-3.md` và bằng chứng khớp commit gắn tag. Ghi chép làm rõ và nhật ký AI đã cập nhật.
- [ ] Nếu làm mở rộng, có test và bằng chứng cho từng mục.
- [ ] Đẩy `phase-3` trỏ tới commit bàn giao trên `main` chậm nhất `2:30`.
