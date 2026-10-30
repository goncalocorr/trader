import unittest

from agente.strategy import REGIME_N, regime_ok, skeptic, target_weights
from tests.helpers import falling, rising


class Strategy(unittest.TestCase):
    def test_regime_on_when_btc_above_200_day_average(self):
        self.assertTrue(regime_ok(rising()))

    def test_regime_off_when_btc_below_average(self):
        self.assertFalse(regime_ok(falling()))

    def test_regime_off_without_enough_history(self):
        self.assertFalse(regime_ok(rising(REGIME_N)))

    def test_holds_only_coins_above_50_day_average(self):
        w = target_weights({"A": rising(), "B": falling()}, btc=rising())
        self.assertEqual(set(w), {"A"})

    def test_calm_coins_get_equal_full_weight(self):
        w = target_weights({"A": rising(), "B": rising(step=0.003)}, btc=rising())
        self.assertAlmostEqual(w["A"], 0.5)
        self.assertAlmostEqual(w["B"], 0.5)

    def test_volatile_portfolio_is_scaled_to_the_vol_target(self):
        wild = [100 * 1.001 ** i * (1.1 if i % 2 else 1.0) for i in range(400)]
        w = target_weights({"A": wild}, btc=rising())
        self.assertLess(w["A"], 1.0)
        self.assertGreater(w["A"], 0.0)

    def test_everything_to_cash_when_regime_is_off(self):
        self.assertEqual(target_weights({"A": rising()}, btc=falling()), {})

    def test_skeptic_holds_back_buying_into_a_spike(self):
        spike = rising()[:-1] + [rising()[-2] * 1.5]
        w, why = skeptic({"A": spike}, current={"A": 0.1}, target={"A": 0.4})
        self.assertAlmostEqual(w["A"], 0.1)
        self.assertIn("A", why)

    def test_skeptic_lets_normal_moves_through(self):
        w, why = skeptic({"A": rising()}, current={}, target={"A": 0.4})
        self.assertEqual(w, {"A": 0.4})
        self.assertEqual(why, {})


if __name__ == "__main__":
    unittest.main()
