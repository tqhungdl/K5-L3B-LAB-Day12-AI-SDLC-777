# Ma trận kiểm chứng Phase 3

- **Trạng thái checkout kiểm chứng:** Nhánh `p3/quan-freshness`, commit `ce58224` (dựa trên `main` `dbbc504`). Manifest `game.contract.json` hiện vẫn ở **`contract_version: "1.1"`**; các nhánh Lát 1 (`p3/inventory`), Lát 2 (`p3/gather-freshness`) và Lát 4 (`p3/day-hud`) chưa gộp lên `main`. `git tag -l` chưa có tag `phase-3`.
- **Kết quả chạy thật trên nhánh `p3/quan-freshness` (`ce58224`):**
  - Test riêng Lát 3 Quán (`test_p3_quan.py` + regression Quán `test_p1_quan_customers.py`, `test_p1_quan_service.py`, `test_p2_quan.py`): **31/31 PASS** (`2.304s`) tại [nguoi-3/test-p3-quan.log](../proof/phase-3/nguoi-3/test-p3-quan.log).
  - Toàn bộ bộ test suite trên nhánh `p3/quan-freshness`: **95/95 PASS** (`11.020s`) tại [nguoi-3/test-all-p3-branch.log](../proof/phase-3/nguoi-3/test-all-p3-branch.log).

| AC | Tiêu chí | Cách kiểm / bằng chứng cần lưu | Kết quả |
|---|---|---|---|
| AC-P3-01 | v1.2 đọc/ghi kho cá thể, từ chối kho đếm và dữ liệu sai. | Chờ Lát 1 (`p3/inventory`) triển khai `test_p3_inventory.py`, nâng `game.contract.json` lên `1.2` và cập nhật `inventory.py`/`scenario.py`/`jsonl.py`. | Chưa đạt (chưa ghép Lát 1; `game.contract.json` vẫn là `1.1`) |
| AC-P3-02 | Gather cấp ID mới, tính hao đúng bước, `spoiled` đúng một lần và rơi LIFO. | Chờ Lát 2 (`p3/gather-freshness`) triển khai độ tươi cho `gather.py`/`gather_resources.py`/`gather_monsters.py` và `test_p3_gather.py`. | Chưa đạt (chưa ghép Lát 2) |
| AC-P3-03 | Kho Quán giữ cá thể chưa ươn theo ID và thử giữ lại khi nguyên liệu ươn. | Chạy `tests/test_p3_quan.py` (`test_01` chọn tươi nhất hòa ID, `test_02` `fresh=30` ươn tick 1 & hai đơn cạnh tranh giữ lại, `test_03` nhả phần còn tươi khi chuyển `unfulfillable`, `test_06` từ chối kho đếm/ID trùng/hàng ươn/sai công thức, `test_07` bỏ qua hàng ươn phát `no_dish`). Bằng chứng: [nguoi-3/test-p3-quan.log](../proof/phase-3/nguoi-3/test-p3-quan.log). | Đạt ở cấp module độc lập (chờ kiểm lại trên `main` sau khi bật manifest `1.2`) |
| AC-P3-04 | Nấu tiêu đúng cá thể được giữ, chốt giá và boa theo độ tươi. | Chạy `tests/test_p3_quan.py` (`test_04` tiêu đúng ID, làm tròn xuống biên dưới `base_price=29` & `tip=floor(29*0.2)=5`, `test_05` `cook_started.items` 4 cá thể sắp theo `(kind, id)` & `base_price=119`). Bằng chứng: [nguoi-3/test-p3-quan.log](../proof/phase-3/nguoi-3/test-p3-quan.log). | Đạt ở cấp module độc lập (chờ kiểm lại trên `main` sau khi bật manifest `1.2`) |
| AC-P3-05 | File bàn giao đúng dữ liệu; ngất ghi rỗng, tick limit giữ nguyên file đích. | Chạy smoke 2 tiến trình v1.2 (`gather --inventory-out → quan --inventory`) trên bản tích hợp sau khi gộp Lát 1 + 2 + 3 và bật `contract_version: "1.2"`. | Chưa đạt (chờ gộp Lát 1 & 2 để bật v1.2) |
| AC-P3-06 | Trong `day`, chuyển pha giữ ID/fresh, Shop và pause dừng hao, Ngày mới cấp ID mới. | Chờ Lát 4 (`p3/day-hud`) chuyển `day.py`/`shop.py`/`runner.py` sang kho cá thể và viết `test_p3_day.py`. | Chưa đạt (chưa ghép Lát 4) |
| AC-P3-07 | HUD cho thấy độ tươi hoặc hàng ươn, kho khả dụng đúng. | Chờ Lát 4 (`p3/day-hud`) cập nhật `chonoi/web/index.html` & `chonoi/live.py` cho kho cá thể và chụp ảnh kiểm chứng. | Chưa đạt (chưa ghép Lát 4) |
| AC-P3-08 | Regression P1/P2 còn hiệu lực và hồ sơ bàn giao đầy đủ. | Bộ test hiện tại trên `p3/quan-freshness` đạt **95/95 PASS** ([nguoi-3/test-all-p3-branch.log](../proof/phase-3/nguoi-3/test-all-p3-branch.log)); kiểm hồ sơ thấy `CHANGELOG.md` mới có `## Unreleased`, `TEAM.md` chưa điền (`check_team.py` exit `1`), chưa có tag `phase-3`. | Chưa đạt (regression Quán hiện xanh; chờ tích hợp đủ 4 lát, cập nhật `CHANGELOG.md`, `TEAM.md`, `docs/retro.md`, `docs/ai-usage-log.md` và đẩy tag `phase-3`) |

## Lý do thay đổi test cũ trong Lát 3 (chuẩn bị chuyển tiếp v1.1 → v1.2)

- `tests/test_p1_quan_service.py`: Tự chuyển shape `stock`/`reserved` sang mảng cá thể và đối chiếu giá sau 1 tick hao (`base_price=59`) khi `game.contract.json` bật `tuning.freshness`, giữ nguyên toàn bộ 6 kịch bản hành vi nấu/bưng/phục vụ/boa/đóng ca.
- `tests/test_p2_quan.py`: `v11_tuning()` gỡ khóa `freshness` để giữ kiểm hồi quy 2 bếp/4 bàn/6 món/kế hoạch ngày độc lập với độ tươi v1.2.

## Baseline v1.1 trước khi triển khai

- Commit `a1d002f`. Lệnh test chung chạy 88 test trên v1.1 (tại checkout Windows `ce58224`, toàn bộ 95/95 test gồm cả 2 test Live Server đều chạy qua).
- `python -m chonoi.live --mode day --days 1` vẫn trả mã `2` vì live CLI chỉ nhận `gather`/`quan`.
- Khi cập bến ở tick `1` trong `day` với nhịp snapshot mặc định (`10`), JSONL hiện ghi `phase_start` mang pha `gather` và thiếu snapshot Quán `phase_tick: 0` (đã xác nhận thực tế tại [../phase-2/integration/day-dock-default-snap.jsonl.txt](../proof/phase-2/integration/day-dock-default-snap.jsonl.txt)) — Người 4 xử lý cùng bàn giao trong bộ nhớ ở `p3/day-hud`.
- Checkout chưa có tag local (`phase-1`, `phase-2`, `phase-3`).
