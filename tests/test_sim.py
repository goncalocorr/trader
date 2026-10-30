import unittest

from agente.sim import drawdown_risk


class MonteCarlo(unittest.TestCase):
    def test_flat_market_never_breaches(self):
        self.assertEqual(drawdown_risk({"A": 1.0}, [{"A": 0.0}] * 50), 0.0)

    def test_steady_fall_always_breaches(self):
        # 1 - 0.98**30 = 45% > 25%
        self.assertEqual(drawdown_risk({"A": 1.0}, [{"A": -0.02}] * 50), 1.0)

    def test_small_weight_survives_the_same_fall(self):
        self.assertEqual(drawdown_risk({"A": 0.1}, [{"A": -0.02}] * 50), 0.0)

    def test_same_seed_same_answer(self):
        rows = [{"A": 0.05}, {"A": -0.06}, {"A": 0.01}] * 20
        self.assertEqual(drawdown_risk({"A": 1.0}, rows, seed=3), drawdown_risk({"A": 1.0}, rows, seed=3))

    def test_empty_portfolio_has_no_risk(self):
        self.assertEqual(drawdown_risk({}, [{"A": -0.5}] * 10), 0.0)


if __name__ == "__main__":
    unittest.main()
