# Polymarket FAA Outage Attribution Forecaster

Entry for make.fun's
[polymarket-faa-attribution-02](https://make.fun/bounty/polymarket-faa-attribution-02):
forecast every market of Polymarket's FAA outage attribution family — whether
the U.S. government attributes the November 13, 2026 FAA outage to Iran, to a
foreign actor, to a hack, or to an AI sandbox escape — minute by minute, 4
hours ahead: five quantiles (5/25/50/75/95%) of each minute's Yes price.

## Run

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=<kit>/input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

`main.py` is Python 3.13, standard library only, offline, deterministic
(~0.05 s per case). It reads every `<id>.in` in the input directory and writes
`<id>.out` (`{"forecasts":[{"id","q"}]}`, 240 rows of five quantiles per
market) to the output directory. Outside the grader, `MAKEFUN_INPUT_DIR` and
`MAKEFUN_OUTPUT_DIR` stand in for `/input` and `/output`.

## Model

Per market, fitted only on the case's own prices:

- **Median:** pure persistence — the price stays where it was at the
  checkpoint. The four FAA markets are four independent Yes/No questions, not
  mutually exclusive outcomes, so there is no sum-to-one drift (unlike the
  sibling NVIDIA contest, where the candidates are exclusive).
- **Fan:** per-market realised volatility — RMS of winsorised 1-minute changes
  over the last 120 minutes — scaled mildly by the price level
  (`(sqrt(p(1-p))/0.5)^0.25`), spread as `sigma * h^0.4` with standard-normal
  quantiles.

See [STRATEGY.md](STRATEGY.md) for the full reasoning, what was tried and
rejected, and the scores.

## Scores (local)

- **NVIDIA practice** (6 cases; the FAA practice is the same six cases
  re-cut, ground truth re-fetched from Polymarket's public CLOB API):
  **0.267 pinball-loss percentage points**, vs 0.364 for the house baseline
  (persistence, sigma 0.0025, sqrt(h)).
- **FAA backtest** (pseudo-cases cut from the four real FAA markets' own
  history, 13–14 Nov 2026): **0.106 pp**, vs 0.227 for the house baseline.
  Small sample (3 checkpoints, quiet overnight windows) — direction, not a
  promise. The final is 12 cases over 48 hours of unseen prices.

## License

MIT. See [LICENSE](LICENSE).
