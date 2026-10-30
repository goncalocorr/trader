"""Risk gate: deterministic limits on target weights. No LLM can bypass this."""

DAILY_LOSS = 0.05    # after losing this much today: only reduce positions
MAX_DRAWDOWN = 0.25  # all to cash and halt until the owner says OK
MAX_WEIGHT = 0.5     # no single coin above half the account
MIN_NOTIONAL = 5.0   # exchange minimum order value (USDT)
COST_BUFFER = 1.002  # leave room for fees and slippage: never spend more than the cash


def check_weights(account, target, current):
    """Returns (weights, reason)."""
    if account.get("halted"):
        return {}, "sistema parado, à espera de OK: tudo em dinheiro"
    eq = account["equity"]
    if eq <= account["peak"] * (1 - MAX_DRAWDOWN):
        return {}, "drawdown máximo atingido: tudo em dinheiro"
    w = {s: min(x, MAX_WEIGHT) for s, x in target.items() if x > 0}
    reason = "aprovado"
    if eq <= account["day_start"] * (1 - DAILY_LOSS):
        w = {s: min(x, current.get(s, 0.0)) for s, x in w.items()}
        w = {s: x for s, x in w.items() if x > 0}
        reason = "perda diária máxima atingida: só reduz posições"
    total, cap = sum(w.values()), 1 / COST_BUFFER
    if total > cap:
        w = {s: x * cap / total for s, x in w.items()}
    return w, reason
