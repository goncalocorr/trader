"""Monte Carlo "time machine": replay the trade many times from the asset's own past bars."""

import random


def ratios(bars):
    """Each bar as (open, high, low, close) / previous close. bars: (t, o, h, l, c, v)."""
    return [(b[1] / a[4], b[2] / a[4], b[3] / a[4], b[4] / a[4]) for a, b in zip(bars, bars[1:])]


def simulate(pool, entry, stop, target, horizon, replays=2000, seed=19, cost=0.004):
    """Long trade. cost = round-trip fees + slippage as a fraction of price.

    ponytail: i.i.d. bootstrap of bars; ignores volatility clustering and news.
    Upgrade path: block bootstrap if results look too smooth vs. real fills.
    """
    rng = random.Random(seed)
    risk = entry - stop
    hits = {"target": 0, "stop": 0, "neither": 0}
    total_r = 0.0
    for _ in range(replays):
        price = entry
        for _ in range(horizon):
            o, h, l, c = rng.choice(pool)
            if price * l <= stop:  # stop first: a bar touching both counts as a loss
                hits["stop"] += 1
                total_r += (min(price * o, stop) - entry) / risk  # a gap below the stop loses more than 1R
                break
            if price * h >= target:
                hits["target"] += 1
                total_r += (target - entry) / risk
                break
            price *= c
        else:
            hits["neither"] += 1
            total_r += (price - entry) / risk
    return {
        "p_target": hits["target"] / replays,
        "p_stop": hits["stop"] / replays,
        "p_neither": hits["neither"] / replays,
        "ev_r": total_r / replays - cost * entry / risk,
    }
