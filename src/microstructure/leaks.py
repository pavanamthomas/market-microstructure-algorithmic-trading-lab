"""Attractive but economically impossible evaluation rules.

Each function is a real method someone uses. Tests compare them with
the executable object so the leak is a number, not a slogan.
"""

from __future__ import annotations

import numpy as np

from microstructure.models import roll_spread


def mark_to_mid_pnl(side: int, mid_now: float, mid_next: float, qty: int) -> float:
    """P&L as if the trade occurred at the mid.

    The mid is not an executable price unless the spread is zero and the
    book has size at that price. This is Layer 1 of the flagship case.
    """
    return side * (mid_next - mid_now) * qty


def lookahead_side(next_mid_move: float) -> int:
    """Position signed with the future mid move. Not an information set."""
    if next_mid_move == 0:
        return 0
    return 1 if next_mid_move > 0 else -1


def roll_on_mids(mids: np.ndarray) -> float | None:
    """Apply Roll's estimator to a mid series.

    A random-walk mid has no bounce. The estimator should fail (nonnegative
    covariance) or return noise around zero, not the quoted spread. An early
    draft of this laboratory reported that number as 'the Roll spread'.
    """
    try:
        return roll_spread(mids)
    except ValueError:
        return None


def vwap_including_self(all_prices: np.ndarray, all_volumes: np.ndarray) -> float:
    """Benchmark that still contains the order being evaluated."""
    from microstructure.execution import vwap

    return vwap(all_prices, all_volumes)


def mark_including_own_permanent(
    side: int,
    fill: float,
    mid_after_own_impact: float,
    qty: int,
) -> float:
    """Credit the trader for the tape they just moved."""
    return side * (mid_after_own_impact - fill) * qty
