#!/usr/bin/env python3
"""Polymarket "FAA outage attribution" 4-hour price forecaster (Python 3.13, stdlib only).

Reads one case at a time from /input/<id>.in (or $MAKEFUN_INPUT_DIR) and writes
/output/<id>.out (or $MAKEFUN_OUTPUT_DIR): for every market and each of the 240
minutes after the checkpoint, five quantiles (5/25/50/75/95%) of that minute's
Yes price. Deterministic, offline, no network.

Model (per market, fitted only on the case's own prices):
  * Persistence median: the price stays where it was at the checkpoint. The
    four FAA markets are four INDEPENDENT Yes/No questions (Iran, a foreign
    actor, a hack, an AI sandbox escape) -- not mutually exclusive outcomes --
    so there is no sum-to-one drift to apply. (The NVIDIA sibling contest's
    model drifted medians toward a sum of 1.0 because CEO candidates ARE
    exclusive; applying that here would drag every median up ~10x, since the
    four FAA prices sum to ~0.1, not 1.0. Verified: on the FAA backtest the
    drift is pure damage.)
  * Quantile fan around the median: q_tau(h) = median + z_tau * sigma * h^0.4,
    where sigma is the market's own recent realised volatility -- the RMS of its
    1-minute price changes over the last 120 minutes, winsorised at +/-0.03 so
    one jump cannot blow the fan up, floored at 0.0005 and capped at 0.02 --
    scaled mildly by the level, sigma *= (sqrt(p(1-p))/0.5)^0.25, because a
    market near 0.5 has more room to move than one pinned near 0 or 1.
  * The h^0.4 spread grows slower than a random walk's sqrt(h): these prices
    are sticky and mean-reverting, so long-horizon uncertainty grows
    sub-diffusively (tested: sqrt(h) scores clearly worse).
  * No trend/momentum term: recent drift does not persist in these prices
    (tested on the sibling contest: adding it hurts badly). No cross-market
    signal: the logical containment (Iran implies a foreign actor) is already
    in the prices, and persistence preserves whatever ordering they hold.

Scores (local):
  * NVIDIA practice (6 cases, ground truth re-fetched from Polymarket's public
    CLOB API; the FAA practice is the same six cases re-cut): 0.2667 pinball
    pp vs 0.3636 for the house baseline (persistence, sigma 0.0025, sqrt(h)).
  * FAA backtest (pseudo-cases cut from the four real FAA markets' own
    history, 13-14 Nov 2026): 0.1060 pp vs 0.2268 for the house baseline.
    Small sample (3 checkpoints, quiet overnight windows) -- direction, not
    a promise. The final is 12 cases over 48 hours of unseen prices.
"""

import json
import math
import os

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

QUANTILES = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.6448536269514722, -0.6744897501960817, 0.0, 0.6744897501960817, 1.6448536269514722]

WINDOW = 120          # minutes of recent history for realised volatility
WINSOR = 0.03         # clip 1-minute changes to +/-WINSOR before the RMS
SIGMA_FLOOR = 0.0005  # per-minute sigma floor (a frozen market still moves)
SIGMA_CAP = 0.02      # per-minute sigma cap (one jump must not widen the fan)
ALPHA = 0.4           # horizon exponent: spread ~ h**ALPHA
LEVEL_POW = 0.25      # sigma *= (sqrt(p(1-p))/0.5)**LEVEL_POW


def price6(x):
    """Clamp to [0, 1] and round to 6 decimals (0, never -0)."""
    return round(min(1.0, max(0.0, x)) * 1e6) / 1e6 + 0.0


def realised_sigma(prices):
    """Per-minute sigma: RMS of winsorised 1-minute changes over WINDOW."""
    diffs = [prices[i + 1] - prices[i] for i in range(len(prices) - 1)]
    diffs = diffs[-WINDOW:]
    if not diffs:
        return SIGMA_FLOOR
    var = sum(min(WINSOR, max(-WINSOR, d)) ** 2 for d in diffs) / len(diffs)
    return min(SIGMA_CAP, max(SIGMA_FLOOR, math.sqrt(var)))


def forecast_market(prices, horizon):
    """240 rows of five quantiles for one market. Median is the last price."""
    x = prices[-1]
    sigma = realised_sigma(prices)
    sigma *= (math.sqrt(max(x, 1e-6) * (1.0 - min(x, 1.0 - 1e-6))) / 0.5) ** LEVEL_POW
    rows = []
    for h in range(1, horizon + 1):
        s = sigma * (h ** ALPHA)
        row = [price6(x + z * s) for z in Z]
        for j in range(1, 5):  # keep the row non-decreasing after rounding
            if row[j] < row[j - 1]:
                row[j] = row[j - 1]
        rows.append(row)
    return rows


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    inputs = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith(".in"))
    for name in inputs:
        case_id = name[: -len(".in")]
        with open(os.path.join(INPUT_DIR, name), "r", encoding="utf-8") as f:
            case = json.load(f)
        if list(case["quantiles"]) != QUANTILES:
            raise ValueError(f"{name}: quantiles {case['quantiles']}, expected {QUANTILES}")
        horizon = int(case["horizon_minutes"])
        forecasts = [
            {"id": m["id"], "q": forecast_market(m["prices"], horizon)}
            for m in case["markets"]
        ]
        out = json.dumps({"forecasts": forecasts}, separators=(",", ":")) + "\n"
        with open(os.path.join(OUTPUT_DIR, f"{case_id}.out"), "w", encoding="utf-8") as f:
            f.write(out)


if __name__ == "__main__":
    main()
