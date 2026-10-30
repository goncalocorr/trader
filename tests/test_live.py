import unittest

from agente import paper
from agente.live import resume, tick
from tests.helpers import DAY, bars, rising

SERIES = {"BTCUSDT": bars(rising()), "A": bars(rising())}
NOW = 400 * DAY  # last bar opened on day 399: fresh


class Live(unittest.TestCase):
    def test_first_tick_only_bookmarks(self):
        acc = paper.new_account(1000.0)
        self.assertEqual(tick(acc, SERIES, now_ms=NOW), [])
        self.assertEqual(acc["last_t"], 399 * DAY)

    def test_new_day_is_processed_once(self):
        acc = paper.new_account(1000.0)
        tick(acc, {s: b[:-1] for s, b in SERIES.items()}, now_ms=NOW)
        self.assertEqual(len(tick(acc, SERIES, now_ms=NOW)), 1)
        self.assertEqual(tick(acc, SERIES, now_ms=NOW), [])

    def test_missed_days_decide_only_on_the_latest_close(self):
        acc = paper.new_account(1000.0)
        tick(acc, {s: b[:-3] for s, b in SERIES.items()}, now_ms=397 * DAY)
        recs = tick(acc, SERIES, now_ms=NOW)
        self.assertEqual([r["t"] for r in recs], [399 * DAY])

    def test_stale_data_means_no_trading(self):
        acc = paper.new_account(1000.0)
        self.assertEqual(tick(acc, SERIES, now_ms=NOW + 10 * DAY), [])
        self.assertNotIn("last_t", acc)

    def test_ok_resumes_after_halt(self):
        acc = paper.new_account(25.0)
        acc.update(halted=True, equity=18.0)
        resume(acc)
        self.assertFalse(acc["halted"])
        self.assertEqual(acc["peak"], 18.0)


if __name__ == "__main__":
    unittest.main()
