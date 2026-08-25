# Interview guide

This is the work I can defend. It is not a script for a job I have not held.

## A. 15-second walkthrough

I built a tick-grid limit-order book and ran one imbalance rule through eight prices. Marked at the mid, mean P&L per unit is +0.007. Walked through the book, it is −0.006. The signal still predicts direction. Direction is not a fill.

## B. 30-second walkthrough

**Problem.** Mid-price backtests of microstructure signals.

**Method.** Rectangular FIFO book; causal signal `s = ε + η`; peel look-ahead → mid → touch → walk → fees → impact (own tape vs not) → delay.

**Failure.** A latent mid off the tick grid made “half-spread drag” a rounding remainder. Snapping the mid restored the identity `drag = Q δ`.

**Validation.** Look-ahead mean = mean `|ε|`; walk VWAP matches a closed form that never calls the book; Kyle `β = 1/(2λ)`; Roll covariance on bounce prints is `−s²/4`; VWAP including self is strictly closer to the order than VWAP excluding self.

## C. 60-second walkthrough

**Target.** An executable-price object a specialist can audit, plus the evaluation leaks that manufacture edge.

**Assumptions.** Tick grid, rectangular depth, no hidden size, impact not fed back into the shared mid path, simulated prints only.

**Implementation.** `LimitOrderBook` in integer ticks; `layers.py` for the peel; `leaks.py` for the wrong marks.

**Hardest failure mode.** A statistically well-defined P&L on the wrong price: look-ahead sign, mid mark, own prints in VWAP, own `λq` in the mark.

**Independent validation.** Identities above, plus Glosten `ask = E[v|buy]` and inventory quotes that shift both sides without changing the quoted spread.

**Limitation.** One toy DGP. Changing `δ` or `Q` can move the sign of the walk layer. That is the point of the assumption-change tests, not a robustness claim about markets.

## D. Hard questions I can defend

1. Why is the mid not executable on this book? There is no size at `m`; size starts at `m ± δ`.
2. What does Kyle’s λ measure? The mapping from signed order flow to the market maker’s price revision in the linear-normal one-shot model, `σ_v/(2σ_u)`.
3. Why can imbalance predict direction without profit? Hit rate 0.59; `|ε|` is smaller than δ plus walk extra.
4. How does Glosten generate a spread with zero inventory? `ask = E[v|buy]`, `bid = E[v|sell]`, `μ > 0`.
5. How does inventory generate a spread with zero informed flow? Reservation `m − q γ σ² τ`, quotes `r ± δ`. Both quotes move when `q` moves; that is not a Bayes update.
6. Temporary vs permanent impact? Temporary is in the fill and does not stay. Permanent revises the efficient price. Marking the post-impact mid pockets permanent impact.
7. Why is a backtest that matches `ε` to the nearest tick still possibly impossible? Look-ahead uses `sign(ε)`, which is not in the time-`t` information set.
8. When does VWAP stop being an appropriate benchmark? When you are the volume; when the risk is arrival-price risk (use implementation shortfall); when the clock of the benchmark is not the clock of the order.
9. Event time vs clock time? `clock_sample` holds the last print. Calendar bars can net two opposing event returns into one.
10. Bid-ask bounce vs news? Roll on bounce prints recovers `s`; Roll on a random-walk mid does not.
11. Why FIFO? Two lots at one price; the first resting size is consumed first (`test_fifo_at_a_price`).
12. What is the microprice? Size-weighted touch. Thick bid pulls it toward the ask. It is still not a fill.
13. Implementation shortfall vs mid P&L? IS uses arrival mid, fill, and unfilled remainder against the end mid (Perold). Mid P&L assumes the fill was the mid.
14. What if `Q ≤ L`? Walk extra is zero and the walk layer collapses into the touch. The sign of executable P&L then hangs on `E[sign(s) ε] ≷ δ`.
15. Is this partial equilibrium? Yes. The rectangular book does not reprice from `μ` or from inventory. Those models sit in `models.py` and are not this DGP.

## E. Change-an-assumption tests

1. **`Q ≤ 10`.** Walk extra vanishes. `test_walk_drag` would report extra = 0. Touch layer remains `−δ` per unit relative to mid.
2. **`δ = 0` with depth still one tick away.** Impossible on this book constructor (`half_spread_ticks ≥ 1`). A one-tick spread is the minimum displayed spread here.
3. **`half_spread_ticks = 2`.** Half-spread doubles to 0.02; causal mid +0.007 cannot survive the touch. The peel becomes more negative earlier.
4. **Feed permanent impact into the shared mid.** Later events trade on a path the order moved. Layer comparison stops being ceteris paribus. That is why it is a mark term only.
5. **Risk-neutral Glosten vs inventory.** Set `μ → 0`: Glosten spread → 0. Set `q = 0`: inventory quotes are symmetric about `m`. Observing one spread does not tell you which model produced it.

## F. Three limitations to volunteer

1. Rectangular displayed depth. Real books have holes, hidden size, and cancellations.
2. The sign of executable P&L is a calibration, not a market theorem.
3. No second implementation of the matching engine (for example a price-time reference from an external library). The independent check on fills is the rectangular closed form, not a second engine.
