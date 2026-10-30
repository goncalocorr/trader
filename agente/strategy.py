"""Scout + Charts (breakout signal) and Skeptic (veto). bars: (t, o, h, l, c, v), oldest first."""

import math

LOOKBACK = 20      # breakout over the previous 20 bars' highs
TREND = 100        # close must be above this simple moving average
ATR_N = 14
STOP_ATR = 2.0     # stop = entry - 2 ATR
R_TARGET = 2.0     # target = 2x the risk
VOL_SPIKE = 1.5    # Scout: volume at least 1.5x its 20-bar average
MIN_EDGE = 0.05    # Skeptic: skip when Monte Carlo expectancy (net of costs) is below this, in R


def atr(bars, n=ATR_N):
    tr = [max(b[2], a[4]) - min(b[3], a[4]) for a, b in zip(bars[-n - 1:], bars[-n:])]
    return sum(tr) / len(tr)


def signal(bars):
    if len(bars) < TREND + 1:
        return None
    last, prev = bars[-1], bars[-LOOKBACK - 1:-1]
    close = last[4]
    if last[5] < VOL_SPIKE * sum(b[5] for b in prev) / LOOKBACK:
        return None  # Scout: nothing unusual
    if close <= max(b[2] for b in prev) or close <= sum(b[4] for b in bars[-TREND:]) / TREND:
        return None  # Charts: no breakout in an uptrend
    a = atr(bars)
    stop = close - STOP_ATR * a
    if stop <= 0:
        return None
    return {"entry": close, "stop": stop, "target": close + R_TARGET * (close - stop), "atr": a}


def skeptic(p, last_bar, mc):
    """Returns (verdict, reason): 'comprar', 'esperar' or 'saltar'."""
    if mc["ev_r"] < MIN_EDGE:
        return "saltar", f"expectativa fraca ({mc['ev_r']:+.2f}R depois de custos)"
    step = 10 ** math.floor(math.log10(p["stop"])) / 2
    round_level = math.ceil(p["stop"] / step) * step
    if (round_level - p["stop"]) / p["stop"] < 0.005:
        return "saltar", f"stop logo abaixo do número redondo {round_level:g}, onde os stops são caçados"
    if last_bar[2] - last_bar[3] > 3 * p["atr"]:
        return "esperar", "vela esticada, seria perseguir o preço"
    return "comprar", f"setup limpo, expectativa {mc['ev_r']:+.2f}R"
