# Roadmap

Open technical work.

## Queue-priority sensitivity under a second arriver

`test_fifo_at_a_price` checks that the first lot is consumed first. It does not compute fill probabilities when a market order and a later marketable limit race. That needs a stated time-priority protocol for same-timestamp events. Adding one without naming the tie-break recreates an unnamed-price problem.

## Hidden size

The flagship excludes iceberg quantity. If hidden size is admitted, the walk closed form is no longer independent of the book: displayed depth is not executable depth. The identity in `test_walk_matches_independent_rectangular_formula` would have to be retired or restated.

## Glosten book as the flagship DGP

Quotes in `layers.py` are a rectangular spread, not `E[v | side]`. Replacing the touch with sequential Glosten quotes would make adverse selection the spread, and the peel would need a new uniqueness statement about whether the signal is public information already in the quote.

## Permanent impact in the path

Feeding `λq` into subsequent mids is economically natural and destroys ceteris paribus layer comparison. A second experiment, separately labelled, is the right place for that — not a silent change to seed 7.

## What this laboratory will not absorb

A live matching engine, a broker adapter, or a claimed execution track record. Valuation identities belong in `quantitative-finance-models`. 10-option items belong in `economics-finance-assessment-benchmark-lab`.
