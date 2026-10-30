DAY = 86_400_000


def bars(closes, start_day=0):
    """Daily bars (t, o, h, l, c, v) from a list of closes."""
    return [((start_day + i) * DAY, c, c, c, c, 1.0) for i, c in enumerate(closes)]


def rising(n=400, start=100.0, step=0.002):
    return [start * (1 + step) ** i for i in range(n)]


def falling(n=400, start=100.0, step=0.002):
    return [start * (1 - step) ** i for i in range(n)]
