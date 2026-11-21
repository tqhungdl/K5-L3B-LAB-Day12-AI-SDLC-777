"""Measure the live Gather canvas in Chromium at a 1280 × 720 viewport."""

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

from .contract import load_contract
from .live import LiveGame, LiveServer

WARMUP_S = 3
CAPTURE = """
({warmupMs, durationMs}) => {
    let firstFrame;
    const timestamps = [];
    window.__chonoiBenchFrame = (now) => {
        if (firstFrame === undefined) {
            firstFrame = now;
            window.__chonoiBenchFirstFrame = performance.timeOrigin + performance.now();
        }
        if (now - firstFrame < warmupMs) return;
        timestamps.push(now);
        if (now - timestamps[0] >= durationMs) {
            window.__chonoiBenchResult = {timestamps, firstFrame: window.__chonoiBenchFirstFrame};
            delete window.__chonoiBenchFrame;
        }
    };
}
"""


def frame_metrics(timestamps, load_ms):
    """Count completed frame intervals over the actual measurement window."""
    intervals = [(end - start) / 1000 for start, end in zip(timestamps, timestamps[1:])]
    if not intervals or any(not math.isfinite(dt) or dt <= 0 for dt in intervals):
        raise ValueError("Benchmark needs strictly increasing frame timestamps")
    frames = len(intervals)
    measured_s = (timestamps[-1] - timestamps[0]) / 1000
    slowest = sorted(intervals, reverse=True)[:math.ceil(frames / 100)]
    return {
        "avg_fps": frames / measured_s,
        "p1_low_fps": len(slowest) / math.fsum(slowest),
        "frames": frames,
        "measured_s": measured_s,
        "load_ms": load_ms,
    }


def run_benchmark(seed, duration, started_ms):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Install Playwright and Chromium using the benchmark setup in README.md") from exc

    contract = load_contract()
    game = LiveGame("gather", contract["tuning"], {}, seed, contract_version=contract["contract_version"])
    server = LiveServer(game, port=0)
    server.start()
    try:
        with sync_playwright() as playwright:
            channel = os.environ.get("CHONOI_BENCH_CHANNEL")
            browser = playwright.chromium.launch(channel=channel)
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
                settings = json.dumps({"warmupMs": WARMUP_S * 1000, "durationMs": duration * 1000})
                page.add_init_script(f"({CAPTURE})({settings})")
                page.goto(server.url, wait_until="domcontentloaded")
                result = page.wait_for_function(
                    "() => window.__chonoiBenchResult", timeout=(WARMUP_S + duration + 30) * 1000
                ).json_value()
            finally:
                browser.close()
    finally:
        server.stop()
    return frame_metrics(result["timestamps"], result["firstFrame"] - started_ms)


def main(argv=None):
    started_ms = time.time_ns() / 1_000_000
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if not math.isfinite(args.duration) or args.duration <= 0:
        parser.error("--duration must be finite and positive")
    try:
        result = run_benchmark(args.seed, args.duration, started_ms)
        args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"Benchmark failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
