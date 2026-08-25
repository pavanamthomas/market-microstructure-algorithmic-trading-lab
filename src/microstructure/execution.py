"""Implementation shortfall, VWAP, TWAP, and a cost split.

Arrival mid is the paper price. The fill is the executable price.
The gap is not 'slippage' as a single number: it splits into spread,
depth, fees, delay, temporary impact, and (if you mark it) permanent
impact. VWAP is a benchmark, not a strategy, and it stops being an
appropriate benchmark when you *are* the volume or when the risk you
care about is arrival-price risk rather than volume-weighted average
distance.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Shortfall:
    """Perold implementation shortfall for a buy (sign flips for a sell).

    executed_cost: (avg_exec − arrival) * filled
    opportunity: (end_mid − arrival) * unfilled
    For a buy, both terms are losses when prices rise after the decision.
    """

    arrival: float
    avg_exec: float | None
    filled: int
    unfilled: int
    end_mid: float
    side: int

    @property
    def executed_cost(self) -> float:
        if self.avg_exec is None or self.filled == 0:
            return 0.0
        return self.side * (self.avg_exec - self.arrival) * self.filled

    @property
    def opportunity(self) -> float:
        return self.side * (self.end_mid - self.arrival) * self.unfilled

    @property
    def total(self) -> float:
        return self.executed_cost + self.opportunity


def implementation_shortfall(
    *,
    side: int,
    arrival: float,
    avg_exec: float | None,
    filled: int,
    unfilled: int,
    end_mid: float,
) -> Shortfall:
    if side not in (1, -1):
        raise ValueError("side must be +1 (buy) or -1 (sell)")
    if filled < 0 or unfilled < 0:
        raise ValueError("quantities must be nonnegative")
    return Shortfall(
        arrival=arrival,
        avg_exec=avg_exec,
        filled=filled,
        unfilled=unfilled,
        end_mid=end_mid,
        side=side,
    )


def vwap(prices: np.ndarray, volumes: np.ndarray) -> float:
    p = np.asarray(prices, dtype=float)
    v = np.asarray(volumes, dtype=float)
    if p.shape != v.shape or p.size == 0:
        raise ValueError("prices and volumes must be nonempty and aligned")
    if np.any(v < 0) or float(v.sum()) <= 0:
        raise ValueError("volumes must be nonnegative and not all zero")
    return float(np.dot(p, v) / v.sum())


def vwap_excluding_self(
    market_prices: np.ndarray,
    market_volumes: np.ndarray,
    own_prices: np.ndarray,
    own_volumes: np.ndarray,
) -> float:
    """Market VWAP after removing own prints.

    Including own prints pulls the benchmark toward the order. A large
    order then 'beats VWAP' by construction. That is leakage, not skill.
    """
    mp, mv = np.asarray(market_prices, dtype=float), np.asarray(market_volumes, dtype=float)
    residual_v = mv.copy()
    # Subtract own volume from matching prices (exact print match).
    own_p = np.asarray(own_prices, dtype=float)
    own_v = np.asarray(own_volumes, dtype=float)
    for px, qty in zip(own_p, own_v, strict=True):
        match = np.where(np.isclose(mp, px))[0]
        left = float(qty)
        for i in match:
            take = min(residual_v[i], left)
            residual_v[i] -= take
            left -= take
            if left <= 0:
                break
        if left > 1e-12:
            raise ValueError("own volume is not a subset of market volume")
    return vwap(mp, residual_v)


def twap(prices: np.ndarray) -> float:
    p = np.asarray(prices, dtype=float)
    if p.size == 0:
        raise ValueError("empty TWAP")
    return float(p.mean())


def clock_sample(event_times: np.ndarray, event_values: np.ndarray, clock: np.ndarray) -> np.ndarray:
    """Last-event-as-of clock sampling. Event time and clock time are not the same process."""
    t = np.asarray(event_times, dtype=float)
    y = np.asarray(event_values, dtype=float)
    c = np.asarray(clock, dtype=float)
    if t.size != y.size or t.size == 0:
        raise ValueError("event series must be aligned and nonempty")
    if np.any(np.diff(t) < 0) or np.any(np.diff(c) < 0):
        raise ValueError("times must be nondecreasing")
    out = np.empty(c.shape, dtype=float)
    j = 0
    last = y[0]
    for i, ci in enumerate(c):
        while j < t.size and t[j] <= ci:
            last = y[j]
            j += 1
        out[i] = last
    return out


@dataclass(frozen=True)
class CostSplit:
    spread: float
    depth: float
    fee: float
    delay: float
    temporary_impact: float
    permanent_marked: float

    @property
    def total(self) -> float:
        return (
            self.spread
            + self.depth
            + self.fee
            + self.delay
            + self.temporary_impact
            + self.permanent_marked
        )


def split_buy_cost(
    *,
    mid: float,
    ask: float,
    walk_vwap: float,
    delayed_vwap: float,
    fee: float,
    temp_add: float,
    post_mid: float,
    mark_own_permanent: bool,
) -> CostSplit:
    """Buy-side decomposition relative to the arrival mid.

    spread = ask − mid
    depth  = walk_vwap − ask
    fee    = fee (already in currency per unit)
    delay  = delayed_vwap − walk_vwap  (clock/event wait, book has moved)
    temp   = temp_add
    perm   = (post_mid − mid) if marked, else 0 in the fill; the mid moved.
    """
    perm = (post_mid - mid) if mark_own_permanent else 0.0
    return CostSplit(
        spread=ask - mid,
        depth=walk_vwap - ask,
        fee=fee,
        delay=delayed_vwap - walk_vwap,
        temporary_impact=temp_add,
        permanent_marked=perm,
    )
