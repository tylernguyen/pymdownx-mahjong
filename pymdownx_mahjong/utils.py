"""Shared utility functions for pymdownx-mahjong."""

from __future__ import annotations

from typing import Any, Final

from .parser import (
    MAX_DORA_INDICATORS,
    OPPONENT_SEATS,
    SEAT_WINDS,
    Hand,
    MahjongParser,
    ParseError,
    face_down_tiles,
    parse_int,
)

_OPTION_KEYS: Final[tuple[str, ...]] = (
    "title",
    "dora",
    "draw",
    "discards",
    "honba",
    "riichi",
    "seat",
    "score",
    "round",
    "remaining",
)

# Keys another player on the board accepts after their seat prefix, e.g. shimo.hand.
_PLAYER_KEYS: Final[tuple[str, ...]] = ("hand", "draw", "discards", "seat", "score")

# Accepted seat values: full names and their initials, e.g. "east" or "E".
_SEAT_VALUES: Final[dict[str, str]] = {key: wind for wind in SEAT_WINDS for key in (wind, wind[0])}

# The most tiles that can be left in the wall (136 - 14 dead wall - 52 dealt).
_MAX_REMAINING: Final = 70

# The other players always hold a 13-tile hand (each meld counts as 3, kans included);
# whatever their notation leaves out (all 13 without a hand option) is face-down.
_HAND_SIZE: Final = 13


def parse_block_content(content: str) -> tuple[str, dict[str, Any]]:
    """Parse block content into notation and options.

    Supports simple notation, YAML-style key: value pairs, or a mix of both.

    Raises:
        ParseError: On an unknown option key, a repeated option or a second hand notation
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
            elif key in options:
                raise ParseError(f"Option '{key}' given more than once: {line}")
            elif key in _OPTION_KEYS:
                options[key] = value
            elif "." in key:
                prefix, _, sub = key.partition(".")
                if prefix not in OPPONENT_SEATS:
                    raise ParseError(
                        f"Unknown player '{prefix}' in '{key}' (expected one of: {', '.join(OPPONENT_SEATS)})"
                    )
                if sub not in _PLAYER_KEYS:
                    raise ParseError(f"Unknown option '{key}' (expected one of: {', '.join(_PLAYER_KEYS)})")
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

    player_options = _split_player_options(options)

    if notation:
        hand = parser.parse(notation)
    elif "discards" in options or player_options:
        # A discard pile, or the other players on a board, may be shown without a hand.
        hand = Hand()
    else:
        raise ParseError("No hand notation provided")

    option_errors = apply_hand_options(hand, parser, options)

    for seat, seat_options in player_options.items():
        try:
            opponent = _parse_opponent_hand(seat_options.get("hand", ""), parser)
        except ParseError as e:
            option_errors.append(f"{seat}: {e}")
            continue
        option_errors.extend(f"{seat}: {error}" for error in apply_hand_options(opponent, parser, seat_options))
        hand.opponents[seat] = opponent

    if option_errors:
        raise ParseError("; ".join(option_errors))

    if hand.opponents:
        _assign_seat_winds(hand)

    # One check over everything on show: every player's hand and discards, and the dora.
    parser.validate_table(hand)

    return hand, options, notation


def _parse_opponent_hand(notation: str, parser: MahjongParser) -> Hand:
    """Parse another player's hand, filling it out to 13 tiles with face-down tiles ahead of
    any revealed ones: e.g. "(777z<)" is 10 hidden tiles and a pon, and no hand at all is
    13 hidden tiles.

    Raises:
        ParseError: If the notation is invalid
    """
    notation = notation.strip()
    hand = parser.parse(notation) if notation else Hand()
    hidden = _HAND_SIZE - 3 * len(hand.melds) - len(hand.closed_tiles)
    if hidden < 0:
        raise ParseError(
            f"Hand has {_HAND_SIZE - hidden} tiles counting each meld as 3 "
            f"(expected at most {_HAND_SIZE}; give a 14th as the draw)"
        )
    hand.closed_tiles = face_down_tiles(hidden) + hand.closed_tiles
    return hand


def _split_player_options(options: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Group dotted options (shimo.hand, kami.score, ...) by seat, in turn order."""
    grouped: dict[str, dict[str, Any]] = {}
    for seat in OPPONENT_SEATS:
        prefix = f"{seat}."
        seat_options = {key.removeprefix(prefix): value for key, value in options.items() if key.startswith(prefix)}
        if seat_options:
            grouped[seat] = seat_options
    return grouped


def _assign_seat_winds(hand: Hand) -> None:
    """Give the other players the winds that follow the bottom player's, unless set,
    and reject two players sharing a wind.

    Raises:
        ParseError: If two players have the same seat wind
    """
    if hand.seat_wind:
        start = SEAT_WINDS.index(hand.seat_wind)
        for offset, seat in enumerate(OPPONENT_SEATS, start=1):
            opponent = hand.opponents.get(seat)
            if opponent and not opponent.seat_wind:
                opponent.seat_wind = SEAT_WINDS[(start + offset) % len(SEAT_WINDS)]

    seats = {"hand": hand.seat_wind} | {seat: opponent.seat_wind for seat, opponent in hand.opponents.items()}
    by_wind: dict[str, list[str]] = {}
    for seat, wind in seats.items():
        if wind:
            by_wind.setdefault(wind, []).append(seat)
    duplicates = [f"{wind} ({', '.join(names)})" for wind, names in by_wind.items() if len(names) > 1]
    if duplicates:
        raise ParseError(f"Seat wind given to more than one player: {'; '.join(duplicates)}")


def apply_hand_options(hand: Hand, parser: MahjongParser, options: dict[str, Any]) -> list[str]:
    """Apply parsed options (dora, draw, discards, honba, riichi, seat, score, round, remaining) to a hand.
    Returns error messages."""
    errors: list[str] = []
    if "dora" in options:
        try:
            tiles = parser.parse_tiles(options["dora"])
            if len(tiles) > MAX_DORA_INDICATORS:
                errors.append(f"Invalid dora notation: expected at most {MAX_DORA_INDICATORS} tiles, got {len(tiles)}")
            else:
                hand.dora_indicators = tiles
        except ParseError as e:
            errors.append(f"Invalid dora notation: {e}")

    if "draw" in options:
        try:
            tiles = parser.parse_tiles(options["draw"])
            if len(tiles) > 1:
                errors.append(f"Invalid draw notation: expected 1 tile, got {len(tiles)}")
            elif tiles:
                hand.draw_tile = tiles[0]
        except ParseError as e:
            errors.append(f"Invalid draw notation: {e}")

    if "discards" in options:
        try:
            hand.discards = parser.parse_discards(options["discards"])
        except ParseError as e:
            errors.append(f"Invalid discards notation: {e}")

    for key in ("honba", "riichi"):
        if key in options:
            count = parse_int(options[key])
            if count is not None:
                setattr(hand, key, count)
            else:
                errors.append(f"Invalid {key} value: expected a non-negative integer, got {options[key]!r}")

    if "seat" in options:
        value = options["seat"]
        wind = _SEAT_VALUES.get(value.lower())
        if wind:
            hand.seat_wind = wind
        else:
            errors.append(
                f"Invalid seat value: expected one of east, south, west, north (or E, S, W, N), got {value!r}"
            )

    if "score" in options:
        score = parse_int(options["score"], signed=True)
        if score is not None:
            hand.score = score
        else:
            errors.append(f"Invalid score value: expected an integer, got {options['score']!r}")

    if "round" in options:
        value = options["round"]
        # "S2", "south 2" or "south2": a wind, then a hand number 1-4.
        wind_part, number_part = value[:-1].strip().lower(), value[-1:]
        wind = _SEAT_VALUES.get(wind_part)
        if wind and number_part and number_part in "1234":
            hand.round_wind = wind
            hand.round_number = int(number_part)
        else:
            errors.append(f"Invalid round value: expected a wind and a number 1-4 (e.g. E1, south 2), got {value!r}")

    if "remaining" in options:
        remaining = parse_int(options["remaining"])
        if remaining is not None and remaining <= _MAX_REMAINING:
            hand.remaining = remaining
        else:
            errors.append(
                f"Invalid remaining value: expected an integer from 0 to {_MAX_REMAINING}, got {options['remaining']!r}"
            )

    return errors
