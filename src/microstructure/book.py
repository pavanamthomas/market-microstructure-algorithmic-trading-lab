"""Limit-order book with FIFO queues at each tick.

Prices are stored as integer ticks. Reported prices are `ticks * tick_size`.
This keeps spread-nonnegativity and queue ranking free of float rounding.

A market buy is filled against resting asks, best price first, FIFO within
a price. It cannot print below the best ask that existed at the start of
the walk: that is the executable-price invariant the mid-price backtest
violates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Iterator


class Side(IntEnum):
    BUY = 1
    SELL = -1


@dataclass(frozen=True)
class Fill:
    side: Side
    quantity: int
    cash: float
    best_touch: float
    walked_levels: int
    remaining: int

    @property
    def vwap(self) -> float:
        if self.quantity <= 0:
            raise ValueError("empty fill has no VWAP")
        return self.cash / self.quantity

    @property
    def fully_filled(self) -> bool:
        return self.remaining == 0


@dataclass
class LimitOrderBook:
    tick_size: float
    _bids: dict[int, list[int]] = field(default_factory=dict)
    _asks: dict[int, list[int]] = field(default_factory=dict)
    _next_id: int = 0

    def __post_init__(self) -> None:
        if self.tick_size <= 0:
            raise ValueError("tick_size must be positive")

    def _px(self, ticks: int) -> float:
        return ticks * self.tick_size

    def to_ticks(self, price: float) -> int:
        ticks = int(round(price / self.tick_size))
        if abs(ticks * self.tick_size - price) > 1e-12 * max(1.0, abs(price)):
            raise ValueError(f"{price} is not an integer number of ticks")
        return ticks

    def best_bid_ticks(self) -> int | None:
        live = [p for p, q in self._bids.items() if q and sum(q) > 0]
        return max(live) if live else None

    def best_ask_ticks(self) -> int | None:
        live = [p for p, q in self._asks.items() if q and sum(q) > 0]
        return min(live) if live else None

    @property
    def best_bid(self) -> float | None:
        t = self.best_bid_ticks()
        return None if t is None else self._px(t)

    @property
    def best_ask(self) -> float | None:
        t = self.best_ask_ticks()
        return None if t is None else self._px(t)

    @property
    def spread(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    @property
    def mid(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return 0.5 * (self.best_bid + self.best_ask)

    def bid_size_at_touch(self) -> int:
        t = self.best_bid_ticks()
        if t is None:
            return 0
        return sum(self._bids.get(t, []))

    def ask_size_at_touch(self) -> int:
        t = self.best_ask_ticks()
        if t is None:
            return 0
        return sum(self._asks.get(t, []))

    def depth(self, side: Side, levels: int | None = None) -> list[tuple[float, int]]:
        if side is Side.BUY:
            keys = sorted((p for p, q in self._bids.items() if sum(q) > 0), reverse=True)
            book = self._bids
        else:
            keys = sorted(p for p, q in self._asks.items() if sum(q) > 0)
            book = self._asks
        if levels is not None:
            keys = keys[:levels]
        return [(self._px(p), sum(book[p])) for p in keys]

    def microprice(self) -> float | None:
        """Size-weighted touch, sometimes called the microprice.

        Thick bid, thin ask ⇒ closer to the ask. That is a statement about
        displayed size, not about a fill you have been given.
        """
        bid, ask = self.best_bid, self.best_ask
        if bid is None or ask is None:
            return None
        qb, qa = self.bid_size_at_touch(), self.ask_size_at_touch()
        if qb + qa == 0:
            return None
        return (ask * qb + bid * qa) / (qb + qa)

    def imbalance(self) -> float | None:
        qb, qa = self.bid_size_at_touch(), self.ask_size_at_touch()
        if qb + qa == 0:
            return None
        return (qb - qa) / (qb + qa)

    def rest_limit(self, side: Side, price: float, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        ticks = self.to_ticks(price)
        if side is Side.BUY:
            ask = self.best_ask_ticks()
            if ask is not None and ticks >= ask:
                raise ValueError("resting buy would cross the ask; use marketable_limit")
            self._bids.setdefault(ticks, []).append(quantity)
        else:
            bid = self.best_bid_ticks()
            if bid is not None and ticks <= bid:
                raise ValueError("resting sell would cross the bid; use marketable_limit")
            self._asks.setdefault(ticks, []).append(quantity)

    def market(self, side: Side, quantity: int) -> Fill:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if side is Side.BUY:
            return self._take(quantity, Side.BUY, self._ask_walk())
        return self._take(quantity, Side.SELL, self._bid_walk())

    def marketable_limit(self, side: Side, limit_price: float, quantity: int) -> Fill:
        """Take until the limit, then rest any remainder at the limit."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        limit_ticks = self.to_ticks(limit_price)
        if side is Side.BUY:
            fill = self._take(
                quantity,
                Side.BUY,
                (item for item in self._ask_walk() if item[0] <= limit_ticks),
            )
        else:
            fill = self._take(
                quantity,
                Side.SELL,
                (item for item in self._bid_walk() if item[0] >= limit_ticks),
            )
        if fill.remaining > 0:
            self.rest_limit(side, limit_price, fill.remaining)
        return fill

    def _ask_walk(self) -> Iterator[tuple[int, int, int]]:
        for price in sorted(p for p, q in self._asks.items() if sum(q) > 0):
            for i, size in enumerate(self._asks[price]):
                if size > 0:
                    yield price, i, size

    def _bid_walk(self) -> Iterator[tuple[int, int, int]]:
        for price in sorted((p for p, q in self._bids.items() if sum(q) > 0), reverse=True):
            for i, size in enumerate(self._bids[price]):
                if size > 0:
                    yield price, i, size

    def _take(
        self,
        quantity: int,
        side: Side,
        walk: Iterator[tuple[int, int, int]],
    ) -> Fill:
        book = self._asks if side is Side.BUY else self._bids
        remaining = quantity
        cash = 0.0
        levels: set[int] = set()
        first_touch: int | None = None
        for price, idx, size in walk:
            if remaining == 0:
                break
            if first_touch is None:
                first_touch = price
            take = min(size, remaining)
            book[price][idx] -= take
            remaining -= take
            cash += take * self._px(price)
            levels.add(price)
        touch = self._px(first_touch) if first_touch is not None else float("nan")
        filled = quantity - remaining
        return Fill(
            side=side,
            quantity=filled,
            cash=cash,
            best_touch=touch,
            walked_levels=len(levels),
            remaining=remaining,
        )


def rectangular_book(
    mid: float,
    tick_size: float,
    half_spread_ticks: int,
    levels: int,
    size_per_level: int,
) -> LimitOrderBook:
    """Symmetric displayed book around a mid that sits on a half-tick if needed.

    `half_spread_ticks=1` and an on-tick mid puts the bid one tick below mid
    and the ask one tick above. The mid of that book equals the supplied mid
    only when `half_spread_ticks` is integer and mid is a half-tick or a tick
    as required. Callers that need an exact mid should pass a mid that is a
    multiple of `tick_size / 2`.
    """
    if half_spread_ticks < 1 or levels < 1 or size_per_level < 1:
        raise ValueError("book geometry must be positive")
    book = LimitOrderBook(tick_size=tick_size)
    mid_ticks = int(round(mid / tick_size))
    # If mid is on a tick, the inside is mid ± half_spread_ticks.
    bid0 = mid_ticks - half_spread_ticks
    ask0 = mid_ticks + half_spread_ticks
    for i in range(levels):
        book.rest_limit(Side.BUY, (bid0 - i) * tick_size, size_per_level)
        book.rest_limit(Side.SELL, (ask0 + i) * tick_size, size_per_level)
    return book


def rectangular_vwap(touch: float, tick_size: float, size_per_level: int, qty: int, side: Side) -> float:
    """Closed-form VWAP for a rectangular book, independent of LimitOrderBook."""
    if qty <= 0 or size_per_level <= 0:
        raise ValueError("qty and size_per_level must be positive")
    remaining = qty
    cash = 0.0
    level = 0
    step = tick_size if side is Side.BUY else -tick_size
    while remaining > 0:
        take = min(size_per_level, remaining)
        cash += take * (touch + level * step)
        remaining -= take
        level += 1
    return cash / qty
