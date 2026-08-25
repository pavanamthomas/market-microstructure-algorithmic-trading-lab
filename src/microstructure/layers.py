"""Layered evaluation of one simulated imbalance strategy.

The strategy is not a claim about markets. It is a device that makes a
mid-price backtest look good so the later layers can take that appearance
apart.

Layers, in order:

0. look-ahead sign of the next mid move, marked at mid
1. causal noisy signal, marked at mid
2. same signal, filled at the touch (quoted spread)
3. same signal, walk the rectangular book (executable price)
4. plus fees
5. plus temporary impact in the fill; mark at mid including own permanent impact
6. same fills, mark excluding own permanent impact
7. fill delayed until after the mid has moved (the predicted move has printed)

The information set, the executable price, and the mark are three
different objects. A backtest can be statistically well-defined on the
wrong pair.

Permanent impact is applied only inside layers 5–6 as an evaluation
term. It is not folded into the shared mid path, so the peel is
ceteris paribus on the same (ε_t).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from microstructure.book import Side, rectangular_book, rectangular_vwap
from microstructure.models import Impact


@dataclass(frozen=True)
class LayerConfig:
    n_events: int = 4000
    seed: int = 7
    mid0: float = 100.0
    tick: float = 0.01
    half_spread_ticks: int = 1
    levels: int = 5
    size_per_level: int = 10
    qty: int = 15
    sigma_mid: float = 0.012
    signal_noise: float = 0.010
    fee_bps: float = 1.0
    temporary_per_unit: float = 4e-5
    permanent_per_unit: float = 1.5e-5


LAYERS = (
    "lookahead_mid",
    "causal_mid",
    "quoted_spread",
    "walk_book",
    "plus_fees",
    "plus_impact_mark_own",
    "plus_impact_ex_own",
    "delayed_fill",
)


def _fee_per_unit(price: float, bps: float) -> float:
    return price * (bps / 1e4)


def simulate_layers(cfg: LayerConfig | None = None) -> pd.DataFrame:
    cfg = cfg or LayerConfig()
    rng = np.random.default_rng(cfg.seed)
    eps_raw = rng.normal(0.0, cfg.sigma_mid, size=cfg.n_events)
    eta = rng.normal(0.0, cfg.signal_noise, size=cfg.n_events)
    impact = Impact(cfg.temporary_per_unit, cfg.permanent_per_unit)
    half = cfg.half_spread_ticks * cfg.tick
    # Snap the efficient price to the tick grid so displayed mid = latent mid
    # and half-spread drag is exactly qty * half, not a rounding remainder.
    mid = float(np.round(cfg.mid0 / cfg.tick) * cfg.tick)

    rows: list[dict[str, float]] = []
    for t in range(cfg.n_events):
        e = float(np.round(eps_raw[t] / cfg.tick) * cfg.tick)
        s = e + float(eta[t])
        causal_side = 0 if s == 0 else (1 if s > 0 else -1)
        look_side = 0 if e == 0 else (1 if e > 0 else -1)
        next_mid = mid + e
        if causal_side == 0:
            rows.append(
                {
                    "mid": mid,
                    "eps": e,
                    "signal": s,
                    "causal_side": 0,
                    "lookahead_mid": look_side * e * cfg.qty,
                    "causal_mid": 0.0,
                    "quoted_spread": 0.0,
                    "walk_book": 0.0,
                    "plus_fees": 0.0,
                    "plus_impact_mark_own": 0.0,
                    "plus_impact_ex_own": 0.0,
                    "delayed_fill": 0.0,
                    "half_spread": half,
                    "walk_vwap": mid,
                    "touch": mid,
                }
            )
            mid = next_mid
            continue
        book = rectangular_book(
            mid=mid,
            tick_size=cfg.tick,
            half_spread_ticks=cfg.half_spread_ticks,
            levels=cfg.levels,
            size_per_level=cfg.size_per_level,
        )
        if book.best_ask is None or book.best_bid is None:
            raise RuntimeError("empty book")
        ask, bid = book.best_ask, book.best_bid
        side_enum = Side.BUY if causal_side > 0 else Side.SELL
        touch = ask if causal_side > 0 else bid
        walk = rectangular_vwap(
            touch, cfg.tick, cfg.size_per_level, cfg.qty, side_enum
        )
        delayed_mid = mid + e
        delayed_book = rectangular_book(
            mid=delayed_mid,
            tick_size=cfg.tick,
            half_spread_ticks=cfg.half_spread_ticks,
            levels=cfg.levels,
            size_per_level=cfg.size_per_level,
        )
        d_ask, d_bid = delayed_book.best_ask, delayed_book.best_bid
        if d_ask is None or d_bid is None:
            raise RuntimeError("empty delayed book")
        d_touch = d_ask if causal_side > 0 else d_bid
        delayed_walk = rectangular_vwap(
            d_touch, cfg.tick, cfg.size_per_level, cfg.qty, side_enum
        )

        qty = cfg.qty
        next_mid = mid + e
        signed_qty = causal_side * qty
        perm = impact.mid_revision(signed_qty)
        temp = impact.fill_add(signed_qty)
        fill_with_temp = walk + temp
        fee = _fee_per_unit(walk, cfg.fee_bps) * qty

        lookahead = look_side * e * qty
        causal_mid = causal_side * e * qty
        spread_pnl = causal_side * (next_mid - touch) * qty
        walk_pnl = causal_side * (next_mid - walk) * qty
        fee_pnl = walk_pnl - fee
        impact_mark_own = causal_side * ((next_mid + perm) - fill_with_temp) * qty - fee
        impact_ex_own = causal_side * (next_mid - fill_with_temp) * qty - fee
        delayed = causal_side * (next_mid - delayed_walk) * qty - fee

        rows.append(
            {
                "mid": mid,
                "eps": e,
                "signal": s,
                "causal_side": causal_side,
                "lookahead_mid": lookahead,
                "causal_mid": causal_mid,
                "quoted_spread": spread_pnl,
                "walk_book": walk_pnl,
                "plus_fees": fee_pnl,
                "plus_impact_mark_own": impact_mark_own,
                "plus_impact_ex_own": impact_ex_own,
                "delayed_fill": delayed,
                "half_spread": half,
                "walk_vwap": walk,
                "touch": touch,
            }
        )
        mid = next_mid
    return pd.DataFrame(rows)


def layer_means(df: pd.DataFrame) -> pd.Series:
    return df.loc[:, list(LAYERS)].mean()


def layer_table(cfg: LayerConfig | None = None) -> pd.DataFrame:
    cfg = cfg or LayerConfig()
    df = simulate_layers(cfg)
    means = layer_means(df)
    out = means.rename("mean_pnl").to_frame()
    out["mean_pnl_per_unit"] = out["mean_pnl"] / cfg.qty
    return out
