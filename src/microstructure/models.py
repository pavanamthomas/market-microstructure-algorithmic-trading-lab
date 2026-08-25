"""Kyle, Glosten–Milgrom, inventory quotes, Roll bounce, impact.

These are teaching identities. Kyle λ is not a forecast of your P&L.
A Glosten spread is adverse-selection, not inventory. Mixing the two
is a standard wrong interview answer; the objects are kept separate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class KyleParams:
    sigma_v: float
    sigma_u: float
    p0: float = 0.0

    def __post_init__(self) -> None:
        if self.sigma_v <= 0 or self.sigma_u <= 0:
            raise ValueError("volatilities must be positive")


def kyle_lambda(params: KyleParams) -> float:
    """Permanent impact coefficient in the one-shot linear-normal model.

    λ = σ_v / (2 σ_u). It maps signed order flow into a price revision.
    It is not a half-spread and it is not a Sharpe ratio.
    """
    return params.sigma_v / (2.0 * params.sigma_u)


def kyle_beta(params: KyleParams) -> float:
    return params.sigma_u / params.sigma_v


def kyle_insider_expected_profit(params: KyleParams, v: float) -> float:
    # x = (v-p0)/(2λ), E[v-p | v] = (v-p0)/2 ⇒ π = (v-p0)² / (4λ)
    lam = kyle_lambda(params)
    return (v - params.p0) ** 2 / (4.0 * lam)


def kyle_price(params: KyleParams, order_flow: float) -> float:
    return params.p0 + kyle_lambda(params) * order_flow


@dataclass(frozen=True)
class GMParams:
    mu: float
    pi: float = 0.5
    v_low: float = 0.0
    v_high: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 < self.mu < 1.0:
            raise ValueError("mu must be in (0, 1)")
        if not 0.0 < self.pi < 1.0:
            raise ValueError("pi must be in (0, 1)")
        if self.v_high <= self.v_low:
            raise ValueError("v_high must exceed v_low")


def glosten_quotes(params: GMParams) -> dict[str, float]:
    """Unit-trade Glosten–Milgrom quotes: ask = E[v|buy], bid = E[v|sell].

    Competitive specialist, no inventory argument in the objective.
    The spread is then entirely adverse-selection.
    """
    mu, pi = params.mu, params.pi
    p_buy_high = mu + (1.0 - mu) * 0.5
    p_buy_low = (1.0 - mu) * 0.5
    p_buy = p_buy_high * pi + p_buy_low * (1.0 - pi)
    p_high_given_buy = p_buy_high * pi / p_buy
    ask = p_high_given_buy * params.v_high + (1.0 - p_high_given_buy) * params.v_low

    p_sell_high = (1.0 - mu) * 0.5
    p_sell_low = mu + (1.0 - mu) * 0.5
    p_sell = p_sell_high * pi + p_sell_low * (1.0 - pi)
    p_high_given_sell = p_sell_high * pi / p_sell
    bid = p_high_given_sell * params.v_high + (1.0 - p_high_given_sell) * params.v_low
    return {
        "ask": ask,
        "bid": bid,
        "spread": ask - bid,
        "p_buy": p_buy,
        "p_sell": p_sell,
        "mid": 0.5 * (ask + bid),
        "unconditional": pi * params.v_high + (1.0 - pi) * params.v_low,
        "pi": pi,
    }


def gm_update(params: GMParams, buy: bool) -> GMParams:
    """Bayes update of π after a unit buy or sell."""
    q = glosten_quotes(params)
    if buy:
        p_buy_high = params.mu + (1.0 - params.mu) * 0.5
        pi_new = p_buy_high * params.pi / q["p_buy"]
    else:
        p_sell_high = (1.0 - params.mu) * 0.5
        pi_new = p_sell_high * params.pi / q["p_sell"]
    pi_new = float(min(max(pi_new, 1e-12), 1.0 - 1e-12))
    return GMParams(mu=params.mu, pi=pi_new, v_low=params.v_low, v_high=params.v_high)


def reservation_quotes(
    mid: float,
    inventory: float,
    gamma: float,
    sigma: float,
    horizon: float,
    half_spread: float,
) -> tuple[float, float]:
    """Inventory-shifted quotes in the spirit of Ho–Stoll / Avellaneda–Stoikov.

    reservation = mid − q γ σ² τ
    bid = reservation − δ, ask = reservation + δ

    This is not Glosten–Milgrom. Inventory can open a spread even if nobody
    is informed. Adverse selection can open a spread even if inventory is
    zero. The two channels are not identified from a single quoted spread.
    """
    if half_spread < 0 or gamma < 0 or sigma < 0 or horizon < 0:
        raise ValueError("penalty parameters must be nonnegative")
    reservation = mid - inventory * gamma * (sigma**2) * horizon
    return reservation - half_spread, reservation + half_spread


def roll_spread(trade_prices: np.ndarray) -> float:
    """Roll (1984) implied spread from serial covariance of trade-price changes.

    Under a constant mid and trades that bounce bid/ask, Cov(Δp_t, Δp_{t-1})
    = −s²/4, so s = 2 sqrt(−cov). Applied to mids of a random walk the
    covariance is ~0 and the estimator is not a spread. Negative serial
    covariance is required; otherwise the estimator is undefined here.
    """
    p = np.asarray(trade_prices, dtype=float)
    if p.size < 3:
        raise ValueError("need at least three prints")
    dp = np.diff(p)
    cov = float(np.cov(dp[1:], dp[:-1], ddof=1)[0, 1])
    if cov >= 0:
        raise ValueError(f"Roll covariance is {cov}; bounce requires cov < 0")
    return 2.0 * float(np.sqrt(-cov))


def bounce_trades(mid: float, half_spread: float, n: int, rng: np.random.Generator) -> np.ndarray:
    """Independent buys/sells at a fixed mid. Pure bounce, no news."""
    sides = rng.choice(np.array([1.0, -1.0]), size=n)
    return mid + sides * half_spread


@dataclass(frozen=True)
class Impact:
    """Temporary extra in the fill; permanent revision of the efficient price.

    Permanent impact is Kyle-like: it stays in subsequent mids.
    Temporary impact is paid in the fill and does not stay.
    Marking a position at the post-trade mid *including* your own permanent
    impact credits you for moving the tape. That is a leak, not alpha.
    """

    temporary_per_unit: float
    permanent_per_unit: float

    def fill_add(self, signed_qty: int) -> float:
        return self.temporary_per_unit * signed_qty

    def mid_revision(self, signed_qty: int) -> float:
        return self.permanent_per_unit * signed_qty
