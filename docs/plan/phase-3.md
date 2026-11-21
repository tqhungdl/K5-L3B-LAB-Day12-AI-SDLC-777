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

- Thay chuỗi nguyên liệu trong giỏ bằng cá thể. Cấp ID sau khi đủ chỗ cho cả lượt hái/bắt, hao tươi trước hành động và phát `spoiled` đúng một lần. Giữ rơi đồ theo thứ tự nhặt, xuất kho rỗng khi ngất.
- Đổi fixture giỏ và assert `lost`/kho bàn giao sang cá thể. Giữ các kiểm tra cá bơi/sinh, ngạt, bất tử và thứ tự Cá Sấu của Phase 2.

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
