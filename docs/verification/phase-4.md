# Ma trận kiểm chứng Phase 4

Ghi SHA của commit bàn giao, lệnh/cách kiểm và đường dẫn bằng chứng thật tại `docs/proof/phase-4/`. Các mã AC dưới đây dùng để truy vết [Ticket 04](../../PHASE4.md).

| AC | Tiêu chí | Cách kiểm và bằng chứng | Kết quả |
|---|---|---|---|
| AC-P4-01 | Manifest v1.3 và tương thích v1.2 | `test_p4_contract` kiểm kho cá thể, từ chối kho đếm, ngưỡng 30, JSONL giống từng byte giữa v1.2/v1.3 và kho dư ở Shop. [Log hồi quy](../proof/phase-4/unittest.log). | 128/128 test đạt trên bản ứng viên |
| AC-P4-02 | Benchmark thật và đúng 5 trường | Seed 42, 1280×720, 3 giây làm nóng và 30 giây đo. Edge 158 headless, Playwright 1.65.2, Windows build 19045, CPU AuthenticAMD Family 23 Model 24. [Số đo](../proof/phase-4/bench.json). | 60,13 FPS trung bình và 56,23 FPS 1% low. Tải 11,44 s, vượt mốc 10 s |
| AC-P4-03 | Ba cảnh báo và tương phản cao | Edge ở 1280×720 với manifest v1.3. Enter bật, Space tắt. [Thủy quái và oxy](../proof/phase-4/ui/gather-v13-contrast.png), [khách sắp giận](../proof/phase-4/ui/quan-v13-contrast.png). | Kiểm trên bản ứng viên |
| AC-P4-04 | Soak 10 Ngày trong một tiến trình | [Soak bản ứng viên](../proof/phase-4/soak-candidate.json) và kiểm lặp cùng seed trong [log hồi quy](../proof/phase-4/unittest.log). | 10 Ngày, 0 lỗi |
| AC-P4-05 | Bản chạy từ clone sạch và gói Release | Giải nén [ZIP ứng viên](../proof/phase-4/release/cho-noi-v1.0.0.zip) vào thư mục sạch và kiểm CLI phục vụ canvas và menu Day. [Log đóng gói](../proof/phase-4/release/package-smoke.txt). | Gói ứng viên chạy trên Windows. Chờ kiểm clone của SHA bàn giao trên macOS/Linux |
| AC-P4-06 | Hồ sơ dự án và phát hành | [Ghi chú phát hành](../../RELEASE_NOTES.md), [CHANGELOG](../../CHANGELOG.md), [CREDITS](../../CREDITS.md). | Chờ SHA bàn giao, tag và GitHub Release. Chưa xác nhận giấy phép để thêm LICENSE |
| AC-P4-07 | Đóng góp, retro, demo | [Retro](../retro.md) đã rà hành động P2 và ghi lỗi AI. Chơi Day rút ngắn qua hai ca và đóng Shop, thu 72 nghìn. [Log Edge](../proof/phase-4/ui/day-v13.txt) · [Tổng kết](../proof/phase-4/ui/day-v13-summary.png). | Có 2/4 phản tư cá nhân. Demo nộp cuối còn chờ |

## Bản ứng viên

- Base Git `6826ebf69e1e11da2435f23964831cdd6d220259` cùng các thay đổi Phase 4 trong working tree. Chưa có SHA bàn giao. GitHub `main` ở cùng base lúc kiểm và chưa có tag `phase-4` hoặc `v1.0.0`.
- Chuyển các fixture hồi quy chạy trên CLI mặc định sang schema cá thể hiện hành. Kiểm giỏ đếm lịch sử giữ tuning v1.1 trong fixture riêng. Test roster mẫu dùng fixture rỗng thay vì đọc `TEAM.md` đã điền.

## Baseline trước khi triển khai

- Commit gốc `8be707f` có code độ tươi nhưng manifest chọn v1.1 và chưa có `tuning.freshness`. Fixture giỏ cá thể trả mã 2 với manifest hiện tại. Với manifest v1.2 tạm, fixture chạy mã 0 và phát `spoiled` ở tick 1. Nhánh `p4/release-contract` chịu trách nhiệm bật v1.3 và kiểm hai đầu kho.
- `DaySim` hiện kẹp tối đa 5 Ngày. `p4/headless-soak` chịu trách nhiệm lối gọi 10 Ngày riêng.
- `LiveGame.state_json()` chưa trả `presentation` và `POST /presentation` còn bỏ qua hành động. `p4/accessible-ui` chịu trách nhiệm nối luồng UI thật. `p4/render-bench` dùng Gather trực tiếp với seed chuẩn.
- Bộ test baseline đạt **114/114** khi cho phép socket localhost. Lần chạy trong sandbox gặp 4 lỗi socket của Live Server. Suite hiện tại chưa thay thế việc kiểm manifest thật và chạy Day qua trình duyệt.
- `TEAM.md` và `CREDITS.md` còn khung mẫu, chưa có `LICENSE` trong cây Git. `PHASE4.md` chưa được Git theo dõi lúc lập kế hoạch. Đã kiểm `git ls-remote --tags origin` và fork chưa công bố tag nào. Người 4 rà bằng chứng của các phase trước, dữ liệu nhóm, giấy phép và gói phát hành.
