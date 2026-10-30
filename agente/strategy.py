"""Momentum rotation: of the coins above their 50-day average, hold the one that rose most over 50 days,
only while BTC is above its 200-day average, with exposure scaled to a 20% yearly volatility.
Skeptic: no buying into a spike.

closes: {symbol: [daily closes, oldest first]}, every list ending on the same day.
"""

import math
import statistics

SMA_N = 50         # coin trend: close above its 50-day average
REGIME_N = 200     # market regime: BTC close above its 200-day average
VOL_TARGET = 0.20  # yearly volatility target (chosen on 2018-2023 data with an out-of-sample margin)
VOL_N = 30         # days used to estimate volatility
SPIKE_SIGMA = 4.0  # Skeptic: a daily move this many standard deviations from normal is a spike
SPIKE_FLOOR = 0.05


def above_average(closes, n):
    return len(closes) > n and closes[-1] > sum(closes[-n - 1:-1]) / n


def regime_ok(btc):
    return above_average(btc, REGIME_N)


def _returns(closes, n):
    return [b / a - 1 for a, b in zip(closes[-n - 1:-1], closes[-n:])]


def target_weights(closes, btc):
    if not regime_ok(btc):
        return {}
    chosen = [s for s, c in closes.items() if len(c) > VOL_N and above_average(c, SMA_N)]
    if not chosen:
        return {}
    w = 1 / len(chosen)
    daily = [sum(w * r for r in day) for day in zip(*(_returns(closes[s], VOL_N) for s in chosen))]
    vol = statistics.pstdev(daily) * math.sqrt(365)
    k = min(1.0, VOL_TARGET / vol) if vol > 0 else 1.0
    # With 25 USDT and a 5 USDT order minimum only one position fits: put the whole exposure in the
    # coin that rose most over SMA_N days. ponytail: exposure is sized on the basket's volatility (the
    # tested version), so one coin runs hotter than 20%; size on that coin's own vol if drawdowns bite.
    best = max(chosen, key=lambda s: closes[s][-1] / closes[s][-SMA_N - 1])
    return {best: k}


def skeptic(closes, current, target):
    """Hold back increases in coins whose last daily move is abnormal. Returns (weights, reasons)."""
    out, why = dict(target), {}
    for s, w in target.items():
        if w <= current.get(s, 0) or len(closes[s]) <= VOL_N + 1:
            continue
        r = _returns(closes[s], VOL_N + 1)
        last, past = r[-1], r[:-1]
        if abs(last - statistics.mean(past)) > max(SPIKE_SIGMA * statistics.pstdev(past), SPIKE_FLOOR):
            out[s] = current.get(s, 0)
            why[s] = f"movimento anormal de {last:+.1%} num dia: não reforço hoje"
    return {s: w for s, w in out.items() if w > 0}, why
