"""Walk-forward backtest over real history, through the same desk the live agent uses.

    python -m agente.backtest                 # 25 USDT (~EUR), default universe, since 2018
    python -m agente.backtest --start 2022-01-01 --capital 25
"""

import argparse
import datetime
import math
import statistics

from agente import data, paper
from agente.desk import decide
from agente.strategy import REGIME_N

UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "LINKUSDT"]


def run(series, capital, since_ms=0, resume=False, until_ms=None):
    """series: {symbol: bars}. No lookahead: each decision only sees bars up to that close.

    resume=True simulates the owner saying OK after each drawdown halt (counted in acc["halts"]).
    """
    acc = paper.new_account(capital)
    acc["halts"] = 0
    idx = {s: {b[0]: i for i, b in enumerate(bs)} for s, bs in series.items()}
    times = sorted({t for bs in series.values() for b in bs for t in [b[0]] if t >= since_ms and (until_ms is None or t < until_ms)})
    last = {}
    curve, records = [], []
    for t in times:
        here = [(s, idx[s][t]) for s in series if t in idx[s]]
        for s, i in here:
            paper.on_bar(acc, s, series[s][i])
            last[s] = series[s][i][4]
        paper.mark(acc, last, t)
        curve.append((t, acc["equity"]))
        if acc["halted"]:
            acc["halts"] += 1
            if not resume:
                break
            acc["halted"], acc["peak"] = False, acc["equity"]
        for s, i in here:
            if s not in acc["positions"]:
                b = idx["BTCUSDT"].get(t) if "BTCUSDT" in idx else None
                btc = series["BTCUSDT"][max(0, b - REGIME_N):b + 1] if b is not None else []
                rec = decide(acc, s, series[s][max(0, i - 600):i + 1], btc=btc)
                if rec:
                    records.append(rec)
                    paper.mark(acc, last, t)
    return acc, curve, records


def report(acc, curve, records, capital):
    if not curve:
        print("Sem dados no período pedido.")
        return
    tr = acc["trades"]
    eq = [e for _, e in curve]
    peak, mdd = eq[0], 0.0
    for e in eq:
        peak = max(peak, e)
        mdd = max(mdd, 1 - e / peak)
    daily = {}
    for t, e in curve:
        daily[t // paper.DAY_MS] = e
    d = list(daily.values())
    rets = [b / a - 1 for a, b in zip(d, d[1:])]
    sharpe = statistics.mean(rets) / statistics.stdev(rets) * math.sqrt(365) if len(rets) > 1 and statistics.stdev(rets) else 0.0
    years = (curve[-1][0] - curve[0][0]) / paper.DAY_MS / 365
    wins = [x for x in tr if x["pnl"] > 0]
    verdicts = {v: sum(r["skeptic"] == v for r in records) for v in ("comprar", "esperar", "saltar")}
    fmt = lambda t: datetime.datetime.fromtimestamp(t / 1000, datetime.timezone.utc).date()
    print(f"Período:          {fmt(curve[0][0])} a {fmt(curve[-1][0])} ({years:.1f} anos)")
    print(f"Capital:          {capital:.2f} -> {acc['equity']:.2f} USDT ({acc['equity'] / capital - 1:+.1%})")
    if years > 0 and acc["equity"] > 0:
        print(f"Por ano (CAGR):   {(acc['equity'] / capital) ** (1 / years) - 1:+.1%}")
    print(f"Trades:           {len(tr)}  (sinais {len(records)}; Skeptic: {verdicts})")
    if tr:
        print(f"Win rate:         {len(wins) / len(tr):.1%}")
        print(f"Expectativa:      {statistics.mean(x['r'] for x in tr):+.3f}R por trade")
        print(f"Saídas:           { {k: sum(x['exit_reason'] == k for x in tr) for k in ('alvo', 'stop', 'tempo')} }")
    print(f"Drawdown máximo:  {mdd:.1%}")
    print(f"Sharpe (diário):  {sharpe:.2f}")
    if acc["halts"]:
        print(f"Paragens por drawdown de 25%: {acc['halts']}" + ("  (parou aqui)" if acc["halted"] else "  (retomado com OK simulado)"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capital", type=float, default=25.0)
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--symbols", default=",".join(UNIVERSE))
    ap.add_argument("--retomar", action="store_true", help="simula o OK do dono após cada paragem")
    a = ap.parse_args()
    series = {s: data.bars(s) for s in a.symbols.split(",")}
    since = int(datetime.datetime.fromisoformat(a.start + "+00:00").timestamp() * 1000)
    acc, curve, records = run(series, a.capital, since, resume=a.retomar)
    report(acc, curve, records, a.capital)
    btc = series.get("BTCUSDT")
    if btc:
        first = next(b[4] for b in btc if b[0] >= since)
        print(f"Referência:       comprar BTC e esperar = {btc[-1][4] / first - 1:+.1%}")


if __name__ == "__main__":
    main()
