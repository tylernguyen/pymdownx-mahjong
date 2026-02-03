"""Shared utility functions for pymdownx-mahjong."""

from __future__ import annotations

from typing import Any

from .parser import Hand, MahjongParser, ParseError


def parse_block_content(content: str) -> tuple[str, dict[str, Any]]:
    """Parse block content into notation and options.

    Supports multiple formats:
    1. Simple: just the notation string
    2. YAML-style: key: value pairs (hand:, title:, dora:, draw:, etc.)
    3. Mixed: notation on first line, then key: value options

    Args:
        content: Block content string

    Returns:
        Tuple of (notation, options dict)
    """
    options: dict[str, Any] = {}
    notation = ""

    lines = content.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if line is a key: value pair
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip().strip("\"'")

            if key == "hand":
                notation = value
            elif key == "title":
                options["title"] = value
            elif key == "dora":
                options["dora"] = value
            elif key == "uradora":
                options["uradora"] = value
            elif key == "draw":
                options["draw"] = value
            else:
                # Unknown key - might be notation if no notation yet
                if not notation:
                    notation = line
        else:
            # Line without colon - treat as notation if none yet
            if not notation:
                notation = line

    return notation, options


def apply_hand_options(hand: Hand, parser: MahjongParser, options: dict[str, Any]) -> None:
    """Apply parsed options (dora, uradora, draw) to a hand.

    Args:
        hand: The Hand object to modify
        parser: Parser instance to parse option values
        options: Options dict from parse_block_content
    """
    if "dora" in options:
        try:
            dora_hand = parser.parse(options["dora"])
            hand.dora_indicators = dora_hand.all_tiles
        except ParseError:
            pass

    if "uradora" in options:
        try:
            uradora_hand = parser.parse(options["uradora"])
            hand.uradora_indicators = uradora_hand.all_tiles
        except ParseError:
            pass

    if "draw" in options:
        try:
            draw_hand = parser.parse(options["draw"])
            if draw_hand.closed_tiles:
                hand.draw_tile = draw_hand.closed_tiles[0]
        except ParseError:
            pass
