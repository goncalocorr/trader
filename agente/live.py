"""Live PAPER trading: process bars closed since the last run, then save. Run every 4h (or more often).

    python -m agente.live            # one tick
    python -m agente.live --estado   # show the account, no trading
    python -m agente.live --ok       # owner's OK to resume after a drawdown halt
"""

import argparse
import datetime
import json
import os
import time

from agente import data, paper
from agente.backtest import UNIVERSE
from agente.desk import decide
from agente.strategy import REGIME_N

STATE_DIR = os.path.join(os.path.dirname(data.DIR), "state")
ACCOUNT = os.path.join(STATE_DIR, "paper.json")
LOG = os.path.join(STATE_DIR, "sinais.jsonl")
CAPITAL = 25.0  # USDT (~EUR); prices are USDT pairs
STALE_MS = 3 * 4 * 3_600_000  # newest closed 4h bar older than 12h = stale


def tick(acc, series, now_ms=None):
    """Process only bars newer than acc['last_t'], in time order across symbols.

    First sight of a symbol just bookmarks it. Stale series are skipped (fail closed).
    """
    marks = acc.setdefault("last_t", {})
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    prices, events = {}, []
    for s, bs in series.items():
        if not bs or now_ms - bs[-1][0] > STALE_MS:
            print(f"{s}: dados desatualizados ou em falta, não opero")
            continue
        if s not in marks:
            marks[s] = bs[-1][0]
        prices[s] = next((b[4] for b in reversed(bs) if b[0] <= marks[s]), bs[0][4])
        events += [(b[0], s, i) for i, b in enumerate(bs) if b[0] > marks[s]]
    records = []
    for t, s, i in sorted(events):
        bs = series[s]
        paper.on_bar(acc, s, bs[i])
        prices[s] = bs[i][4]
        paper.mark(acc, prices, t)
        if s not in acc["positions"]:
            btc = [b for b in series.get("BTCUSDT", [])[-REGIME_N - 50:] if b[0] <= t][-REGIME_N - 1:]
            rec = decide(acc, s, bs[max(0, i - 600):i + 1], btc=btc)
            if rec:
                records.append(rec)
        marks[s] = t
    if prices:
        paper.mark(acc, prices, max(marks.values()))
    return records


def resume(acc):
    """Owner's OK after a drawdown halt: resume and measure the next drawdown from here."""
    acc["halted"], acc["peak"] = False, acc["equity"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estado", action="store_true")
    ap.add_argument("--ok", action="store_true", help="o dono autoriza retomar depois de uma paragem por drawdown")
    a = ap.parse_args()
    os.makedirs(STATE_DIR, exist_ok=True)
    acc = paper.new_account(CAPITAL)
    if os.path.exists(ACCOUNT):
        with open(ACCOUNT, encoding="utf-8") as fh:
            acc = json.load(fh)
    if a.ok and acc["halted"]:
        resume(acc)
        print("Retomado com o teu OK.")
    if not a.estado:
        n_trades = len(acc["trades"])
        records = tick(acc, {s: data.bars(s) for s in UNIVERSE})
        with open(LOG, "a", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            for t in acc["trades"][n_trades:]:
                fh.write(json.dumps({"fecho": t}, ensure_ascii=False) + "\n")
        tmp = ACCOUNT + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(acc, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, ACCOUNT)
        for r in records:
            print(f"{r['symbol']}: Skeptic {r['skeptic']} ({r['reason']})"
                  + (f", risk gate: {r['risk']['reason']}" if r["risk"] else ""))
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[{now}] capital {acc['equity']:.2f} USDT ({acc['equity'] / CAPITAL - 1:+.1%}), "
          f"posições {list(acc['positions'])}, trades fechados {len(acc['trades'])}"
          + (", PARADO por drawdown: precisa do teu OK" if acc["halted"] else ""))


if __name__ == "__main__":
    main()
