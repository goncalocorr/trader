import unittest

from agente.sim import ratios, simulate

UP = [(1.0, 1.02, 1.0, 1.02)]      # every bar +2%, never dips
DOWN = [(1.0, 1.0, 0.98, 0.98)]    # every bar -2%, never rises
BOTH = [(1.0, 1.10, 0.90, 1.0)]    # touches stop and target in the same bar


class MonteCarlo(unittest.TestCase):
    def test_rising_market_hits_target(self):
        r = simulate(UP, entry=100, stop=95, target=110, horizon=20, cost=0)
        self.assertEqual(r["p_target"], 1.0)
        self.assertAlmostEqual(r["ev_r"], 2.0)

    def test_falling_market_hits_stop(self):
        r = simulate(DOWN, entry=100, stop=95, target=110, horizon=20, cost=0)
        self.assertEqual(r["p_stop"], 1.0)
        self.assertAlmostEqual(r["ev_r"], -1.0)

    def test_stop_checked_before_target(self):
        self.assertEqual(simulate(BOTH, 100, 95, 105, 5, cost=0)["p_stop"], 1.0)

    def test_gap_through_stop_loses_more_than_1r(self):
        gap = [(0.9, 0.9, 0.9, 0.9)]
        self.assertAlmostEqual(simulate(gap, 100, 95, 110, 5, cost=0)["ev_r"], -2.0)

    def test_horizon_exit_counts_partial_r(self):
        r = simulate(UP, entry=100, stop=95, target=200, horizon=1, cost=0)
        self.assertEqual(r["p_neither"], 1.0)
        self.assertAlmostEqual(r["ev_r"], 0.4)  # +2 on a 5 risk

    def test_costs_reduce_expectancy_in_r(self):
        r = simulate(UP, entry=100, stop=95, target=110, horizon=20, cost=0.005)
        self.assertAlmostEqual(r["ev_r"], 2.0 - 0.1)

    def test_same_seed_same_result(self):
        pool = UP + DOWN + BOTH
        self.assertEqual(simulate(pool, 100, 95, 110, 30, seed=7),
                         simulate(pool, 100, 95, 110, 30, seed=7))

    def test_ratios_relative_to_previous_close(self):
        bars = [(0, 10, 10, 10, 10, 1), (1, 10, 11, 9, 10.5, 1)]
        self.assertEqual(ratios(bars), [(1.0, 1.1, 0.9, 1.05)])


if __name__ == "__main__":
    unittest.main()
