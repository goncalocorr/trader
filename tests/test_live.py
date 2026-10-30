import unittest

from agente import paper
from agente.live import resume, summary, tick
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

    def test_first_tick_remembers_btc_start_price(self):
        acc = paper.new_account(25.0)
        tick(acc, SERIES, now_ms=NOW)
        self.assertAlmostEqual(acc["btc_start"], SERIES["BTCUSDT"][-1][4])

    def test_each_decision_is_added_to_the_history(self):
        acc = paper.new_account(25.0)
        tick(acc, {s: b[:-1] for s, b in SERIES.items()}, now_ms=NOW)
        tick(acc, SERIES, now_ms=NOW)
        self.assertEqual([h[0] for h in acc["historico"]], [399 * DAY])

    def test_summary_shows_capital_position_and_decision(self):
        acc = paper.new_account(25.0)
        acc.update(equity=26.0, cash=20.0, positions={"SOLUSDT": 0.05}, px={"SOLUSDT": 120.0},
                   btc_start=100.0, historico=[[399 * DAY, 26.0]])
        rec = {"t": 399 * DAY, "regime": True, "target": {"SOLUSDT": 0.23}, "skeptic": {},
               "risk": "aprovado", "fills": [{"symbol": "SOLUSDT", "lado": "compra", "qty": 0.05, "preco": 120.0}]}
        md = summary(acc, [rec], btc_now=110.0)
        for text in ("26.00 USDT", "+4.0%", "SOLUSDT", "6.00 USDT", "ligado", "compra", "BTC", "+10.0%"):
            self.assertIn(text, md)

    def test_summary_warns_when_halted(self):
        acc = paper.new_account(25.0)
        acc["halted"] = True
        self.assertIn("PARADO", summary(acc, [], btc_now=None))

    def test_ok_resumes_after_halt(self):
        acc = paper.new_account(25.0)
        acc.update(halted=True, equity=18.0)
        resume(acc)
        self.assertFalse(acc["halted"])
        self.assertEqual(acc["peak"], 18.0)


if __name__ == "__main__":
    unittest.main()
