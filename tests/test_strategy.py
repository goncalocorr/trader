import unittest

from agente.strategy import signal, skeptic


def flat_then_breakout(vol_last=300.0, n=150):
    # gentle uptrend so the close sits above the long average, range-bound highs
    bars = [(i, 100 + i * 0.01, 101 + i * 0.01, 99 + i * 0.01, 100 + i * 0.01, 100.0) for i in range(n)]
    c = bars[-1][4]
    bars.append((n, c, c + 4, c - 0.5, c + 3.5, vol_last))
    return bars


class Strategy(unittest.TestCase):
    def test_breakout_with_volume_gives_long_with_stop_and_target(self):
        p = signal(flat_then_breakout())
        self.assertIsNotNone(p)
        self.assertLess(p["stop"], p["entry"])
        self.assertAlmostEqual((p["target"] - p["entry"]) / (p["entry"] - p["stop"]), 2.0)

    def test_breakout_without_volume_is_ignored(self):
        self.assertIsNone(signal(flat_then_breakout(vol_last=100.0)))

    def test_too_little_history_is_ignored(self):
        self.assertIsNone(signal(flat_then_breakout(n=50)))

    def test_skeptic_skips_weak_edge(self):
        v, _ = skeptic({"entry": 100, "stop": 95, "atr": 2.5}, (0, 0, 101, 99, 100, 0), {"ev_r": 0.01})
        self.assertEqual(v, "saltar")

    def test_skeptic_skips_stop_just_under_round_number(self):
        p = {"entry": 82000, "stop": 79900, "atr": 1050}
        v, why = skeptic(p, (0, 0, 82100, 81500, 82000, 0), {"ev_r": 0.5})
        self.assertEqual(v, "saltar")
        self.assertIn("redondo", why)

    def test_skeptic_waits_on_stretched_candle(self):
        p = {"entry": 103, "stop": 98, "atr": 1.0}
        v, _ = skeptic(p, (0, 0, 104, 99, 103, 0), {"ev_r": 0.5})
        self.assertEqual(v, "esperar")

    def test_skeptic_buys_clean_setup(self):
        p = {"entry": 103, "stop": 98, "atr": 2.5}
        v, _ = skeptic(p, (0, 0, 104, 101, 103, 0), {"ev_r": 0.5})
        self.assertEqual(v, "comprar")


if __name__ == "__main__":
    unittest.main()
