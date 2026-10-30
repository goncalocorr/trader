"""Live PAPER trading, once a day after the daily close: process days closed since the last run, then save.

    python -m agente.live            # one run
    python -m agente.live --estado   # show the account, no trading
    python -m agente.live --ok       # owner's OK to resume after a drawdown halt
"""

import argparse
import datetime
import json
import os
import time

from agente import data, paper
from agente.backtest import INTERVAL, UNIVERSE
from agente.desk import MIN_HISTORY, decide, window

STATE_DIR = os.path.join(os.path.dirname(data.DIR), "state")
ACCOUNT = os.path.join(STATE_DIR, "paper.json")
LOG = os.path.join(STATE_DIR, "sinais.jsonl")
CAPITAL = 100.0  # USDT (~90 EUR): below ~100 the 5 USDT order minimum leaves the strategy idle
STALE_MS = 2 * paper.DAY_MS  # newest closed daily bar older than 2 days = stale


def tick(acc, series, now_ms=None):
    """Decide on the latest daily close newer than acc['last_t']. First run only bookmarks.
    Stale BTC data (the regime reference) means no trading at all (fail closed)."""
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    btc = series.get("BTCUSDT") or []
    if not btc or now_ms - btc[-1][0] > STALE_MS:
        print("BTCUSDT: dados desatualizados ou em falta, não opero")
        return []
    if "last_t" not in acc:
        acc["last_t"] = btc[-1][0]
        return []
    new = [b[0] for b in btc if b[0] > acc["last_t"]]
    if not new:
        return []
    if len(new) > 1:  # never trade at past closes: only the latest one is a price we could get now
        print(f"{len(new) - 1} fecho(s) falhado(s): decido só com o mais recente")
    acc["last_t"] = new[-1]
    return [decide(acc, window(series, new[-1], min_n=MIN_HISTORY), new[-1])]


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
            saved = json.load(fh)
        if saved.get("v") == paper.VERSION:
            acc = saved
        else:
            print(f"Estado antigo de outra estratégia: conta paper reiniciada com {CAPITAL:.0f} USDT.")
    if a.ok and acc["halted"]:
        resume(acc)
        print("Retomado com o teu OK.")
    if not a.estado:
        records = tick(acc, {s: data.bars(s, INTERVAL) for s in UNIVERSE})
        with open(LOG, "a", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        tmp = ACCOUNT + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(acc, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, ACCOUNT)
        for r in records:
            day = datetime.datetime.fromtimestamp(r["t"] / 1000, datetime.timezone.utc).date()
            alvo = ", ".join(f"{s} {w:.0%}" for s, w in r["target"].items()) or "tudo em dinheiro"
            print(f"{day}: regime {'ligado' if r['regime'] else 'desligado'} | alvo: {alvo} | "
                  f"ordens {len(r['fills'])} | risk gate: {r['risk']}"
                  + "".join(f" | Skeptic {s}: {m}" for s, m in r["skeptic"].items()))
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pos = {s: round(q * acc["px"][s], 2) for s, q in acc["positions"].items()}
    print(f"[{now}] capital {acc['equity']:.2f} USDT ({acc['equity'] / CAPITAL - 1:+.1%}), "
          f"dinheiro {acc['cash']:.2f}, posições {pos}"
          + (", PARADO por drawdown: precisa do teu OK" if acc["halted"] else ""))


if __name__ == "__main__":
    main()
