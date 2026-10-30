"""Risk gate: deterministic limits. No LLM can bypass this."""

RISK_CAP = 0.02      # max fraction of equity lost if the stop is hit
DAILY_LOSS = 0.05    # stop trading for the day after losing this fraction
MAX_DRAWDOWN = 0.25  # halt until the owner says OK
MIN_NOTIONAL = 5.0   # exchange minimum order value (USDT)
HEAT_CAP = 0.06      # max total equity at risk across open positions (crypto moves together)
COST_BUFFER = 1.002  # entry slippage + fee, so a full-cash order never overdraws


def _no(reason):
    return {"ok": False, "reason": reason, "qty": 0.0, "risk_frac": 0.0}


def check(account, p):
    entry, stop, target = p["entry"], p.get("stop"), p["target"]
    if stop is None or not 0 < stop < entry:
        return _no("stop em falta ou acima da entrada")
    if target <= entry:
        return _no("alvo abaixo da entrada")
    if p["ev_r"] <= 0:
        return _no("expectativa não positiva")
    if account.get("halted"):
        return _no("sistema parado, à espera de OK")
    eq = account["equity"]
    if eq <= account["peak"] * (1 - MAX_DRAWDOWN):
        return _no("drawdown máximo atingido")
    if eq <= account["day_start"] * (1 - DAILY_LOSS):
        return _no("perda diária máxima atingida")
    if p["symbol"] in account["positions"]:
        return _no("já existe posição neste ativo")

    r_multiple = (target - entry) / (entry - stop)
    # Binary Kelly: f* = p - q/R = EV/R (fraction of equity at risk). Half Kelly, capped.
    risk_frac = min(p["ev_r"] / r_multiple / 2, RISK_CAP)
    open_risk = sum((q["entry"] - q["stop"]) * q["qty"] for q in account["positions"].values())
    risk_frac = min(risk_frac, HEAT_CAP - open_risk / eq)
    if risk_frac <= 0:
        return _no("risco total aberto no máximo")
    qty = eq * risk_frac / (entry - stop)
    qty = min(qty, account["cash"] / (entry * COST_BUFFER))  # no leverage
    if qty * entry < MIN_NOTIONAL:
        return _no("ordem abaixo do mínimo da exchange")
    return {"ok": True, "reason": "aprovado", "qty": qty, "risk_frac": risk_frac}
