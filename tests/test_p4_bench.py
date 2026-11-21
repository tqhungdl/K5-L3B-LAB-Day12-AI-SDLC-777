import unittest

from chonoi.bench import frame_metrics


class BenchmarkMetricsTest(unittest.TestCase):
    def test_slowest_one_percent_rounds_up(self):
        timestamps = [0, *range(10, 1000, 10), 1040, 1140]
        metrics = frame_metrics(timestamps, 250)
        self.assertEqual(metrics["frames"], 101)
        self.assertAlmostEqual(metrics["measured_s"], 1.14)
        self.assertAlmostEqual(metrics["avg_fps"], 101 / 1.14)
        self.assertAlmostEqual(metrics["p1_low_fps"], 2 / 0.15)
        self.assertEqual(metrics["load_ms"], 250)

    def test_rejects_nonincreasing_timestamps(self):
        with self.assertRaises(ValueError):
            frame_metrics([0, 0], 250)
