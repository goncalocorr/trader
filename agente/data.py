"""Public market data from Binance's market-data-only endpoint. No API key."""

import csv
import datetime
import json
import os
import time
import urllib.request

URL = "https://data-api.binance.vision/api/v3/klines?symbol={s}&interval={i}&limit=1000&startTime={t}"
DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return json.load(r)
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def bars(symbol, interval="4h", start="2018-01-01"):
    """Closed bars (t_ms, o, h, l, c, v), oldest first. Cached in data/; only new bars are fetched."""
    os.makedirs(DIR, exist_ok=True)
    path = os.path.join(DIR, f"{symbol}_{interval}.csv")
    out = []
    if os.path.exists(path):
        with open(path, newline="") as fh:
            out = [(int(r[0]), *map(float, r[1:])) for r in csv.reader(fh)]
    t = out[-1][0] + 1 if out else int(datetime.datetime.fromisoformat(start + "+00:00").timestamp() * 1000)
    now = int(time.time() * 1000)
    new = []
    while True:
        rows = _get(URL.format(s=symbol, i=interval, t=t))
        # keep only closed bars (close time in the past)
        new += [(int(k[0]), *map(float, k[1:6])) for k in rows if k[6] < now]
        if len(rows) < 1000:
            break
        t = rows[-1][0] + 1
    if new:
        with open(path, "a", newline="") as fh:
            csv.writer(fh).writerows(new)
    return out + new
