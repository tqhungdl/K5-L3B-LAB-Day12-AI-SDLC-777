# TEAM

**Tên nhóm:** 777  **Số người:** 4  (khớp `team_size` trong `game.contract.json`)

| Thành viên | GitHub handle | Module chính | Vai quy trình | Người dự phòng cho |
|---|---|---|---|---|
| Trần Quang Hùng | tqhungdl | sim/gather | PO / Leader | sim/quan |
| Nguyễn Tiến Đạt | chesschillchill | sim/quan | QA Lead | sim/gather |
| Nguyễn Quang Huy | nguyenquanghuy091204 | client/ui | UI Lead | sim/quan |
| Đào Nguyễn Quang Thành | ThanhDao11 | sim/day | Integrator / Release | client/ui |

**Vai quy trình:** PO (đầu mối hỏi giảng viên, giữ `docs/clarify.md`) · Integrator (giữ `docs/contracts/`, gắn tag) · QA lead · Scrum/Release. Có thể kiêm.

## Thỏa thuận làm việc nhóm (điền trong 15 phút kickoff, ≤ 10 dòng)

- Kênh liên lạc: Discord / Zalo nhóm 777
- Khi bất đồng về thiết kế: Thảo luận 2 phút, nếu chưa xong thì Integrator chốt quyết định kỹ thuật và ghi lý do.
- Khi ai đó trễ hoặc vướng quá 10 phút: Báo ngay lên kênh chat nhóm, người dự phòng lập tức nhận hỗ trợ.
- Giờ standup giữa phase: Phút thứ 20 của mỗi phase.
- Cách đọc code của nhau: Review chéo theo lát liền kề (1 ↔ 2, 3 ↔ 4) qua GitHub PR trước khi merge.
- Cách làm việc với Git: Làm trên nhánh tính năng riêng theo kế hoạch, chạy test đạt 100% trước khi tạo PR, Integrator gộp và gắn tag.

## Báo cáo đóng góp qua bốn phase

Báo cáo dựa trên lịch sử Git, bằng chứng kiểm thử và các bản phản tư đã có trong repo.

### Trần Quang Hùng (`tqhungdl`)

- **Phase 1** — Triển khai cơ chế oxy và nối các thao tác hái rau, bắt cá vào vòng lặp Gather. Commit `f0addd4`, `73b4d69`.
- **Phase 2** — Cập nhật dữ liệu v1.1 và triển khai cá bơi, đổi hướng, phản xạ và sinh theo seed. Commit `a1d002f`.
- **Phase 3** — Xây bộ đọc/ghi kho theo phiên bản và sửa luồng tích hợp kho cá thể. Commit `b692d5a`, `8be707f`.
- **Phase 4** — Thêm benchmark render, sửa độ chính xác của độ tươi khi chuyển pha và kiểm bản phát hành. Lưu bằng chứng chạy từ clone sạch trên Ubuntu và video demo. Commit `8cd94ad`, `01f5892`.

### Nguyễn Tiến Đạt (`chesschillchill`)

- **Phase 1** — Triển khai hái rau, bắt cá và HUD khi chơi. Ghi lại giao diện bàn giao kho và bằng chứng kiểm thử. Commit `4073fbf`, `7c949c8`.
- **Phase 2** — Triển khai hành vi Cá Sấu và kiểm dữ liệu scenario của Gather. Commit `67ce56f`.
- **Phase 3** — Triển khai độ tươi theo cá thể trong Gather và tài liệu phân công, tích hợp Phase 3. Commit `0171a14`, `dbbc504`.
- **Phase 4** — Triển khai chế độ tương phản cao, nhãn cảnh báo, hook đo khung hình và luồng màn hình Day trên trình duyệt. Lưu ảnh và log kiểm chứng. Commit `2738fdd`, `3170ebe`, `487467e`.

### Nguyễn Quang Huy (`nguyenquanghuy091204`)

- **Phase 1** — Triển khai khách gọi món, giữ nguyên liệu và kiểm fixture Quán. Commit `232bdcb`.
- **Phase 2** — Mở rộng Quán lên hai bếp, bốn bàn và sáu món, thêm lọc món theo kế hoạch Ngày và cập nhật giao diện Quán. Commit `1fdd183`.
- **Phase 3** — Triển khai giữ chỗ theo ID cá thể, xử lý hàng ươn và tính giá theo độ tươi. Bổ sung log test và smoke cho ba phase đầu. Commit `ce58224`, `9813650`.
- **Phase 4** — Triển khai soak tất định qua 10 Ngày trong một Session, kiểm tính liên tục của trạng thái và ID, cập nhật retro và nhật ký AI. Commit `233015c`, `54c987f`. [Phản tư cá nhân](docs/members/nguyenquanghuy091204.md)

### Đào Nguyễn Quang Thành (`ThanhDao11`)

- **Phase 1** — Triển khai nấu, bưng, phục vụ, thanh toán, boa, uy tín và đóng ca. Viết test cho luồng phục vụ. Commit `e79afe1`.
- **Phase 2** — Triển khai vòng Ngày, Shop nâng cấp và pause. Commit `96ec98f`.
- **Phase 3** — Cập nhật Day/Shop và runner để bàn giao kho cá thể và ghi snapshot ngay khi đổi pha. Commit `c56ae4f`.
- **Phase 4** — Bật Test Contract v1.3, thêm kiểm tra tương thích và chuẩn bị gói ứng viên cùng hướng dẫn khởi chạy. Commit `17d6df3`. [Phản tư cá nhân](docs/members/ThanhDao11.md)

### Kết quả bàn giao chung

Bản `v1.0.0` tại commit `01f5892` có ZIP chạy được và video demo 36 giây. Bộ hồi quy đạt 128 test. Soak hoàn tất 10 Ngày với 0 lỗi. Benchmark đạt trung bình 60,13 FPS và 56,23 FPS ở nhóm 1% khung chậm nhất. Thời gian đến khung đầu là 11,44 giây, cao hơn mốc báo cáo 10 giây. [Ma trận kiểm chứng](docs/verification/phase-4.md) · [Bản phát hành](https://github.com/tqhungdl/K5-L3B-LAB-Day12-AI-SDLC-777/releases/tag/v1.0.0)

