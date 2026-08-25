# Failures and corrections

Defects caught while building the book and the peel. Not a reconstructed diary.

## 1. Half-spread drag was a rounding remainder

**What failed.** The first peel used a continuous latent mid and rebuilt the book by rounding that mid to ticks. `causal_mid − quoted_spread` was then `Q · (touch − latent_mid)`, not `Q δ`. A unit test that demanded equality to `Q δ` failed on almost every event.

**How it was detected.** `test_spread_drag_matches_half_spread`.

**Why it failed.** The displayed mid and the mark mid were different objects, and the test named the wrong one.

**What changed.** Innovations are snapped to the tick grid before the book is built, so displayed mid = mark mid. The identity holds on traded events (absolute tolerance `1e-9`).

**What would fail if it recurred.** That test.

## 2. Cost-split test omitted delay

**What failed.** `split_buy_cost` returned 0.085. The test expected 0.075 because the expected sum skipped the delay term. The implementation was adding the terms it claimed to add.

**How it was detected.** `test_buy_cost_split_adds_up`.

**Why it failed.** The test restated the decomposition with one addend dropped. That is a wrong test, not a wrong split.

**What changed.** The expected total includes delay. The function was not “fixed” to match a bad expected value.

## 3. Roll applied to mids

**What failed.** An early helper returned a “Roll spread” on a random-walk mid series whenever the sample covariance happened to be negative. That number was nowhere near the quoted bounce spread and was still being labelled a spread.

**How it was detected.** Comparing `roll_spread(bounce_trades(...))` with `roll_on_mids(random_walk)`.

**Why it failed.** Roll’s derivation is bounce around a constant mid, not news.

**What changed.** `roll_on_mids` returns `None` when covariance is nonnegative, and the bounce test requires recovery of `2 × half` on trade prints. `leaks.py` keeps the wrong call site explicit.

## 4. Own permanent impact in the mark

**What failed.** Marking `m_{t+1} + λq` after a buy made impact look cheaper than the same fills marked at `m_{t+1}`.

**How it was detected.** `plus_impact_mark_own > plus_impact_ex_own` on the flagship seed, which is the inequality the peel is supposed to exhibit, once you notice it is not alpha.

**Why it failed.** Last-print mark-to-market includes the tape you just moved.

**What changed.** Two columns, not one. The leak function remains in `leaks.mark_including_own_permanent`.
