"""Paper broker: simulated fills with fees and slippage. Never talks to a real exchange."""

from agente.risk import MAX_DRAWDOWN, MIN_NOTIONAL

FEE = 0.001     # per side (Binance spot taker)
SLIP = 0.0005   # per side
DAY_MS = 86_400_000
VERSION = 2     # account format; older state files are replaced by a fresh account


def new_account(capital):
    return {"v": VERSION, "cash": capital, "equity": capital, "peak": capital, "day": 0,
            "day_start": capital, "positions": {}, "px": {}, "halted": False}


def mark(acc, prices, t):
    """Mark to market (last known price for coins without a new one); roll the UTC day; halt on max drawdown."""
    if t // DAY_MS != acc["day"]:  # a new day starts from the previous close, before today's move
        acc["day"], acc["day_start"] = t // DAY_MS, acc["equity"]
    acc["px"].update(prices)
    acc["equity"] = acc["cash"] + sum(q * acc["px"][s] for s, q in acc["positions"].items())
    acc["peak"] = max(acc["peak"], acc["equity"])
    if acc["equity"] <= acc["peak"] * (1 - MAX_DRAWDOWN):
        acc["halted"] = True


def rebalance(acc, weights, prices, t):
    """Trade toward target weights of equity. Sells first, then buys. Orders under the exchange
    minimum are skipped, except a full exit. Returns the fills."""
    eq = acc["cash"] + sum(q * prices.get(s, acc["px"].get(s, 0.0)) for s, q in acc["positions"].items())
    fills = []
    for s, q in list(acc["positions"].items()):
        if s not in prices:
            continue  # no fresh price: do not trade it today
        want = weights.get(s, 0.0)
        delta = want * eq - q * prices[s]
        if delta >= 0 or (want > 0 and -delta < MIN_NOTIONAL):
            continue
        sell = q if want == 0 else -delta / prices[s]
        px = prices[s] * (1 - SLIP)
        acc["cash"] += sell * px * (1 - FEE)
        if want == 0:
            del acc["positions"][s]
        else:
            acc["positions"][s] = q - sell
        fills.append({"t": t, "symbol": s, "lado": "venda", "qty": sell, "preco": px})
    for s, want in weights.items():
        delta = want * eq - acc["positions"].get(s, 0.0) * prices[s]
        spend = min(delta, acc["cash"])
        if spend < MIN_NOTIONAL:
            continue
        px = prices[s] * (1 + SLIP)
        qty = spend / (px * (1 + FEE))
        acc["cash"] -= spend
        acc["positions"][s] = acc["positions"].get(s, 0.0) + qty
        fills.append({"t": t, "symbol": s, "lado": "compra", "qty": qty, "preco": px})
    return fills
