"""Shortfall, VWAP leakage, clock versus event time, cost split."""

from __future__ import annotations

import numpy as np
import pytest

from microstructure.execution import (
    clock_sample,
    implementation_shortfall,
    split_buy_cost,
    twap,
    vwap,
    vwap_excluding_self,
)
from microstructure.leaks import vwap_including_self


def test_shortfall_splits_executed_and_opportunity() -> None:
    sf = implementation_shortfall(
        side=1,
        arrival=100.0,
        avg_exec=100.20,
        filled=8,
        unfilled=2,
        end_mid=101.0,
    )
    assert sf.executed_cost == pytest.approx(1.6)
    assert sf.opportunity == pytest.approx(2.0)
    assert sf.total == pytest.approx(3.6)
    sell = implementation_shortfall(
        side=-1,
        arrival=100.0,
        avg_exec=99.80,
        filled=8,
        unfilled=2,
        end_mid=99.0,
    )
    assert sell.executed_cost == pytest.approx(1.6)
    assert sell.opportunity == pytest.approx(2.0)


def test_own_prints_in_vwap_are_leakage() -> None:
    market_p = np.array([10.0, 10.0, 11.0])
    market_v = np.array([100.0, 50.0, 50.0])
    own_p = np.array([11.0])
    own_v = np.array([50.0])
    bench = vwap_excluding_self(market_p, market_v, own_p, own_v)
    leaked = vwap_including_self(market_p, market_v)
    # Ex-self: (10*100 + 10*50) / 150 = 10. With self: 10.25.
    assert bench == pytest.approx(10.0)
    assert leaked == pytest.approx(10.25)
    assert leaked > bench
    # Distance of the 11-print to leaked VWAP is smaller than to ex-self VWAP.
    assert abs(11.0 - leaked) < abs(11.0 - bench)


def test_twap_ignores_volume() -> None:
    prices = np.array([1.0, 3.0])
    volumes = np.array([99.0, 1.0])
    assert twap(prices) == pytest.approx(2.0)
    assert vwap(prices, volumes) == pytest.approx((99 + 3) / 100)


def test_clock_sample_holds_last_event() -> None:
    times = np.array([0.0, 0.4, 1.7])
    values = np.array([10.0, 11.0, 9.0])
    clock = np.array([0.0, 2.0])
    sampled = clock_sample(times, values, clock)
    np.testing.assert_allclose(sampled, [10.0, 9.0])
    # Event time sees 10→11 and 11→9. Clock time at {0,2} sees only 10→9.
    event_ret = np.diff(values)
    clock_ret = np.diff(sampled)
    assert event_ret.shape != clock_ret.shape
    assert not np.isclose(clock_ret.sum(), event_ret[0])


def test_buy_cost_split_adds_up() -> None:
    split = split_buy_cost(
        mid=100.0,
        ask=100.01,
        walk_vwap=100.013,
        delayed_vwap=100.023,
        fee=0.01,
        temp_add=0.002,
        post_mid=100.05,
        mark_own_permanent=True,
    )
    assert split.spread == pytest.approx(0.01)
    assert split.depth == pytest.approx(0.003)
    assert split.delay == pytest.approx(0.01)
    assert split.total == pytest.approx(
        0.01 + 0.003 + 0.01 + 0.01 + 0.002 + 0.05
    )
    split_ex = split_buy_cost(
        mid=100.0,
        ask=100.01,
        walk_vwap=100.013,
        delayed_vwap=100.023,
        fee=0.01,
        temp_add=0.002,
        post_mid=100.05,
        mark_own_permanent=False,
    )
    assert split_ex.permanent_marked == 0.0
    assert split.total - split_ex.total == pytest.approx(0.05)
