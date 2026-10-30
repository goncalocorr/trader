"""Monte Carlo "time machine": replay the next 30 days of the portfolio many times."""

import random


def drawdown_risk(weights, rows, horizon=30, limit=0.25, replays=500, seed=19):
    """Probability that the portfolio falls `limit` from its peak within `horizon` days.

    rows: past days as {symbol: daily return}; whole days are drawn so coins keep moving together.
    ponytail: i.i.d. day bootstrap; ignores volatility clustering. Block bootstrap if it looks too calm.
    """
    if not weights or not rows:
        return 0.0
    rng = random.Random(seed)
    hits = 0
    for _ in range(replays):
        equity = peak = 1.0
        for _ in range(horizon):
            day = rng.choice(rows)
            equity *= 1 + sum(w * day.get(s, 0.0) for s, w in weights.items())
            peak = max(peak, equity)
            if 1 - equity / peak >= limit:
                hits += 1
                break
    return hits / replays
