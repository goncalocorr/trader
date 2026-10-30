"""The trading desk, once a day: Charts (momentum targets) -> Skeptic -> Monte Carlo -> Risk gate -> paper.

One path for both backtest and live paper, so the backtest tests the real thing.
"""

import bisect
import math

from agente import paper
from agente.risk import check_weights
from agente.sim import drawdown_risk
from agente.strategy import SMA_N, regime_ok, skeptic, target_weights

MC_DAYS = 365        # Monte Carlo draws whole days from the last year
MAX_BREACH_P = 0.05  # scale down until P(25% drawdown within 30 days) <= 5%
MIN_SCALE = 0.25
MIN_HISTORY = SMA_N + 1  # a coin needs this many days of history before it can be held
MAX_GAP = 3 * paper.DAY_MS  # an exchange outage of a day or two does not break the history
DAY = paper.DAY_MS


def window(series, t, n=MC_DAYS + 1, min_n=None):
    """{symbol: last up-to-n daily closes ending at t}. Coins without a bar at t, with a non-positive
    price, or with fewer than min_n bars since a gap longer than MAX_GAP, are left out (fail closed)."""
    min_n = n if min_n is None else min_n
    out = {}
    for s, bs in series.items():
        i = bisect.bisect_right(bs, (t, math.inf)) - 1
        if i < 0 or bs[i][0] != t:
            continue
        j = i
        while j > 0 and i - j + 1 < n and bs[j][0] - bs[j - 1][0] <= MAX_GAP:
            j -= 1
        closes = [b[4] for b in bs[j:i + 1]]
        if len(closes) >= min_n and min(closes) > 0:
            out[s] = closes
    return out


def decide(acc, closes, t):
    """Rebalance the paper account at the close of day t. Returns the audit record."""
    prices = {s: c[-1] for s, c in closes.items()}
    paper.mark(acc, prices, t)
    eq = acc["equity"]
    current = {s: q * acc["px"][s] / eq for s, q in acc["positions"].items()}
    btc = closes.get("BTCUSDT", [])

    target = target_weights(closes, btc)
    target, doubts = skeptic(closes, current, target)

    days = min((len(closes[s]) for s in target), default=1) - 1
    rows = [{s: closes[s][-i] / closes[s][-i - 1] - 1 for s in target} for i in range(1, min(days, MC_DAYS) + 1)]
    scale = 1.0
    p = drawdown_risk(target, rows)
    while p > MAX_BREACH_P and scale * 0.8 >= MIN_SCALE:
        scale *= 0.8
        p = drawdown_risk({s: w * scale for s, w in target.items()}, rows)
    target = {s: w * scale for s, w in target.items()}

    weights, reason = check_weights(acc, target, current)
    fills = paper.rebalance(acc, weights, prices, t)
    paper.mark(acc, prices, t)
    return {"t": t, "regime": regime_ok(btc), "target": weights, "skeptic": doubts,
            "mc": {"p_queda_25": p, "escala": scale}, "risk": reason, "fills": fills,
            "equity": acc["equity"]}
