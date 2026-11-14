# Strategy: per-market realised-volatility quantile fan, persistence median

## The problem
Forecast, for every market of Polymarket's FAA outage attribution family and
each of the 240 minutes after a checkpoint, five quantiles (5/25/50/75/95%) of
that minute's Yes price. Score is mean pinball loss (percentage points) over
every case, market, minute and quantile. A prize needs a loss strictly below
the best house entry (the persistence baseline, and a house AI model).

## What the prices actually do
Two sources of evidence:
- **The practice** (6 cases cut from Polymarket's "Next CEO of NVIDIA?"
  event, ground truth re-fetched from the public CLOB API): most minutes,
  most markets do not move at all; moves come as occasional jumps of
  0.005–0.02 and rare big jumps on news. Recent drift does NOT persist.
- **The real FAA markets** (fetched 14 Nov 2026, ~07:30 UTC): Iran 0.016,
  foreign actor 0.0325, hack 0.043, AI sandbox escape 0.006. All four are
  sticky and low-priced: over the last 120 minutes the RMS 1-minute change is
  0.0000–0.0005 (below the model's floor), with rare jumps up to 0.035 in a
  minute in the last 6 hours. The early minutes of trading saw huge jumps
  (Iran 0.49 → 0.275 in a minute), but that was the market's birth, not its
  regime at the deadline.

## The one structural difference from the NVIDIA sibling
The NVIDIA event's markets are mutually exclusive CEO candidates, so their Yes
prices should sum to 1.0 — the NVIDIA model drifted medians toward a sum of
1.0 and gained from it (0.259 vs 0.267 without). The FAA family is four
INDEPENDENT Yes/No questions: Iran, a foreign actor, a hack, an AI sandbox
escape can each be attributed or not on their own; their prices sum to ~0.1,
not 1.0. Applying a sum-to-one drift here would drag every median up ~10x
over the horizon — pure damage. So the median is pure persistence. The one
logical link (Iran implies a foreign actor, so P(foreign) ≥ P(Iran)) is already
in the prices, and persistence preserves whatever ordering they hold; no
cross-market adjustment is applied.

## The model
1. **Median: persistence.** median(h) = x, the last price at the checkpoint.
2. **Fan: per-market realised volatility.** sigma = RMS of the market's
   1-minute changes over the last 120 minutes, winsorised at +/-0.03 (one jump
   must not blow the fan up), floored at 0.0005, capped at 0.02. This is the
   big win over the house baseline's fixed 0.0025: frozen markets get a narrow
   fan, jumpy ones a wide one — and the fan widens automatically if jumps start
   during the final window.
3. **Level scaling.** sigma *= (sqrt(p(1-p))/0.5)^0.25: a market near 0.5 has
   more room to move than one pinned near 0 or 1. This matters here: all four
   FAA prices are ≤ 0.05.
4. **Sub-diffusive spread.** quantiles = median + z_tau * sigma * h^0.4 with
   standard-normal z. The spread grows slower than a random walk's sqrt(h):
   these prices are sticky and bounded, so long-horizon uncertainty grows
   slower than diffusion. No trend term, no cross-market signal.

## What was tried and rejected (local scores)
| Variant | NVIDIA practice | FAA backtest |
|---|---|---|
| House baseline (fixed sigma 0.0025, sqrt(h)) | 0.364 | 0.227 |
| Final model (persistence, floor 0.0005, h^0.4) | **0.267** | **0.106** |
| Same, floor 0.001 | 0.266 | 0.111 |
| Same, floor 0.001, h^0.5 | 0.285 | 0.154 |
| NVIDIA model (sum-to-one drift) | 0.259 | — (structurally wrong for FAA) |

The floor-0.001 variant ties on the practice and loses slightly on the FAA
backtest; the h^0.5 spread loses clearly on both. Parameters sit on a broad
plateau (window 90–180, alpha 0.35–0.45, winsor 0.02–0.03 all score within
~0.02 of each other on the practice), chosen for robustness, not for the last
0.001 of practice score.

## Caveats
The practice is graded on past prices of another event; the FAA backtest is 3
quiet overnight checkpoints. The final runs on 48 hours of prices nobody had
seen when entries closed. If an official attribution lands during the window,
one market jumps toward 1 and the others toward 0, and every entry's loss
spikes; the per-market realised-vol fan is the defence — it widens within two
hours of jumps starting. The window also ends early once every market has
settled; nothing in the model depends on that.
