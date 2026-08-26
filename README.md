# Market microstructure and algorithmic-trading laboratory

A backtest marked at the mid is a statement about a price that was not available. This repository implements a small limit-order book, the one-shot Kyle and Glosten–Milgrom identities, and a single simulated imbalance rule evaluated at eight successive prices: look-ahead mid, causal mid, quoted touch, walked book, fees, impact with and without marking your own tape, and a delayed fill.

Simulated prints are simulated. A positive mid-marked mean is not a claim that the rule is tradable. Rectangular depth, one tick size. Not a desk.

Related work, not this object: [quantitative-finance-models](https://github.com/pavanamthomas/quantitative-finance-models) is valuation, parity, and risk summaries. [economics-finance-assessment-benchmark-lab](https://github.com/pavanamthomas/economics-finance-assessment-benchmark-lab) writes 10-option items about these mechanisms. This repository is the executable book.

## Eight marks of the same rule

Same 4,000 events, seed 7, quantity 15, half-spread 0.01, 10 contracts per level. Mean P&L **per unit**:

| Evaluation | per unit | What changed |
| --- | ---: | --- |
| Look-ahead mid | +0.00910 | Sign of the future mid move; not an information set |
| Causal mid | +0.00745 | Noisy signal; still filled at the mid |
| Quoted spread | −0.00255 | Buy ask / sell bid, infinite size at the touch |
| Walk the book | −0.00588 | 15 into 10+5 on a rectangular book |
| Plus 1 bp fee | −0.01580 | Fee on walked notional |
| Impact, mark own tape | −0.01617 | Temporary in the fill; permanent credited in the mark |
| Impact, exclude own tape | −0.01640 | Same fills; do not pocket λq |
| Delayed fill | −0.02325 | Book rebuilt after ε has already printed |

The mid-marked rule looks like an edge. The executable rule does not. Order imbalance can still be correlated with the next mid move (hit rate 0.59 here). Correlation with direction is not a fill.

`python examples/run_flagship.py` reprints the table. `FLAGSHIP_CASE_STUDY.md` is the write-up.

## Bugs that already bit me

- Mid not snapped to the tick grid: “half-spread drag” picks up a rounding remainder. That bug is in `FAILURES_AND_CORRECTIONS.md`.
- Permanent impact folded into the shared mid path, so later layers are not ceteris paribus.
- Own prints left in the VWAP benchmark (`tests/test_execution.py`).
- Roll’s estimator run on mids rather than on bouncing trade prints.

## Checks that are not the same function twice

- Look-ahead mean per unit equals mean `|ε|` (identity, not a fit).
- Causal-mid minus touch P&L equals `qty × half-spread` on every traded event.
- Walked VWAP equals `rectangular_vwap`, a closed form that does not use `LimitOrderBook`.
- Kyle: `β = 1/(2λ)`. Glosten: `ask = E[v|buy]`. Roll: serial covariance of bounce prints is `−s²/4`.

Passing `pytest` means those identities held on the objects as defined. It does not mean a market looks like a rectangular book.

## Layout

```
src/microstructure/book.py       FIFO book, mid, microprice, depth, marketable limits
src/microstructure/models.py     Kyle λ, Glosten–Milgrom, inventory quotes, Roll, impact
src/microstructure/execution.py  implementation shortfall, VWAP/TWAP, clock vs event, TCA split
src/microstructure/leaks.py      mid-mark, look-ahead sign, Roll-on-mids, VWAP-with-self
src/microstructure/layers.py     the eight-layer peel
FLAGSHIP_CASE_STUDY.md
questions.md
```

## Install

Python 3.11+:

```bash
pip install -e ".[dev]"
python -m pytest -q
python examples/run_flagship.py
python scripts/run_all.py
```

CI runs pytest and `scripts/run_all.py`.

## What the book will not do

- Educational book: rectangular depth, one tick size, no hidden size, no cancellations, no maker/taker queue games beyond FIFO.
- No live data, no broker API, no claimed Sharpe, no AUM.
- Event time is the native index. Clock sampling is a demonstration that the two calendars are not the same process.
- One author. No second implementation of the matching engine. The independent check on fills is the rectangular closed form, not a second engine.

## Citation

See `CITATION.cff`.
