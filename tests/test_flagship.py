"""Flagship peel: mid-marked edge is not an executable edge.

Independent checks: half-spread drag from the quoted spread, walk extra
from the rectangular closed form, look-ahead strictly above causal mid.
"""

from __future__ import annotations

import numpy as np
import pytest

from microstructure.book import Side, rectangular_vwap
from microstructure.layers import LayerConfig, layer_means, simulate_layers
from microstructure.leaks import lookahead_side, mark_to_mid_pnl


def test_lookahead_mean_is_mean_abs_innovation() -> None:
    df = simulate_layers(LayerConfig(n_events=4000, seed=7))
    per_unit = df["lookahead_mid"].mean() / LayerConfig().qty
    assert per_unit == pytest.approx(float(df["eps"].abs().mean()), rel=1e-12)


def test_lookahead_beats_causal_mid_on_this_dgp() -> None:
    df = simulate_layers(LayerConfig(n_events=4000, seed=7))
    means = layer_means(df)
    assert means["lookahead_mid"] > means["causal_mid"] > 0
    # Quoted spread still uses the same signal. Paying the touch consumes
    # the mid-marked edge on this calibration.
    assert means["quoted_spread"] < means["causal_mid"]
    assert means["walk_book"] < means["quoted_spread"]
    assert means["plus_fees"] < means["walk_book"]
    # Crediting own permanent impact overstates the impact layer.
    assert means["plus_impact_mark_own"] > means["plus_impact_ex_own"]
    # Waiting until the move has printed is worse than walking the pre-move book.
    assert means["delayed_fill"] < means["walk_book"]


def test_spread_drag_matches_half_spread() -> None:
    cfg = LayerConfig(n_events=2000, seed=1)
    df = simulate_layers(cfg)
    # causal_mid − quoted_spread = side * (touch − mid) * qty = qty * half_spread
    drag = df["causal_mid"] - df["quoted_spread"]
    traded = df["causal_side"] != 0
    expected = cfg.qty * df.loc[traded, "half_spread"]
    np.testing.assert_allclose(
        drag.loc[traded].to_numpy(), expected.to_numpy(), rtol=0, atol=1e-9
    )


def test_walk_drag_matches_closed_form() -> None:
    cfg = LayerConfig()
    df = simulate_layers(cfg)
    row = df.loc[df["causal_side"] != 0].iloc[0]
    mid = float(row["mid"])
    side = int(row["causal_side"])
    touch = mid + side * cfg.half_spread_ticks * cfg.tick
    walk = rectangular_vwap(
        touch,
        cfg.tick,
        cfg.size_per_level,
        cfg.qty,
        Side.BUY if side > 0 else Side.SELL,
    )
    assert float(row["walk_vwap"]) == pytest.approx(walk)
    extra = abs(walk - touch)
    drag = abs(float(row["quoted_spread"] - row["walk_book"])) / cfg.qty
    assert drag == pytest.approx(extra)


def test_mid_mark_is_the_leak_function() -> None:
    assert mark_to_mid_pnl(1, 100.0, 100.5, 10) == pytest.approx(5.0)
    assert lookahead_side(-0.2) == -1
    assert lookahead_side(0.0) == 0


def test_positive_mid_edge_need_not_be_executable() -> None:
    means = layer_means(simulate_layers(LayerConfig(seed=7)))
    assert means["causal_mid"] > 0
    assert means["walk_book"] < 0
