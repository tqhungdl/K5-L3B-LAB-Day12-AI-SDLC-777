# Quán Ăn Chợ Nổi v1.0.0

- Chơi trọn vòng Ngày từ Lặn & Hái đến Mở Quán và Cửa hàng Má Tư.
- Kho cá thể giữ ID và độ tươi khi chuyển ca. Độ tươi ảnh hưởng đến giữ chỗ, giá món và tiền boa.
- Cảnh báo thủy quái, oxy thấp và khách sắp giận có nhãn riêng. Có thể bật chế độ tương phản cao bằng bàn phím.
- Test Contract v1.3 hỗ trợ benchmark render và soak headless 10 Ngày.

Giải nén `cho-noi-v1.0.0.zip`, mở terminal trong thư mục đã giải nén và chạy `python3 -m chonoi.live --mode day --days 5`. Cần Python 3.10 trở lên và một trình duyệt. Mở địa chỉ localhost in trong terminal.

File kho phải dùng mảng cá thể theo v1.2/v1.3. Benchmark cần Playwright và Chromium, xem hướng dẫn cài trong README. Phép đo trên Windows với Edge headless đạt 60,13 FPS trung bình và 56,23 FPS ở nhóm 1% khung chậm nhất. Thời gian đến khung đầu là 11,44 giây, cao hơn mốc báo cáo 10 giây.
