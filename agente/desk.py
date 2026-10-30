"""The trading desk: Scout/Charts -> Monte Carlo -> Skeptic -> Risk gate -> paper order.

One path for both backtest and live paper, so the backtest tests the real thing.
"""

from agente import paper
from agente.risk import check
from agente.sim import ratios, simulate
from agente.strategy import regime_ok, signal, skeptic

POOL = 500  # Monte Carlo draws from the last 500 bars (~83 days of 4h)


def decide(acc, sym, bars, btc=None):
    """Evaluate the latest closed bar. Returns an audit record, or None when there is no signal.

    btc: BTC bars up to the same close, for the regime filter (None skips the filter).
    """
    if btc is not None and not regime_ok(btc):
        return None
    p = signal(bars)
    if not p:
        return None
    mc = simulate(ratios(bars[-POOL - 1:]), p["entry"], p["stop"], p["target"], paper.MAX_BARS,
                  cost=2 * (paper.FEE + paper.SLIP))
    verdict, why = skeptic(p, bars[-1], mc)
    rec = {"t": bars[-1][0], "symbol": sym, "signal": p, "mc": mc, "skeptic": verdict,
           "reason": why, "risk": None}
    if verdict == "comprar":
        rec["risk"] = check(acc, {**p, "symbol": sym, "ev_r": mc["ev_r"]})
        if rec["risk"]["ok"]:
            paper.open_position(acc, sym, rec["risk"]["qty"], p["entry"], p["stop"], p["target"], rec["t"])
    return rec
