# Ma trận kiểm chứng Phase 4

Ghi SHA của commit bàn giao, lệnh/cách kiểm và đường dẫn bằng chứng thật tại `docs/proof/phase-4/`. Các mã AC dưới đây dùng để truy vết [Ticket 04](../../PHASE4.md).

| AC | Tiêu chí | Cách kiểm và bằng chứng | Kết quả |
|---|---|---|---|
| AC-P4-01 | Manifest v1.3 và tương thích v1.2 | Chạy fixture qua ngưỡng 30, bàn giao file và Day, từ chối kho đếm mã 2. So JSONL cùng fixture v1.2/v1.3 và chạy hồi quy P1–P3. | Chưa kiểm v1.3 |
| AC-P4-02 | Benchmark thật và đúng 5 trường | Seed 42, 1280×720, 3 giây làm nóng + 30 giây đo. Lưu `bench.json`, thông tin máy và đối chiếu công thức/mốc báo cáo. | Chưa kiểm v1.3 |
| AC-P4-03 | Ba cảnh báo và tương phản cao | Chơi thử cả ba cảnh báo ở chế độ tương phản cao, lưu ảnh hoặc video và kiểm bật/tắt bằng bàn phím. | Chưa kiểm v1.3 |
| AC-P4-04 | Soak 10 Ngày trong một tiến trình | Lưu `soak.json` với 10 kết quả, 0 lỗi. Kiểm kế hoạch ngày 6–10, trạng thái xuyên Ngày, kết quả lấy lúc đóng Shop và so phần gameplay của hai lượt cùng seed. | Chưa kiểm v1.3 |
| AC-P4-05 | Bản chạy từ clone sạch và gói Release | Chạy giao diện từ clone mới bằng tối đa 3 lệnh; giải nén gói vào thư mục khác và thử chạy lại. Lưu log, SHA, tên asset và cách chạy. | Chưa kiểm v1.3 |
| AC-P4-06 | Hồ sơ dự án và phát hành | Đối chiếu tag `phase-4` và `v1.0.0` cùng SHA trên `main`. Kiểm Release notes, asset, CHANGELOG theo phase, CREDITS và giấy phép. | Chưa bàn giao |
| AC-P4-07 | Đóng góp, retro, demo | Rà hành động P2, ghi một lỗi AI và cách xác minh, có bốn phản tư và link bằng chứng cá nhân. Demo đủ bốn mục của ticket. | Chưa bàn giao |

## Baseline trước khi triển khai

- Commit gốc `8be707f` có code độ tươi nhưng manifest chọn v1.1 và chưa có `tuning.freshness`. Fixture giỏ cá thể trả mã 2 với manifest hiện tại. Với manifest v1.2 tạm, fixture chạy mã 0 và phát `spoiled` ở tick 1. Nhánh `p4/release-contract` chịu trách nhiệm bật v1.3 và kiểm hai đầu kho.
- `DaySim` hiện kẹp tối đa 5 Ngày. `p4/headless-soak` chịu trách nhiệm lối gọi 10 Ngày riêng.
- `LiveGame.state_json()` chưa trả `presentation` và `POST /presentation` còn bỏ qua hành động. `p4/accessible-ui` chịu trách nhiệm nối luồng UI thật. `p4/render-bench` dùng Gather trực tiếp với seed chuẩn.
- Bộ test baseline đạt **114/114** khi cho phép socket localhost. Lần chạy trong sandbox gặp 4 lỗi socket của Live Server. Suite hiện tại chưa thay thế việc kiểm manifest thật và chạy Day qua trình duyệt.
- `TEAM.md` và `CREDITS.md` còn khung mẫu, chưa có `LICENSE` trong cây Git. `PHASE4.md` chưa được Git theo dõi lúc lập kế hoạch. Đã kiểm `git ls-remote --tags origin` và fork chưa công bố tag nào. Người 4 rà bằng chứng của các phase trước, dữ liệu nhóm, giấy phép và gói phát hành.
