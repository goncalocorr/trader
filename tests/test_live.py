import unittest

from agente import paper
from agente.live import resume, tick
from tests.test_strategy import flat_then_breakout

NOW = 151  # synthetic bars use t = 0..150, so the series is fresh
RISING_BTC = [(t, 0, 0, 0, 2000 + t, 0) for t in range(-1300, 151)]  # BTC regime on


class Live(unittest.TestCase):
    def test_first_tick_only_bookmarks_no_trading_on_old_bars(self):
        acc = paper.new_account(25.0)
        recs = tick(acc, now_ms=NOW, series={"X": flat_then_breakout()})
        self.assertEqual(recs, [])
        self.assertEqual(acc["last_t"]["X"], flat_then_breakout()[-1][0])

    def test_new_bar_is_evaluated_once(self):
        bars = flat_then_breakout()
        acc = paper.new_account(25.0)
        tick(acc, now_ms=NOW, series={"BTCUSDT": RISING_BTC, "X": bars[:-1]})
        recs = tick(acc, now_ms=NOW, series={"BTCUSDT": RISING_BTC, "X": bars})
        self.assertEqual(len(recs), 1)
        self.assertEqual(tick(acc, now_ms=NOW, series={"BTCUSDT": RISING_BTC, "X": bars}), [])

    def test_no_btc_data_means_no_trading(self):
        bars = flat_then_breakout()
        acc = paper.new_account(25.0)
        tick(acc, now_ms=NOW, series={"X": bars[:-1]})
        self.assertEqual(tick(acc, now_ms=NOW, series={"X": bars}), [])

    def test_stale_series_is_skipped(self):
        acc = paper.new_account(25.0)
        tick(acc, now_ms=10**12, series={"X": flat_then_breakout()})
        self.assertNotIn("X", acc["last_t"])

    def test_ok_resumes_after_halt(self):
        acc = paper.new_account(25.0)
        acc.update(halted=True, equity=18.0)
        resume(acc)
        self.assertFalse(acc["halted"])
        self.assertEqual(acc["peak"], 18.0)


if __name__ == "__main__":
    unittest.main()
