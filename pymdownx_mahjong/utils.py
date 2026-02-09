"""Shared utility functions for pymdownx-mahjong."""

from __future__ import annotations

from typing import Any

from .parser import Hand, MahjongParser, ParseError


def parse_block_content(content: str) -> tuple[str, dict[str, Any]]:
    """Parse block content into notation and options.

    Supports simple notation, YAML-style key: value pairs, or a mix of both.
    """
    options: dict[str, Any] = {}
    notation = ""

    lines = content.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip().strip("\"'")

            if key == "hand":
                notation = value
            elif key in ("title", "dora", "uradora", "draw"):
                options[key] = value
            elif not notation:
                notation = line
        elif not notation:
            notation = line

    return notation, options


def parse_hand_block(content: str, parser: MahjongParser) -> tuple[Hand, dict[str, Any], str]:
    """Parse a block of mahjong content into a Hand.

    Raises:
        ParseError: If the block content is invalid
    """
    notation, options = parse_block_content(content)

    if not notation:
        raise ParseError("No hand notation provided")

    hand = parser.parse(notation)

    option_errors = apply_hand_options(hand, parser, options)
    if option_errors:
        raise ParseError("; ".join(option_errors))

    return hand, options, notation


def apply_hand_options(hand: Hand, parser: MahjongParser, options: dict[str, Any]) -> list[str]:
    """Apply parsed options (dora, uradora, draw) to a hand. Returns error messages."""
    errors: list[str] = []
    if "dora" in options:
        try:
            dora_hand = parser.parse(options["dora"])
            hand.dora_indicators = dora_hand.all_tiles
        except ParseError as e:
            errors.append(f"Invalid dora notation: {e}")

    if "uradora" in options:
        try:
            uradora_hand = parser.parse(options["uradora"])
            hand.uradora_indicators = uradora_hand.all_tiles
        except ParseError as e:
            errors.append(f"Invalid uradora notation: {e}")

    if "draw" in options:
        try:
            draw_hand = parser.parse(options["draw"])
            if draw_hand.closed_tiles:
                hand.draw_tile = draw_hand.closed_tiles[0]
        except ParseError as e:
            errors.append(f"Invalid draw notation: {e}")

    return errors
