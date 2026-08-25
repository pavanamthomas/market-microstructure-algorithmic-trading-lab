"""Order-book invariants: spread, executable price, FIFO, microprice."""

from __future__ import annotations

import pytest

from microstructure.book import (
    LimitOrderBook,
    Side,
    rectangular_book,
    rectangular_vwap,
)


def test_spread_nonnegative_and_mid_inside() -> None:
    book = rectangular_book(100.0, 0.01, half_spread_ticks=1, levels=3, size_per_level=4)
    assert book.spread is not None and book.spread >= 0
    assert book.best_bid == pytest.approx(99.99)
    assert book.best_ask == pytest.approx(100.01)
    assert book.mid == pytest.approx(100.0)
    assert book.best_bid < book.mid < book.best_ask


def test_market_buy_cannot_print_below_best_ask() -> None:
    book = rectangular_book(50.0, 0.01, 1, 4, 10)
    ask = book.best_ask
    assert ask is not None
    fill = book.market(Side.BUY, 25)
    assert fill.fully_filled
    assert fill.best_touch == pytest.approx(ask)
    assert fill.vwap >= ask - 1e-12
    assert fill.walked_levels == 3


def test_market_sell_cannot_print_above_best_bid() -> None:
    book = rectangular_book(50.0, 0.01, 1, 4, 10)
    bid = book.best_bid
    assert bid is not None
    fill = book.market(Side.SELL, 12)
    assert fill.vwap <= bid + 1e-12
    assert fill.best_touch == pytest.approx(bid)


def test_walk_matches_independent_rectangular_formula() -> None:
    tick, size, qty = 0.01, 10, 25
    book = rectangular_book(100.0, tick, 1, 5, size)
    ask = book.best_ask
    assert ask is not None
    fill = book.market(Side.BUY, qty)
    closed = rectangular_vwap(ask, tick, size, qty, Side.BUY)
    assert fill.vwap == pytest.approx(closed)
    # 10 @ 100.01, 10 @ 100.02, 5 @ 100.03
    expected = (10 * 100.01 + 10 * 100.02 + 5 * 100.03) / 25
    assert closed == pytest.approx(expected)


def test_fifo_at_a_price() -> None:
    book = LimitOrderBook(tick_size=0.01)
    book.rest_limit(Side.SELL, 10.00, 3)
    book.rest_limit(Side.SELL, 10.00, 7)
    book.rest_limit(Side.BUY, 9.90, 10)
    fill = book.market(Side.BUY, 3)
    assert fill.quantity == 3
    assert fill.vwap == pytest.approx(10.00)
    # The first lot is gone; 7 remain at the ask.
    assert book.ask_size_at_touch() == 7
    fill2 = book.market(Side.BUY, 7)
    assert fill2.quantity == 7
    assert book.best_ask is None


def test_microprice_pulled_toward_thin_side() -> None:
    book = LimitOrderBook(0.01)
    book.rest_limit(Side.BUY, 9.99, 90)
    book.rest_limit(Side.SELL, 10.01, 10)
    mid = book.mid
    micro = book.microprice()
    assert mid is not None and micro is not None
    # Thick bid ⇒ microprice closer to the ask than the mid is.
    assert micro > mid
    assert book.imbalance() == pytest.approx(0.8)


def test_marketable_limit_takes_then_rests() -> None:
    book = rectangular_book(10.0, 0.01, 1, 2, 5)
    fill = book.marketable_limit(Side.BUY, 10.01, 8)
    # 5 available at 10.01; remainder 3 rests at 10.01, crossing no further.
    assert fill.quantity == 5
    assert fill.remaining == 3
    assert book.best_bid == pytest.approx(10.01)
    assert book.bid_size_at_touch() == 3


def test_resting_cross_is_rejected() -> None:
    book = rectangular_book(10.0, 0.01, 1, 1, 5)
    with pytest.raises(ValueError, match="cross"):
        book.rest_limit(Side.BUY, 10.01, 1)
