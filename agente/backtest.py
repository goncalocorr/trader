"""Walk-forward backtest over real daily history, through the same desk the live agent uses.

    python -m agente.backtest                          # 100 USDT, default universe, since 2018
    python -m agente.backtest --start 2024-01-01 --retomar
"""

import argparse
import datetime
import math
import statistics

from agente import data, paper
from agente.desk import MIN_HISTORY, decide, window

UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "LINKUSDT"]
INTERVAL = "1d"


def run(series, capital, since_ms=0, until_ms=None, resume=False):
    """No lookahead: each day's decision only sees closes up to that day.

    resume=True simulates the owner saying OK after each drawdown halt (counted in acc["halts"]).
    """
    if "BTCUSDT" not in series:
        raise SystemExit("BTCUSDT é obrigatório: é a referência do regime e do calendário.")
    acc = paper.new_account(capital)
    acc["halts"] = 0
    curve, records = [], []
    for b in series["BTCUSDT"]:
        t = b[0]
        if t < since_ms or (until_ms is not None and t >= until_ms):
            continue
        rec = decide(acc, window(series, t, min_n=MIN_HISTORY), t)
        records.append(rec)
        curve.append((t, acc["equity"], sum(q * acc["px"][s] for s, q in acc["positions"].items())))
        if acc["halted"]:
            acc["halts"] += 1
            if not resume:
                break
            acc["halted"], acc["peak"] = False, acc["equity"]
    return acc, curve, records


def report(acc, curve, records, capital):
    if not curve:
        print("Sem dados no período pedido.")
        return
    eq = [e for _, e, _ in curve]
    peak, mdd = eq[0], 0.0
    for e in eq:
        peak = max(peak, e)
        mdd = max(mdd, 1 - e / peak)
    rets = [b / a - 1 for a, b in zip(eq, eq[1:])]
    sd = statistics.stdev(rets) if len(rets) > 1 else 0.0
    sharpe = statistics.mean(rets) / sd * math.sqrt(365) if sd else 0.0
    years = (curve[-1][0] - curve[0][0]) / paper.DAY_MS / 365
    fills = [f for r in records for f in r["fills"]]
    exposure = statistics.mean(inv / e for _, e, inv in curve if e > 0)
    fmt = lambda t: datetime.datetime.fromtimestamp(t / 1000, datetime.timezone.utc).date()
    print(f"Período:          {fmt(curve[0][0])} a {fmt(curve[-1][0])} ({years:.1f} anos)")
    print(f"Capital:          {capital:.2f} -> {acc['equity']:.2f} USDT ({acc['equity'] / capital - 1:+.1%})")
    if years > 0 and acc["equity"] > 0:
        print(f"Por ano (CAGR):   {(acc['equity'] / capital) ** (1 / years) - 1:+.1%}")
    print(f"Drawdown máximo:  {mdd:.1%}")
    print(f"Sharpe (diário):  {sharpe:.2f}")
    print(f"Exposição média:  {exposure:.0%} investido")
    print(f"Ordens:           {len(fills)} ({len(fills) / max(years, 1e-9):.0f} por ano)")
    print(f"Skeptic travou:   {sum(len(r['skeptic']) for r in records)} reforços")
    if acc["halts"]:
        print(f"Paragens por drawdown de 25%: {acc['halts']}" + ("  (parou aqui)" if acc["halted"] else "  (retomado com OK simulado)"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capital", type=float, default=100.0)
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--fim", default=None)
    ap.add_argument("--symbols", default=",".join(UNIVERSE))
    ap.add_argument("--retomar", action="store_true", help="simula o OK do dono após cada paragem")
    a = ap.parse_args()
    ms = lambda d: int(datetime.datetime.fromisoformat(d + "+00:00").timestamp() * 1000)
    series = {s: data.bars(s, INTERVAL) for s in a.symbols.split(",")}
    since, until = ms(a.start), (ms(a.fim) if a.fim else None)
    acc, curve, records = run(series, a.capital, since, until, resume=a.retomar)
    report(acc, curve, records, a.capital)
    btc = [b for b in series["BTCUSDT"] if b[0] >= since and (until is None or b[0] < until)]
    if btc:
        print(f"Referência:       comprar BTC e esperar = {btc[-1][4] / btc[0][4] - 1:+.1%}")


if __name__ == "__main__":
    main()
