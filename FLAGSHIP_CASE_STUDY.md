# Flagship case: the mid-price edge that does not fill

**Code.** `src/microstructure/layers.py`, `examples/run_flagship.py`. **Leaks.** `src/microstructure/leaks.py`.

## Problem

Write a backtest of a signed-imbalance rule so that an examiner can see, in one table, which assumption manufactures the apparent profit. The rule is not interesting. The evaluation layers are.

## Assumptions

- Efficient mid lives on a tick grid of 0.01.
- Displayed book is rectangular: five levels, 10 contracts each, one tick of half-spread (quoted spread 0.02).
- Signal `s_t = ε_t + η_t`. Side is `sign(s_t)`. Quantity 15, so a buy walks 10 at the ask and 5 one tick worse.
- Fees 1 bp of walked notional. Temporary impact `4e-5` per contract added to the fill. Permanent impact `1.5e-5` per contract is a mark term only; it is not fed back into the shared mid path.
- 4,000 events, NumPy Generator seed 7.
- No hidden size, no cancellations, no lot-size constraints other than integers.

These are model assumptions, not market facts.

## Formal objects

Displayed mid `m`, best ask `a = m + δ`, best bid `b = m − δ`, `δ = 0.01`.

Rectangular buy VWAP of quantity `Q` with `L` contracts per level:

```
cost = Σ_k min(L, Q − kL) · (a + k tick),   k = 0, 1, … until filled.
```

Implementation is `rectangular_vwap` in `book.py`. The book walker must match it.

Look-ahead P&L per event: `sign(ε_t) · ε_t · Q = |ε_t| · Q`.
Causal mid P&L: `sign(s_t) · ε_t · Q`.
Touch P&L: `sign(s_t) · (m_{t+1} − touch_t) · Q`.
Walk P&L: `sign(s_t) · (m_{t+1} − walk_t) · Q`.

Kyle λ is not used as a trading signal. It appears only as a permanent-impact coefficient in layers 5–6, and as its own identity `λ = σ_v/(2σ_u)` in `models.py`.

## Implementation

`simulate_layers` rebuilds a rectangular book at `m_t`, computes each column on that event, then sets `m_{t+1} = m_t + ε_t` with `ε_t` already snapped to ticks.

## Plausible wrong approach

Mark every fill at `m_t` and the position at `m_{t+1}`. The signal is correlated with `ε_t` (hit rate 0.59 at this seed), so the mean is positive (+0.00745 per unit). A second wrong approach uses `sign(ε_t)` itself (+0.00910 per unit, which equals mean `|ε|`). A third credits `m_{t+1} + λq` as the mark.

## Why those are attractive

Mids are what researchers plot. Look-ahead is what a notebook does when the column is shifted the wrong way. Marking your own permanent impact is what a last-print mark-to-market does after a large order. None of these requires malice. They require an unnamed price.

## Failure

On this calibration the causal mid mean is positive and the walked-book mean is negative (−0.00588 per unit). The rule still “predicts direction.” It does not pay for 15 contracts of depth plus the touch.

## Corrected approach

Name the price. Report the eight-layer table. Keep the DGP fixed. If a later layer changes the mid path, the comparison is no longer a peel.

## Independent verification

1. Look-ahead mean per unit = mean `|ε|` = 0.00910. Algebra, not a regression.
2. On every traded event, causal-mid P&L minus touch P&L = `Q δ` = 0.15. Float-tolerant identity in `test_spread_drag_matches_half_spread`.
3. First traded walk equals `rectangular_vwap`, which does not instantiate `LimitOrderBook`.

## Limitation

Rectangular depth and a half-spread that does not depend on inventory or `μ`. A Ho–Stoll book or a Glosten book would change the touch layer; those models are implemented separately and are not this DGP. Fees at 1 bp dominate the walk extra on this notional — that is a parameter, not a theorem. Permanent impact is small by choice so that layer 5 does not swamp the spread story.

## Interview questions this file is meant to generate

1. Why is +0.00745 not a tradable edge?
2. Why does look-ahead equal mean `|ε|`?
3. What changes if `Q ≤ 10` so the walk layer collapses into the touch?
4. What changes if `δ → 0` with depth held fixed?
5. Why is marking `m + λq` a leak rather than “permanent impact alpha”?
6. Why is a 0.59 hit rate compatible with negative executable P&L?
7. If I put own prints into VWAP, which test fails?

Numbers from `python examples/run_flagship.py` (seed 7, n = 4000):

```
lookahead_mid          +0.009100 / unit
causal_mid             +0.007450
quoted_spread          -0.002550
walk_book              -0.005883
plus_fees              -0.015797
plus_impact_mark_own   -0.016172
plus_impact_ex_own     -0.016397
delayed_fill           -0.023247
```
