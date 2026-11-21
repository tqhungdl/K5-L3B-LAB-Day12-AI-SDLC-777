"""Vòng tick (Contract B, mô hình tick).

Thứ tự ghi: snapshot tick 0 -> với mỗi bước: sự kiện (theo thứ tự xử lý) rồi snapshot (nếu tới lượt
hoặc buổi kết thúc) -> dòng 'end'. Mỗi tick tối đa một snapshot.

`Session` là API bước tick gọn dùng chung cho headless (`run`) và cửa sổ chơi trực tiếp (`chonoi.live`).
Hỗ trợ Phase 2 & 3:
- mode 'day' và điều phối ngày.
- Cơ chế Pause (Esc/P): đóng băng gameplay, chỉ tăng tick ngoài.
- Dòng 'end' và event có gắn kèm 'day' và 'days_completed'.
- Bàn giao kho cá thể và snapshot pha mới tại phase_tick: 0.
"""

import math

from .ids import IdAllocator
from .inputs import InputPlayer
from .inventory import write_inventory
from .jsonl import JsonlWriter
from .rng import Streams
from .sim.day import DaySim
from .sim.gather import GatherSim
from .sim.quan import QuanSim


def build_sim(mode, tuning, scenario, seed, inventory=None, days=1,
              contract_version="1.1", *, allow_extended_days=False):
    streams, ids = Streams(seed), IdAllocator()
    if mode == "gather":
        return GatherSim(tuning, scenario, streams, ids)
    elif mode == "quan":
        return QuanSim(tuning, scenario, streams, ids, inventory=inventory)
    elif mode == "day":
        return DaySim(
            tuning, scenario, streams, ids, days=days,
            contract_version=contract_version,
            allow_extended_days=allow_extended_days,
        )
    raise ValueError(f"mode không hợp lệ: {mode}")


def _common(sim, tick, sim_tick, phase_tick, tuning, state):
    mult = tuning["score"]["reputation_multiplier"]
    phase = getattr(sim, "phase", sim.mode)
    return {
        "type": "snapshot", "tick": tick, "sim_tick": sim_tick, "mode": sim.mode, "phase": phase,
        "phase_tick": phase_tick, "state": state, "time_left_ticks": sim.time_left_ticks,
        "money": sim.money, "earned": sim.earned, "reputation": sim.reputation,
        "score": sim.earned + mult * math.floor(sim.reputation),
    }


class Session:
    """Một lượt chơi: dựng sim, bước từng tick, lấy snapshot / dòng end."""

    def __init__(self, mode, tuning, scenario, seed, inventory=None, days=1, *,
                 contract_version="1.1", allow_extended_days=False):
        self.mode = mode
        self.tuning = tuning
        self.contract_version = contract_version
        self.sim = build_sim(
            mode, tuning, scenario, seed, inventory, days=days,
            contract_version=contract_version,
            allow_extended_days=allow_extended_days,
        )
        self.tick = 0
        self.paused = False

    @property
    def done(self) -> bool:
        return self.sim.done

    def snapshot(self) -> dict:
        state = "paused" if self.paused else ("finished" if self.sim.done else "playing")
        sim_tick = getattr(self.sim, "sim_tick", self.tick)
        phase_tick = getattr(self.sim, "phase_tick", self.tick)
        s = _common(self.sim, self.tick, sim_tick, phase_tick, self.tuning, state)
        s.update(self.sim.snapshot())
        return s

    def step(self, inp) -> list:
        """Chạy một bước với `inp` (chonoi.inputs.InputState); trả các dòng event (tick = k + 1)."""
        # 1. Xét cạnh pause trước mọi hành động
        if not self.paused and inp.pressed("pause"):
            self.paused = True
            self.tick += 1
            cur_phase = getattr(self.sim, "phase", self.mode)
            row = {"type": "event", "tick": self.tick, "phase": cur_phase, "name": "paused", "data": {}}
            if self.mode == "day":
                row["day"] = getattr(self.sim, "day", 1)
            return [row]
        elif self.paused:
            if inp.pressed("pause"):
                self.paused = False
                self.tick += 1
                cur_phase = getattr(self.sim, "phase", self.mode)
                resumed_row = {"type": "event", "tick": self.tick, "phase": cur_phase, "name": "resumed", "data": {}}
                if self.mode == "day":
                    resumed_row["day"] = getattr(self.sim, "day", 1)
                sub_events = self.sim.step(inp)
                ev_rows = []
                for ev in sub_events:
                    name, data, *rest = ev
                    ev_phase = rest[0] if len(rest) > 0 else getattr(self.sim, "phase", self.mode)
                    ev_day = rest[1] if len(rest) > 1 else getattr(self.sim, "day", None)
                    r = {"type": "event", "tick": self.tick, "phase": ev_phase, "name": name, "data": data}
                    if self.mode == "day" and ev_day is not None:
                        r["day"] = ev_day
                    ev_rows.append(r)
                return [resumed_row, *ev_rows]
            else:
                self.tick += 1
                return []

        # 2. Bước gameplay thông thường
        sub_events = self.sim.step(inp)
        self.tick += 1
        ev_rows = []
        for ev in sub_events:
            name, data, *rest = ev
            ev_phase = rest[0] if len(rest) > 0 else getattr(self.sim, "phase", self.mode)
            ev_day = rest[1] if len(rest) > 1 else getattr(self.sim, "day", None)
            r = {"type": "event", "tick": self.tick, "phase": ev_phase, "name": name, "data": data}
            if self.mode == "day" and ev_day is not None:
                r["day"] = ev_day
            ev_rows.append(r)
        return ev_rows

    def end_row(self) -> dict:
        sim = self.sim
        sim_tick = getattr(sim, "sim_tick", self.tick)
        phase_tick = getattr(sim, "phase_tick", self.tick)
        score = _common(sim, self.tick, sim_tick, phase_tick, self.tuning, "")["score"]
        res = {
            "type": "end", "ticks": self.tick, "sim_tick": sim_tick, "mode": sim.mode,
            "state": "finished" if sim.done else "playing",
            "reason": sim.reason if sim.done else "tick_limit",
            "money": sim.money, "earned": sim.earned, "reputation": sim.reputation, "score": score
        }
        if self.mode == "day":
            res["days_completed"] = getattr(sim, "days_completed", 0)
        return res

    def write_inventory_if_done(self, inventory_out):
        """File kho: ghi MỘT lần khi có gather_end; chưa kết thúc thì giữ nguyên file đích."""
        if self.mode == "gather" and self.sim.done and inventory_out:
            write_inventory(inventory_out, self.sim.inventory_items(), contract_version=self.contract_version)


def run(mode, tuning, scenario, seed, frames, ticks, out_path, snapshot_every,
        inventory=None, inventory_out=None, days=1, *, contract_version="1.1"):
    sess = Session(mode, tuning, scenario, seed, inventory, days=days, contract_version=contract_version)
    player = InputPlayer(frames)
    w = JsonlWriter(out_path)
    try:
        # Ghi các sự kiện khởi tạo trước snapshot tick 0 nếu có (ví dụ day_start, day_plan)
        if hasattr(sess.sim, "flush_initial_events"):
            for ev in sess.sim.flush_initial_events():
                name, data, *rest = ev
                ev_phase = rest[0] if len(rest) > 0 else getattr(sess.sim, "phase", mode)
                ev_day = rest[1] if len(rest) > 1 else getattr(sess.sim, "day", 1)
                row = {"type": "event", "tick": 0, "phase": ev_phase, "name": name, "data": data}
                if mode == "day":
                    row["day"] = ev_day
                w.write(row)

        w.write(sess.snapshot())  # tick 0: sau khi dựng scenario, trước mọi input
        last_snapped = 0
        old_phase = getattr(sess.sim, "phase", None)

        while sess.tick < ticks and not sess.done:
            inp = player.advance(sess.tick)  # bước k đọc input có tick == k
            evs = sess.step(inp)
            for ev in evs:
                w.write(ev)

            new_phase = getattr(sess.sim, "phase", None)
            # Khi đổi pha trong mode day: ghi ngay snapshot pha mới tại phase_tick 0!
            if old_phase != new_phase and not sess.done:
                w.write(sess.snapshot())
                last_snapped = sess.tick
                old_phase = new_phase
            elif sess.tick % snapshot_every == 0 or sess.done:
                w.write(sess.snapshot())
                last_snapped = sess.tick

        if last_snapped != sess.tick:
            w.write(sess.snapshot())
        sess.write_inventory_if_done(inventory_out)
        w.write(sess.end_row())
    finally:
        w.close()
