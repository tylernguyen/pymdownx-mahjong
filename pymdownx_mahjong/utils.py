"""Shared utility functions for pymdownx-mahjong."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final

from .parser import (
    MAX_DORA_INDICATORS,
    OPPONENT_SEATS,
    SEAT_WINDS,
    Hand,
    MahjongParser,
    ParseError,
    Tile,
    face_down_tiles,
    parse_int,
    raise_if_errors,
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

    Supports simple notation, YAML-style key: value pairs, or a mix of both. A discards
    option continues onto the lines after it that are indented deeper than its key.

    Raises:
        ParseError: On an unknown option key, a repeated option or a second hand notation
    """
    options: dict[str, Any] = {}
    notation = ""
    discards_key: str | None = None  # the discards option that indented lines would continue
    discards_indent = 0

    lines = content.split("\n")

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        indent = len(raw_line) - len(raw_line.lstrip())
        if discards_key and indent > discards_indent and ":" not in line:
            options[discards_key] += f" {line}"
            continue
        discards_key = None

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

            if key.rpartition(".")[2] == "discards":
                discards_key, discards_indent = key, indent
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

    hand = parser.parse(notation) if notation else Hand()

    option_errors = apply_hand_options(hand, parser, options)

    for seat, seat_options in player_options.items():
        try:
            opponent = _parse_opponent_hand(seat_options.get("hand", ""), parser)
        except ParseError as e:
            option_errors.append(f"{seat}: {e}")
            continue
        option_errors.extend(f"{seat}: {error}" for error in apply_hand_options(opponent, parser, seat_options))
        hand.opponents[seat] = opponent

    raise_if_errors(option_errors)

    # A discard pile, or the other players on a board, may be shown without a hand.
    if not (hand.closed_tiles or hand.melds or hand.discards or hand.opponents):
        raise ParseError("No hand notation provided")

    if hand.opponents:
        _assign_seat_winds(hand)

    if _is_auto_remaining(options.get("remaining", "")):
        hand.remaining = _count_remaining(hand)

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
    """Work out every player's seat wind from any one that's given, as the winds follow turn
    order around the table. The bottom player's is flagged when inferred, so a table given only
    the other players doesn't gain a bottom area just for a wind.

    Raises:
        ParseError: If the given seat winds don't follow turn order
    """
    players = {"hand": hand, **hand.opponents}
    positions = {name: position for position, name in enumerate(("hand", *OPPONENT_SEATS))}
    given = {name: player.seat_wind for name, player in players.items() if player.seat_wind}
    if not given:
        return

    # Each given wind implies the bottom player's; winds in turn order all imply the same one.
    bottoms = {(SEAT_WINDS.index(wind) - positions[name]) % len(SEAT_WINDS) for name, wind in given.items()}
    if len(bottoms) > 1:
        listed = ", ".join(f"{name} {wind}" for name, wind in given.items())
        raise ParseError(f"Seat winds conflict: {listed}")

    bottom = bottoms.pop()
    hand.seat_wind_inferred = "hand" not in given
    for name, player in players.items():
        player.seat_wind = SEAT_WINDS[(bottom + positions[name]) % len(SEAT_WINDS)]


def _is_auto_remaining(value: str) -> bool:
    return value.lower() == "auto"


def _count_remaining(hand: Hand) -> int:
    """Count the tiles left in the wall from everything on the table.

    Every tile beyond the 13 each player was dealt came from the wall: it's now a 14th tile
    in hand, a discard, or the extra tile of a kan, whose replacement draw also shortens the
    live wall. A called discard is only counted in its caller's meld.

    Raises:
        ParseError: If the table is missing a player, the calls don't match, or too many
            tiles are on the table
    """
    missing = [seat for seat in OPPONENT_SEATS if seat not in hand.opponents]
    if missing:
        raise ParseError(f"remaining: auto needs all four players on the table (missing: {', '.join(missing)})")

    players = (hand, *hand.opponents.values())
    open_melds = sum(meld.is_open for player in players for meld in player.melds)
    called = sum(tile.is_called for player in players for tile in player.discards)
    if open_melds != called:
        raise ParseError(
            f"remaining: auto needs each called tile marked with 'c' in a discard pile "
            f"(found {open_melds} open melds and {called} called discards)"
        )

    drawn = 0
    for player in players:
        in_hand = len(player.closed_tiles) + 3 * len(player.melds) + (1 if player.draw_tile else 0)
        # A draw came from the wall even when the rest of the hand isn't shown.
        extra = max(in_hand - _HAND_SIZE, 1 if player.draw_tile else 0)
        kans = sum(len(meld.tiles) == 4 for meld in player.melds)
        discarded = sum(not tile.is_called for tile in player.discards)
        drawn += extra + kans + discarded

    remaining = _MAX_REMAINING - drawn
    if remaining < 0:
        raise ParseError(f"remaining: auto found {drawn} tiles drawn, but the wall only holds {_MAX_REMAINING}")
    return remaining


def _parse_option_tiles(key: str, parse: Callable[[str], list[Tile]], value: str) -> list[Tile]:
    """Parse an option's tile notation, naming the option in any error.

    Raises:
        ParseError: If the notation is invalid
    """
    try:
        return parse(value)
    except ParseError as e:
        raise ParseError(f"Invalid {key} notation: {e}") from e


def _parse_count(key: str, value: str) -> int:
    """Parse an option's non-negative count, naming the option in any error.

    Raises:
        ParseError: If the value isn't a non-negative integer
    """
    count = parse_int(value)
    if count is None:
        raise ParseError(f"Invalid {key} value: expected a non-negative integer, got {value!r}")
    return count


def _apply_dora(hand: Hand, parser: MahjongParser, value: str) -> None:
    tiles = _parse_option_tiles("dora", parser.parse_tiles, value)
    if len(tiles) > MAX_DORA_INDICATORS:
        raise ParseError(f"Invalid dora notation: expected at most {MAX_DORA_INDICATORS} tiles, got {len(tiles)}")
    hand.dora_indicators = tiles


def _apply_draw(hand: Hand, parser: MahjongParser, value: str) -> None:
    tiles = _parse_option_tiles("draw", parser.parse_tiles, value)
    if len(tiles) > 1:
        raise ParseError(f"Invalid draw notation: expected 1 tile, got {len(tiles)}")
    if tiles:
        hand.draw_tile = tiles[0]


def _apply_discards(hand: Hand, parser: MahjongParser, value: str) -> None:
    hand.discards = _parse_option_tiles("discards", parser.parse_discards, value)


def _apply_honba(hand: Hand, _parser: MahjongParser, value: str) -> None:
    hand.honba = _parse_count("honba", value)


def _apply_riichi(hand: Hand, _parser: MahjongParser, value: str) -> None:
    hand.riichi = _parse_count("riichi", value)


def _apply_seat(hand: Hand, _parser: MahjongParser, value: str) -> None:
    wind = _SEAT_VALUES.get(value.lower())
    if not wind:
        raise ParseError(f"Invalid seat value: expected one of east, south, west, north (or E, S, W, N), got {value!r}")
    hand.seat_wind = wind


def _apply_score(hand: Hand, _parser: MahjongParser, value: str) -> None:
    score = parse_int(value, signed=True)
    if score is None:
        raise ParseError(f"Invalid score value: expected an integer, got {value!r}")
    hand.score = score


def _apply_round(hand: Hand, _parser: MahjongParser, value: str) -> None:
    # "S2", "south 2" or "south2": a wind, then a hand number 1-4, then optionally the honba: "S2-1".
    round_part, has_honba, honba_part = (part.strip() for part in value.partition("-"))
    wind_part, number_part = round_part[:-1].strip().lower(), round_part[-1:]
    wind = _SEAT_VALUES.get(wind_part)
    honba = parse_int(honba_part) if has_honba else 0
    if not (wind and number_part and number_part in "1234" and honba is not None):
        raise ParseError(
            f"Invalid round value: expected a wind and a number 1-4, optionally followed by '-' and the honba "
            f"(e.g. E1, south 2, S2-1), got {value!r}"
        )
    hand.round_wind = wind
    hand.round_number = int(number_part)
    if has_honba:
        hand.honba = honba


def _apply_remaining(hand: Hand, _parser: MahjongParser, value: str) -> None:
    # "auto" needs the other players, so parse_hand_block counts it once they're parsed.
    if _is_auto_remaining(value):
        return
    remaining = parse_int(value)
    if remaining is None or remaining > _MAX_REMAINING:
        raise ParseError(
            f"Invalid remaining value: expected 'auto' or an integer from 0 to {_MAX_REMAINING}, got {value!r}"
        )
    hand.remaining = remaining


# How each option is applied to a hand, in the order their errors are reported.
_OPTION_APPLIERS: Final[dict[str, Callable[[Hand, MahjongParser, str], None]]] = {
    "dora": _apply_dora,
    "draw": _apply_draw,
    "discards": _apply_discards,
    "honba": _apply_honba,
    "riichi": _apply_riichi,
    "seat": _apply_seat,
    "score": _apply_score,
    "round": _apply_round,
    "remaining": _apply_remaining,
}


def apply_hand_options(hand: Hand, parser: MahjongParser, options: dict[str, Any]) -> list[str]:
    """Apply parsed options (dora, draw, discards, honba, riichi, seat, score, round, remaining) to a hand.
    Returns error messages."""
    errors: list[str] = []
    if "honba" in options and "-" in options.get("round", ""):
        errors.append(f"Honba given twice: honba: {options['honba']} and round: {options['round']}")
    for key, apply_option in _OPTION_APPLIERS.items():
        if key in options:
            try:
                apply_option(hand, parser, options[key])
            except ParseError as e:
                errors.append(str(e))
    return errors
