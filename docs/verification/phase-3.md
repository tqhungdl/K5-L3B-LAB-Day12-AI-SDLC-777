# Ma trận kiểm chứng Phase 3

Điền commit bàn giao và dẫn bằng chứng thực tế ở `docs/proof/phase-3/`. Các mã dưới đây do nhóm đặt để theo dõi Ticket 03.

| AC | Tiêu chí | Cách kiểm / bằng chứng cần lưu | Kết quả |
|---|---|---|---|
| AC-P3-01 | v1.2 đọc/ghi kho cá thể, từ chối kho đếm và dữ liệu sai. | File sai kiểu, ID trùng, loại lạ, fresh ngoài miền; ca v1.1 đọc kho đếm trong lúc chuyển; ca v1.2 đọc sát 30 và so lại file sau khi ghi. | Chưa kiểm v1.2 |
| AC-P3-02 | Gather cấp ID mới, tính hao đúng bước, `spoiled` đúng một lần và rơi LIFO. | Hái/bắt đủ chỗ và thiếu chỗ, hàng mới vẫn 100, hàng 30 ươn tick 1, nhiều ID hòa, hit rồi ngất trong bước. | Chưa kiểm v1.2 |
| AC-P3-03 | Kho Quán giữ cá thể chưa ươn theo ID và thử giữ lại khi nguyên liệu ươn. | Kiểm fresh đúng 30 ở đầu fixture, hai cá thể hòa điểm, hai đơn cạnh tranh, giữ lại đủ/thiếu, ID giữ trùng hoặc sai công thức. | Chưa kiểm v1.2 |
| AC-P3-04 | Nấu tiêu đúng cá thể được giữ, chốt giá và boa theo độ tươi. | Công thức nhiều cá thể ở hai phía biên làm tròn xuống; kiểm payload `cook_started`, món đã nấu, tiền, boa và điểm. | Chưa kiểm v1.2 |
| AC-P3-05 | File bàn giao đúng dữ liệu; ngất ghi rỗng, tick limit giữ nguyên file đích. | Smoke hai tiến trình ở phút 20; đối chiếu file, event và snapshot Quán tick 0. Thử kho đã ươn và chạy hai lần so byte. | Chưa kiểm v1.2 |
| AC-P3-06 | Trong `day`, chuyển pha giữ ID/fresh, Shop và pause dừng hao, Ngày mới cấp ID mới. | Fixture ca ngắn qua hai Ngày; kiểm `phase_tick:0`, không hao thêm khi chuyển, kho Shop và ID tăng sau mất hoặc tiêu. | Chưa kiểm v1.2 |
| AC-P3-07 | HUD cho thấy độ tươi hoặc hàng ươn, kho khả dụng đúng. | Chụp giỏ, Quán và Shop với cả hàng tươi, ươn và đã giữ. Ghi rõ ảnh từ lượt live hay dữ liệu demo. | Chưa kiểm v1.2 |
| AC-P3-08 | Regression P1/P2 còn hiệu lực và hồ sơ bàn giao đầy đủ. | Log test trên commit bàn giao, danh sách fixture đã đổi cùng lý do, CHANGELOG, clarify, nhật ký AI và tag `phase-3`. | Chưa kiểm v1.2 |

## Baseline v1.1 trước khi triển khai

- Commit `a1d002f`. Lệnh test chung chạy 88 test, không có assertion fail và có 3 lỗi socket từ hai test Live Server trong môi trường hiện tại.
- `python3 -m chonoi.live --mode day --days 1` trả mã 2 vì live CLI chỉ nhận Gather/Quán. Client có preview màn Day/Shop bằng `?demo=`. Người 4 kiểm hai đường riêng và ghi mức xác nhận trực tiếp khi bàn giao.
- Khi cập bến ở tick 1 trong `day` với nhịp snapshot mặc định, JSONL hiện ghi `phase_start` mang pha `gather` và thiếu snapshot Quán tick pha 0. Người 4 xử lý cùng bàn giao trong bộ nhớ.
- Checkout chưa có tag local; phiên này chưa xác minh được tag trên fork do lỗi phân giải GitHub. `PHASE3.md` đang là file mới chưa được theo dõi ở thời điểm lập kế hoạch.
