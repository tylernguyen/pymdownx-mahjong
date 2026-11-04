"""Tests for the stylesheet."""

from pathlib import Path

import pytest

from pymdownx_mahjong.tiles import TILE_DATABASE

CSS = (Path(__file__).parent.parent / "pymdownx_mahjong" / "css" / "mahjong.css").read_text()


@pytest.mark.parametrize(("suit", "number"), [key for key in TILE_DATABASE if key[1] not in (0, 5) or key[0] == "z"])
def test_same_tile_highlight_covers_each_tile(suit, number):
    selector = f'[data-tile="{number}{suit}"]'

    assert f".mahjong-table:has({selector}:hover) {selector}" in CSS


@pytest.mark.parametrize("suit", ["m", "p", "s"])
def test_same_tile_highlight_treats_a_red_five_as_a_five(suit):
    fives = f':is([data-tile="5{suit}"], [data-tile="0{suit}"])'

    assert f".mahjong-table:has({fives}:hover) {fives}" in CSS
