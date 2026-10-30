"""Paper broker: simulated fills with fees and slippage. Never talks to a real exchange."""

from agente.risk import MAX_DRAWDOWN

FEE = 0.001     # per side (Binance spot taker)
SLIP = 0.0005   # per side
MAX_BARS = 30   # time exit: 30 bars of 4h = 5 days
DAY_MS = 86_400_000


def new_account(capital):
    return {"cash": capital, "equity": capital, "peak": capital, "day": 0, "day_start": capital,
            "positions": {}, "halted": False, "trades": []}


def open_position(acc, sym, qty, price, stop, target, t):
    fill = price * (1 + SLIP)
    acc["cash"] -= fill * qty * (1 + FEE)
    acc["positions"][sym] = {"qty": qty, "entry": fill, "stop": stop, "target": target,
                             "opened": t, "bars": 0}


def _close(acc, sym, price, reason, t):
    pos = acc["positions"].pop(sym)
    fill = price * (1 - SLIP)
    acc["cash"] += fill * pos["qty"] * (1 - FEE)
    pnl = (fill * (1 - FEE) - pos["entry"] * (1 + FEE)) * pos["qty"]
    trade = {"symbol": sym, "opened": pos["opened"], "closed": t, "entry": pos["entry"], "exit": fill,
             "qty": pos["qty"], "pnl": pnl, "r": pnl / ((pos["entry"] - pos["stop"]) * pos["qty"]),
             "exit_reason": reason}
    acc["trades"].append(trade)
    return trade


def on_bar(acc, sym, bar):
    """Manage an open position with a new closed bar (t, o, h, l, c, v). Returns the closed trade or None."""
    pos = acc["positions"].get(sym)
    if not pos:
        return None
    t, o, h, l, c = bar[:5]
    pos["bars"] += 1
    if l <= pos["stop"]:  # stop first; a gap below the stop fills at the open
        return _close(acc, sym, min(o, pos["stop"]), "stop", t)
    if h >= pos["target"]:
        return _close(acc, sym, max(o, pos["target"]), "alvo", t)
    if pos["bars"] >= MAX_BARS:
        return _close(acc, sym, c, "tempo", t)
    return None


def mark(acc, prices, t):
    """Mark to market; roll the trading day (UTC); halt on max drawdown."""
    acc["equity"] = acc["cash"] + sum(p["qty"] * prices[s] for s, p in acc["positions"].items())
    acc["peak"] = max(acc["peak"], acc["equity"])
    if t // DAY_MS != acc["day"]:
        acc["day"], acc["day_start"] = t // DAY_MS, acc["equity"]
    if acc["equity"] <= acc["peak"] * (1 - MAX_DRAWDOWN):
        acc["halted"] = True
