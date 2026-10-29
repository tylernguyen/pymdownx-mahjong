"""Shared utility functions for pymdownx-mahjong."""

from __future__ import annotations

from typing import Any, Final

from .parser import Hand, MahjongParser, ParseError

_OPTION_KEYS: Final[tuple[str, ...]] = ("title", "dora", "ura", "waits", "draw")


def parse_block_content(content: str) -> tuple[str, dict[str, Any]]:
    """Parse block content into notation and options.

    Supports simple notation, YAML-style key: value pairs, or a mix of both.

    Raises:
        ParseError: On an unknown option key or a second hand notation
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
            value = _unquote(value.strip())

            if key == "hand":
                if notation:
                    raise ParseError(f"Hand notation given more than once: {line}")
                notation = value
            elif key in _OPTION_KEYS:
                options[key] = value
            else:
                expected = ", ".join(("hand", *_OPTION_KEYS))
                raise ParseError(f"Unknown option '{key}' (expected one of: {expected})")
        elif notation:
            raise ParseError(f"Hand notation given more than once: {line}")
        else:
            notation = line

    return notation, options


def _unquote(value: str) -> str:
    """Remove one pair of matching surrounding quotes, leaving unpaired quotes intact."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


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

    if hand.draw_tile:
        # parse() checked tile counts before the draw tile was added.
        parser.validate(hand)

    return hand, options, notation


def apply_hand_options(hand: Hand, parser: MahjongParser, options: dict[str, Any]) -> list[str]:
    """Apply parsed options (dora, ura, draw) to a hand. Returns error messages."""
    errors: list[str] = []
    if "dora" in options:
        try:
            hand.dora_indicators = parser.parse_tiles(options["dora"])
        except ParseError as e:
            errors.append(f"Invalid dora notation: {e}")

    if "ura" in options:
        try:
            hand.ura_indicators = parser.parse_tiles(options["ura"])
        except ParseError as e:
            errors.append(f"Invalid ura notation: {e}")

    if "draw" in options:
        try:
            tiles = parser.parse_tiles(options["draw"])
            if len(tiles) > 1:
                errors.append(f"Invalid draw notation: expected 1 tile, got {len(tiles)}")
            elif tiles:
                hand.draw_tile = tiles[0]
        except ParseError as e:
            errors.append(f"Invalid draw notation: {e}")

    if "waits" in options:
        try:
            hand.waits = parser.parse_tiles(options["waits"])
        except ParseError as e:
            errors.append(f"Invalid waits notation: {e}")

    return errors
