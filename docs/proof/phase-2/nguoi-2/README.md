# Phase 2 · Bằng chứng lát 2

Nhánh `p2/gather-monsters` dựa trên `38a4dbf`. Manifest của checkout dùng v1.0. Bộ test lát 2 nạp dữ liệu Cá Sấu và nâng cấp từ fixture trước khi manifest v1.1 của lát 1 được tích hợp.

## Kết quả

| AC | Bằng chứng chạy tại lát 2 |
|---|---|
| AC-P2-03 | Test Gather kiểm bố trí M1/M2 theo Ngày, ngưỡng chase/hit, phân thắng theo ID, rơi LIFO, recoil, bất tử và thứ tự ngạt/hit/ngất. Test dựng Quán với kho thực của Gather sau ngất xác nhận kho rỗng và đơn giữ chỗ mâu thuẫn bị từ chối. |
| AC-P2-07 | Hái `keo_neo`, bắt `ca_keo` và ngất qua điểm vào headless bằng fixture. JSONL và file kho giống từng byte qua hai lượt cùng seed. Smoke hai tiến trình với kho v1.0 đã qua. |
| Scenario | Test khối Day, luật tiền/cấp, domain Cá Sấu, tuổi cá, giới hạn HP/oxy theo cấp hiệu lực và mã 2 giữ nguyên file đích khi fixture Cá Sấu lỗi. |

```bash
PYTHONPATH=tests:. python3 -m unittest discover -s tests -p 'test_p2*.py' -v
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
```

15 test lát 2 đạt. Bộ đầy đủ đạt 71 test, gồm cả test Live Server chạy với quyền mở localhost.

## Smoke kho v1.0

```bash
tmp_dir=$(mktemp -d /tmp/chonoi-p2-slice2.XXXXXX)
printf '%s\n' '{"gather":{"hold":["ca_loc","bong_sung","bong_sung"],"random_fish":false,"monsters":[]}}' > "$tmp_dir/dock.json"
printf '%s\n' '{"frames":[{"tick":0,"interact":true}]}' > "$tmp_dir/input.json"
python3 -m chonoi.headless --mode gather --seed 42 --scenario "$tmp_dir/dock.json" --inputs "$tmp_dir/input.json" --ticks 1 --out "$tmp_dir/gather.jsonl" --inventory-out "$tmp_dir/stock.json"
python3 -m chonoi.headless --mode quan --seed 42 --inventory "$tmp_dir/stock.json" --ticks 0 --out "$tmp_dir/quan.jsonl"
```

`gather_end` ở tick 1 có lý do `docked`. Đối chiếu bằng Python cho thấy `gather_end.inventory` và file kho đều chứa `{"items":{"bong_sung":2,"ca_loc":1}}`. Snapshot Quán tick 0 có `stock` khớp.

## Bàn giao tích hợp

- Sửa loader starter `chonoi/scenario.py` để nhận ba khối của Day và kiểm dữ liệu Gather mới. `DaySim` dùng `resolve_day_plans` để tính và kiểm preset/override. `QuanSim` kiểm khách, món và giữ chỗ theo menu và kho khi vào ca.
- Lát 1 cấp dữ liệu `tuning.gather.monsters` và hai hàm `init_fish`/`advance_fish`. Test lát 2 kiểm thời điểm gọi hai hàm qua mock. Cần chạy lại bằng module cá thật khi có v1.1.
- QA và Integrator chạy smoke hai tiến trình với cả `ca_keo` và `keo_neo`, cùng ca `--mode day` ngất mở Quán ở cùng tick. Xác nhận lỗi fixture Quán sau Gather trả mã 2 và giữ file JSONL đích. Ghi kết quả lên ma trận theo SHA bàn giao.
