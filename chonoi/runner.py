"""Vòng tick (Contract B, mô hình tick).

Thứ tự ghi: snapshot tick 0 -> với mỗi bước: sự kiện (theo thứ tự xử lý) rồi snapshot (nếu tới lượt
hoặc buổi kết thúc) -> dòng 'end'. Mỗi tick tối đa một snapshot.

`Session` là API bước tick gọn dùng chung cho headless (`run`) và cửa sổ chơi trực tiếp (`chonoi.live`).
Hỗ trợ Phase 2:
- mode 'day' và điều phối ngày.
- Cơ chế Pause (Esc/P): đóng băng gameplay, chỉ tăng tick ngoài.
- Dòng 'end' và event có gắn kèm 'day' và 'days_completed'.
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


def build_sim(mode, tuning, scenario, seed, inventory=None, days=1):
    streams, ids = Streams(seed), IdAllocator()
    if mode == "gather":
        return GatherSim(tuning, scenario, streams, ids)
    elif mode == "quan":
        return QuanSim(tuning, scenario, streams, ids, inventory=inventory)
    elif mode == "day":
        return DaySim(tuning, scenario, streams, ids, days=days)
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

    def __init__(self, mode, tuning, scenario, seed, inventory=None, days=1):
        self.mode = mode
        self.tuning = tuning
        self.sim = build_sim(mode, tuning, scenario, seed, inventory, days=days)
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
        phase = getattr(self.sim, "phase", self.mode)
        day_num = getattr(self.sim, "day", None)

        def _wrap_event(name, data, t):
            row = {"type": "event", "tick": t, "phase": phase, "name": name, "data": data}
            if self.mode == "day" and day_num is not None:
                row["day"] = day_num
            return row

        # 1. Xét cạnh pause trước mọi hành động
        if not self.paused and inp.pressed("pause"):
            self.paused = True
            self.tick += 1
            return [_wrap_event("paused", {}, self.tick)]
        elif self.paused:
            if inp.pressed("pause"):
                self.paused = False
                self.tick += 1
                resumed_ev = _wrap_event("resumed", {}, self.tick)
                sub_events = self.sim.step(inp)
                ev_rows = [_wrap_event(name, data, self.tick) for name, data in sub_events]
                return [resumed_ev, *ev_rows]
            else:
                self.tick += 1
                return []

        # 2. Bước gameplay thông thường
        sub_events = self.sim.step(inp)
        self.tick += 1
        return [_wrap_event(name, data, self.tick) for name, data in sub_events]

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
            write_inventory(inventory_out, self.sim.inventory_items())


def run(mode, tuning, scenario, seed, frames, ticks, out_path, snapshot_every,
        inventory=None, inventory_out=None, days=1):
    sess = Session(mode, tuning, scenario, seed, inventory, days=days)
    player = InputPlayer(frames)
    w = JsonlWriter(out_path)
    try:
        # Ghi các sự kiện khởi tạo trước snapshot tick 0 nếu có (ví dụ day_start, day_plan)
        if hasattr(sess.sim, "flush_initial_events"):
            for name, data in sess.sim.flush_initial_events():
                ev = {"type": "event", "tick": 0, "phase": getattr(sess.sim, "phase", mode), "name": name, "data": data}
                if mode == "day":
                    ev["day"] = getattr(sess.sim, "day", 1)
                w.write(ev)

        w.write(sess.snapshot())  # tick 0: sau khi dựng scenario, trước mọi input
        last_snapped = 0
        while sess.tick < ticks and not sess.done:
            inp = player.advance(sess.tick)  # bước k đọc input có tick == k
            for row in sess.step(inp):
                w.write(row)
            if sess.tick % snapshot_every == 0 or sess.done:
                w.write(sess.snapshot())
                last_snapped = sess.tick
        if last_snapped != sess.tick:
            w.write(sess.snapshot())
        w.write(sess.end_row())
    finally:
        w.close()
    sess.write_inventory_if_done(inventory_out)
    return sess.sim
