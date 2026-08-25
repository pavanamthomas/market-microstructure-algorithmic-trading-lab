# Identities used as tests

Not a tutorial. The test names are the index.

| Object | Statement | Test |
| --- | --- | --- |
| Spread | `ask − bid ≥ 0`; mid strictly inside | `test_spread_nonnegative_and_mid_inside` |
| Executable buy | VWAP `≥` best ask at the start of the walk | `test_market_buy_cannot_print_below_best_ask` |
| Rectangular walk | Book walker = `rectangular_vwap` | `test_walk_matches_independent_rectangular_formula` |
| FIFO | First lot at a price fills first | `test_fifo_at_a_price` |
| Microprice | Thick bid ⇒ microprice `>` mid | `test_microprice_pulled_toward_thin_side` |
| Kyle | `λ = σ_v/(2σ_u)`, `β = 1/(2λ)` | `test_kyle_foc_identity` |
| Glosten | `ask = E[v\|buy]`; `μ → 0` ⇒ spread `→ 0` | `test_glosten_spread_is_adverse_selection_only` |
| Inventory | Long inventory shifts both quotes down; spread unchanged | `test_inventory_shifts_both_quotes_same_direction` |
| Roll | Bounce prints: `Cov(Δp_t, Δp_{t−1}) = −s²/4` | `test_roll_recovers_bounce_spread_not_mid_path` |
| Look-ahead | Mean per unit = mean `\|ε\|` | `test_lookahead_mean_is_mean_abs_innovation` |
| Spread drag | Mid P&L − touch P&L = `Q δ` | `test_spread_drag_matches_half_spread` |
| VWAP leak | Including own prints moves the benchmark toward the order | `test_own_prints_in_vwap_are_leakage` |
