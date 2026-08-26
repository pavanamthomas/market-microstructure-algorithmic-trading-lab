# Notes on the peel

The mid is not executable on this book because there is no size at `m`. Size starts at `m ± δ`. That sentence is the whole of layer 1 → 2, and I still catch myself marking mids.

Kyle’s λ is the mapping from signed order flow to the market maker’s price revision in the linear-normal one-shot model, `σ_v/(2σ_u)`. It is not a trading signal in the peel. It appears as a permanent-impact coefficient in layers 5–6, and as its own identity in `models.py`.

Imbalance can predict direction without profit. Hit rate 0.59 here; `|ε|` is smaller than δ plus walk extra. Direction is not a fill.

Glosten generates a spread with zero inventory: `ask = E[v|buy]`, `bid = E[v|sell]`, `μ > 0`. Inventory generates a spread with zero informed flow: reservation `m − q γ σ² τ`, quotes `r ± δ`. Both quotes move when `q` moves; that is not a Bayes update. Observing one spread does not tell you which model produced it.

Temporary impact is in the fill and does not stay. Permanent revises the efficient price. Marking the post-impact mid pockets permanent impact. Feeding `λq` into subsequent mids is economically natural and destroys ceteris paribus layer comparison. That is why it is a mark term only. A second experiment, separately labelled, is the right place for the path-feedback version — not a silent change to seed 7.

A backtest that matches `ε` to the nearest tick can still be impossible. Look-ahead uses `sign(ε)`, which is not in the time-`t` information set.

VWAP stops being an appropriate benchmark when you are the volume; when the risk is arrival-price risk (use implementation shortfall); when the clock of the benchmark is not the clock of the order. Own prints in the VWAP pull the benchmark toward the order. That leak has a test.

Event time vs clock time: `clock_sample` holds the last print. Calendar bars can net two opposing event returns into one.

Roll on bounce prints recovers `s`. Roll on a random-walk mid does not. Bid-ask bounce is not news.

FIFO: two lots at one price; the first resting size is consumed first (`test_fifo_at_a_price`). It does not compute fill probabilities when a market order and a later marketable limit race. That needs a stated tie-break for same-timestamp events.

The microprice is size-weighted touch. Thick bid pulls it toward the ask. It is still not a fill.

Implementation shortfall uses arrival mid, fill, and unfilled remainder against the end mid (Perold). Mid P&L assumes the fill was the mid.

If `Q ≤ L`, walk extra is zero and the walk layer collapses into the touch. The sign of executable P&L then hangs on `E[sign(s) ε] ≷ δ`. Changing `δ` or `Q` can move that sign. That is a calibration, not a market theorem.

This is partial equilibrium. The rectangular book does not reprice from `μ` or from inventory. Those models sit in `models.py` and are not this DGP. Quotes in `layers.py` are a rectangular spread, not `E[v | side]`.

Hidden size is excluded. If it is admitted, displayed depth is not executable depth and `test_walk_matches_independent_rectangular_formula` has to be retired or restated.

## Assumption changes I have actually run

`Q ≤ 10`. Walk extra vanishes. Touch layer remains `−δ` per unit relative to mid.

`δ = 0` with depth still one tick away. Impossible on this book constructor (`half_spread_ticks ≥ 1`).

`half_spread_ticks = 2`. Half-spread doubles to 0.02; causal mid +0.007 cannot survive the touch. The peel becomes more negative earlier.

Risk-neutral Glosten vs inventory. Set `μ → 0`: Glosten spread → 0. Set `q = 0`: inventory quotes are symmetric about `m`.
