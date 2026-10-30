import unittest

from agente import paper
from agente.desk import decide
from tests.test_strategy import flat_then_breakout


class Desk(unittest.TestCase):
    def test_no_signal_no_record(self):
        acc = paper.new_account(25.0)
        self.assertIsNone(decide(acc, "X", flat_then_breakout(vol_last=100.0)))

    def test_signal_is_logged_with_every_opinion(self):
        acc = paper.new_account(25.0)
        rec = decide(acc, "X", flat_then_breakout())
        for key in ("t", "symbol", "signal", "mc", "skeptic", "reason"):
            self.assertIn(key, rec)

    def test_order_only_after_skeptic_buys_and_risk_approves(self):
        acc = paper.new_account(25.0)
        rec = decide(acc, "X", flat_then_breakout())
        opened = "X" in acc["positions"]
        self.assertEqual(opened, rec["skeptic"] == "comprar" and rec["risk"]["ok"])

    def test_bad_btc_regime_blocks_signal(self):
        acc = paper.new_account(25.0)
        falling_btc = [(i, 0, 0, 0, 1000 - i * 0.1, 0) for i in range(2000)]
        self.assertIsNone(decide(acc, "X", flat_then_breakout(), btc=falling_btc))

    def test_halted_account_never_opens(self):
        acc = paper.new_account(25.0)
        acc["halted"] = True
        decide(acc, "X", flat_then_breakout())
        self.assertEqual(acc["positions"], {})


if __name__ == "__main__":
    unittest.main()
