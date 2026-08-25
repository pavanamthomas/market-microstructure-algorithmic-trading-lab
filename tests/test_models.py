"""Kyle, Glosten–Milgrom, inventory quotes, Roll bounce."""

from __future__ import annotations

import numpy as np
import pytest

from microstructure.leaks import roll_on_mids
from microstructure.models import (
    GMParams,
    KyleParams,
    bounce_trades,
    gm_update,
    glosten_quotes,
    kyle_beta,
    kyle_insider_expected_profit,
    kyle_lambda,
    reservation_quotes,
    roll_spread,
)


def test_kyle_foc_identity() -> None:
    p = KyleParams(sigma_v=2.0, sigma_u=4.0)
    lam = kyle_lambda(p)
    beta = kyle_beta(p)
    assert lam == pytest.approx(0.25)
    assert beta == pytest.approx(2.0)
    assert beta == pytest.approx(1.0 / (2.0 * lam))
    # Scale invariance: doubling both vols leaves λ unchanged.
    assert kyle_lambda(KyleParams(4.0, 8.0)) == pytest.approx(lam)
    assert kyle_insider_expected_profit(p, v=1.0) == pytest.approx(1.0 / (4.0 * lam))


def test_glosten_spread_is_adverse_selection_only() -> None:
    q = glosten_quotes(GMParams(mu=0.2, pi=0.5))
    assert q["ask"] == pytest.approx(0.6)
    assert q["bid"] == pytest.approx(0.4)
    assert q["spread"] == pytest.approx(0.2)
    assert q["mid"] == pytest.approx(0.5)
    tiny = glosten_quotes(GMParams(mu=1e-6, pi=0.5))
    assert tiny["spread"] == pytest.approx(0.0, abs=1e-5)


def test_gm_buys_raise_pi_and_quotes() -> None:
    p = GMParams(mu=0.4, pi=0.5)
    after = p
    for _ in range(25):
        after = gm_update(after, buy=True)
    q = glosten_quotes(after)
    assert after.pi > 0.95
    assert q["ask"] > 0.9
    assert q["spread"] < glosten_quotes(p)["spread"]


def test_inventory_shifts_both_quotes_same_direction() -> None:
    bid0, ask0 = reservation_quotes(100.0, inventory=0.0, gamma=0.1, sigma=1.0, horizon=1.0, half_spread=0.05)
    bid_l, ask_l = reservation_quotes(100.0, inventory=10.0, gamma=0.1, sigma=1.0, horizon=1.0, half_spread=0.05)
    assert ask0 - bid0 == pytest.approx(0.10)
    assert ask_l - bid_l == pytest.approx(0.10)
    # Long inventory: both quotes drop. This is not a Glosten update.
    assert bid_l < bid0
    assert ask_l < ask0


def test_roll_recovers_bounce_spread_not_mid_path() -> None:
    rng = np.random.default_rng(3)
    half = 0.02
    prints = bounce_trades(mid=50.0, half_spread=half, n=8000, rng=rng)
    s_hat = roll_spread(prints)
    assert s_hat == pytest.approx(2.0 * half, rel=0.05)

    # Independent route: serial covariance of Δp is −s²/4.
    dp = np.diff(prints)
    cov = float(np.cov(dp[1:], dp[:-1], ddof=1)[0, 1])
    assert cov == pytest.approx(-(2.0 * half) ** 2 / 4.0, rel=0.08)

    mids = 50.0 + np.cumsum(rng.normal(0.0, 0.01, size=8000))
    leaked = roll_on_mids(mids)
    # Random-walk mids do not bounce. Estimator must not return the quoted spread.
    if leaked is not None:
        assert abs(leaked - 2.0 * half) > 0.02
