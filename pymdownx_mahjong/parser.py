"""MPSZ notation parser for Riichi Mahjong hands."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Final

from .tiles import get_tile_info

if TYPE_CHECKING:
    from .tiles import TileInfo


class MeldType(Enum):
    """Types of called tile groups (melds)."""

    CHI = "chi"
    PON = "pon"
    KAN_OPEN = "kan_open"
    KAN_CLOSED = "kan_closed"
    KAN_ADDED = "kan_added"


class MeldSource(Enum):
    """Source direction for called tiles."""

    LEFT = "<"  # Kamicha
    ACROSS = "^"  # Toimen
    RIGHT = ">"  # Shimocha
    SELF = ""  # Self-drawn


# Seat winds, in turn order.
SEAT_WINDS: Final = ("east", "south", "west", "north")

# The other players on a board, in turn order from the bottom player: right, across, left.
OPPONENT_SEATS: Final = ("shimo", "toimen", "kami")

# One dora indicator plus up to four kan dora.
MAX_DORA_INDICATORS: Final = 5


@dataclass
class Tile:
    """Represents a single mahjong tile."""

    suit: str  # m, p, s, z (empty for a face-down tile)
    number: int  # 0-9 for suited, 1-7 for honors
    is_rotated: bool = False
    is_added: bool = False
    is_back: bool = False  # face-down tile (notation: Xz)
    is_tsumogiri: bool = False  # discarded straight from the draw (discard marker: t)
    is_called: bool = False  # discard called by another player (discard marker: c)

    @property
    def notation(self) -> str:
        return f"{self.number}{self.suit}"

    @property
    def info(self) -> TileInfo | None:
        return get_tile_info(self.suit, self.number)

    @property
    def display_name(self) -> str:
        info = self.info
        return info.display_name if info else f"Unknown ({self.notation})"


@dataclass
class Meld:
    """Represents a called tile group (meld)."""

    tiles: list[Tile]
    meld_type: MeldType
    source: MeldSource = MeldSource.SELF

    @property
    def is_open(self) -> bool:
        return self.meld_type != MeldType.KAN_CLOSED


@dataclass
class Hand:
    """Represents a complete mahjong hand."""

    closed_tiles: list[Tile] = field(default_factory=list)
    melds: list[Meld] = field(default_factory=list)
    dora_indicators: list[Tile] = field(default_factory=list)
    draw_tile: Tile | None = None
    discards: list[Tile] = field(default_factory=list)
    honba: int = 0
    riichi: int = 0  # riichi sticks on the table
    seat_wind: str | None = None  # one of SEAT_WINDS
    seat_wind_inferred: bool = False  # worked out from another player's wind, not given
    score: int | None = None
    round_wind: str | None = None  # one of SEAT_WINDS
    round_number: int | None = None  # 1-4
    remaining: int | None = None  # tiles left in the wall
    opponents: dict[str, Hand] = field(default_factory=dict)  # keyed by OPPONENT_SEATS

    @property
    def all_tiles(self) -> list[Tile]:
        """Get all tiles in the hand (including draw tile if present)."""
        tiles = list(self.closed_tiles)
        for meld in self.melds:
            tiles.extend(meld.tiles)
        if self.draw_tile:
            tiles.append(self.draw_tile)
        return tiles


def parse_int(text: str, *, signed: bool = False) -> int | None:
    """Parse a plain ASCII integer (with a leading '-' if ``signed``), or None if ``text``
    isn't one; e.g. rejects '+1', '1.5', '25,000' and full-width digits."""
    digits = text.removeprefix("-") if signed else text
    return int(text) if digits.isascii() and digits.isdigit() else None


def face_down_tiles(count: int) -> list[Tile]:
    """Make ``count`` face-down tiles."""
    return [Tile(suit="", number=0, is_back=True) for _ in range(count)]


def _rank(tile: Tile) -> int:
    """A tile's rank, with a red 5 (0) ranked as a 5."""
    return 5 if tile.number == 0 else tile.number


def _strip_separators(notation: str) -> str:
    """Remove the characters allowed between tiles for readability."""
    return notation.replace("_", "").replace(" ", "").replace("|", "")


class ParseError(Exception):
    """Exception raised when parsing fails."""


def raise_if_errors(errors: list[str]) -> None:
    """Raise a ParseError combining ``errors``, if there are any."""
    if errors:
        raise ParseError("; ".join(errors))


class MahjongParser:
    """Parser for MPSZ mahjong notation.

    Supports notation like:
    - Basic: 123m456p789s1122z
    - Red dora: 1230m (0 = red 5)
    - Melds: (123m<) for chi, [1111m] for closed kan
    - Separators: |, _, and spaces are ignored and may be used for readability
    - Face-down tiles: Xz, e.g. XXX123z (not in melds)
    """

    # Tile groups: ranks + suit, where a rank is a digit or 'X' (a face-down tile).
    # 'X' is only valid with the z suit (Xz); e.g. 123m, 1234567z, Xz, or 1234567Xz.
    _TILE_OR_BACK_PATTERN: Final[re.Pattern[str]] = re.compile(r"([0-9X]+)([mpsz])")

    # Discards also allow per-tile prefix markers before a rank: r (riichi, rotated),
    # t (tsumogiri), c (called away); e.g. 1r9m, rt5p, c7z.
    _DISCARD_PATTERN: Final[re.Pattern[str]] = re.compile(r"((?:[rtc]*[0-9X])+)([mpsz])")

    # For added kan, use + to mark the added tile: (111+1m<)
    MELD_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"(?P<open>\[|\()(?P<base>[0-9]+)(?P<plus>\+)?(?P<added>[0-9])?(?P<suit>[mpsz])(?P<source>[<^>])?(?P<close>\]|\))"
    )

    def parse(self, notation: str) -> Hand:
        """Parse a hand notation string into a Hand object.

        Raises:
            ParseError: If the notation is invalid
        """
        errors: list[str] = []
        hand = Hand()

        notation = notation.strip()

        # Extract melds first (they're unambiguous with brackets)
        hand.melds = self._parse_melds(notation, errors)

        # Remove meld notation to get closed tiles
        closed_part = self.MELD_PATTERN.sub("", notation).strip()
        number = parse_int(_strip_separators(closed_part))
        if number is not None:
            # Digits with no suit: most likely a forgotten suit.
            errors.append(f"Invalid tile notation: {number} (did you forget a suit?)")
        else:
            hand.closed_tiles = self._parse_tiles(closed_part, errors)

        self._validate_tile_counts(hand, errors)

        raise_if_errors(errors)

        return hand

    def parse_tiles(self, notation: str) -> list[Tile]:
        """Parse a simple tile notation string.

        Raises:
            ParseError: If the notation is invalid
        """
        errors: list[str] = []
        tiles = self._parse_tiles(notation, errors)
        raise_if_errors(errors)
        return tiles

    def parse_discards(self, notation: str) -> list[Tile]:
        """Parse discard pile notation, which allows r/t/c markers before a rank.

        After riichi a player can only discard the tile they draw, so every discard after
        the riichi tile is tsumogiri, whether or not it's marked.

        Raises:
            ParseError: If the notation is invalid
        """
        errors: list[str] = []
        tiles = self._parse_tiles(notation, errors, discards=True)
        raise_if_errors(errors)
        riichi = next((i for i, tile in enumerate(tiles) if tile.is_rotated), None)
        if riichi is not None:
            for tile in tiles[riichi + 1 :]:
                tile.is_tsumogiri = True
        return tiles

    def _parse_tiles(self, notation: str, errors: list[str], *, discards: bool = False) -> list[Tile]:
        """Parse tile notation into a list of Tile objects, appending any problems to errors."""
        tiles: list[Tile] = []
        pattern = self._DISCARD_PATTERN if discards else self._TILE_OR_BACK_PATTERN

        clean = _strip_separators(notation)
        if not clean:
            return tiles

        invalid_notation = False
        last_end = 0
        matched_any = False

        for match in pattern.finditer(clean):
            if match.start() != last_end:
                invalid_notation = True
            matched_any = True

            ranks = match.group(1)
            suit = match.group(2)

            markers = ""
            for rank in ranks:
                if rank in "rtc":
                    markers += rank
                    continue

                tile = self._make_tile(rank, suit)
                if tile is None:
                    errors.append(f"Invalid tile: {rank}{suit}")
                else:
                    self._apply_markers(tile, markers)
                    tiles.append(tile)
                markers = ""

            last_end = match.end()

        if not matched_any or last_end != len(clean):
            invalid_notation = True

        if invalid_notation:
            errors.append(f"Invalid tile notation: {clean}")

        return tiles

    @staticmethod
    def _make_tile(rank: str, suit: str) -> Tile | None:
        """Make the tile for a rank (a digit, or X for a face-down tile, which is only valid
        with the z suit) and suit, or None if there is no such tile."""
        if rank == "X":
            return face_down_tiles(1)[0] if suit == "z" else None
        number = int(rank)
        return Tile(suit=suit, number=number) if get_tile_info(suit, number) else None

    @staticmethod
    def _apply_markers(tile: Tile, markers: str) -> None:
        """Set discard marker flags (r, t, c) on a tile."""
        tile.is_rotated = "r" in markers
        tile.is_tsumogiri = "t" in markers
        tile.is_called = "c" in markers

    def _parse_melds(self, notation: str, errors: list[str]) -> list[Meld]:
        """Parse meld notation from a hand string.

        For added kan (shouminkan), use + before the added tile: (111+1m<)
        """
        melds: list[Meld] = []

        for match in self.MELD_PATTERN.finditer(notation):
            is_closed = match["open"] == "["
            is_added_kan = match["plus"] is not None
            source_char = match["source"] or ""

            if is_closed != (match["close"] == "]"):
                errors.append(f"Mismatched brackets in meld: {match[0]}")
                continue

            if is_added_kan and not match["added"]:
                errors.append(f"Added kan notation requires digit after '+': {match[0]}")
                continue

            # The base digits are greedy, so an added digit only ever follows a '+'.
            tiles = self._parse_tiles(f"{match['base']}{match['added'] or ''}{match['suit']}", errors)

            if not tiles:
                continue

            meld_type = self._classify_meld(match[0], tiles, is_closed, is_added_kan, source_char, errors)
            if meld_type is None:
                continue

            source = MeldSource(source_char)

            # Rotated tile position indicates which player the tile was called from:
            #   < (kamicha): index 0, ^ (toimen): index 1, > (shimocha): last position
            if source != MeldSource.SELF:
                if source == MeldSource.LEFT:
                    rotated_idx = 0
                elif source == MeldSource.ACROSS:
                    rotated_idx = 1
                elif meld_type == MeldType.KAN_OPEN:
                    rotated_idx = 3
                else:
                    rotated_idx = 2

                tiles[rotated_idx].is_rotated = True

                if meld_type == MeldType.KAN_ADDED:
                    tiles[-1].is_rotated = True
                    tiles[-1].is_added = True

            melds.append(Meld(tiles=tiles, meld_type=meld_type, source=source))

        return melds

    def _classify_meld(
        self, meld: str, tiles: list[Tile], is_closed: bool, is_added_kan: bool, source_char: str, errors: list[str]
    ) -> MeldType | None:
        """Determine a meld's type, recording an error and returning None if it is invalid."""
        tile_count = len(tiles)
        identical = len({(t.suit, _rank(t)) for t in tiles}) == 1

        if is_closed and source_char:
            error = "Closed kan cannot have source marker"
        elif is_closed and is_added_kan:
            error = "Closed kan cannot be an added kan"
        elif is_closed and tile_count != 4:
            error = "Closed meld must be a kan of 4 tiles"
        elif is_added_kan and tile_count != 4:
            error = "Added kan must have 4 tiles"
        elif is_added_kan and not source_char:
            error = "Added kan requires a source marker (<, ^, or >)"
        elif tile_count == 4:
            if identical:
                if is_added_kan:
                    return MeldType.KAN_ADDED
                return MeldType.KAN_CLOSED if is_closed else MeldType.KAN_OPEN
            error = "Kan must be 4 identical tiles"
        elif tile_count == 3:
            if self._is_sequence(tiles):
                if source_char in ("", "<"):
                    return MeldType.CHI
                error = "Chi can only be called from the left (<)"
            elif identical:
                return MeldType.PON
            else:
                error = "Meld must be a sequence or 3 identical tiles"
        else:
            error = f"Invalid meld size: {tile_count} tiles"

        errors.append(f"{error}: {meld}")
        return None

    def _is_sequence(self, tiles: list[Tile]) -> bool:
        """Check if tiles form a consecutive sequence (chi)."""
        if len(tiles) != 3:
            return False

        suits = {t.suit for t in tiles}
        if len(suits) != 1 or "z" in suits:
            return False

        numbers = sorted(_rank(t) for t in tiles)

        return numbers[1] == numbers[0] + 1 and numbers[2] == numbers[1] + 1

    def validate_table(self, hand: Hand) -> None:
        """Validate tile counts for a hand changed after parse() (e.g. with a draw tile,
        discards or dora indicators) and any other players on its table: every hand and
        discard pile, plus the dora indicators.

        A called discard (``c``) moved into the caller's meld, so it's counted there rather
        than in the pile; this also keeps a caller shown on the table from counting it twice.

        Raises:
            ParseError: If any tile appears more than 4 times
        """
        tiles = list(hand.dora_indicators)
        for player in (hand, *hand.opponents.values()):
            tiles.extend(player.all_tiles)
            tiles.extend(tile for tile in player.discards if not tile.is_called)
        errors: list[str] = []
        self._validate_tile_list(tiles, errors)
        raise_if_errors(errors)

    # The original name for validate_table, kept for existing callers.
    validate = validate_table

    def _validate_tile_counts(self, hand: Hand, errors: list[str]) -> None:
        """Validate that no tile appears more than 4 times."""
        self._validate_tile_list(hand.all_tiles, errors)

    @staticmethod
    def _validate_tile_list(tiles: list[Tile], errors: list[str]) -> None:
        """Record an error for each tile that appears more than 4 times."""
        # A red 5 (0) replaces one of the four 5s, so it counts as a 5. Face-down tiles
        # are unknown, so they don't count toward the per-tile limit.
        tiles = [t for t in tiles if not t.is_back]
        counts = Counter((t.suit, _rank(t)) for t in tiles)
        has_red = {t.suit for t in tiles if t.number == 0}

        for (suit, number), count in counts.items():
            if count > 4:
                red_note = ", including red 5s" if number == 5 and suit in has_red else ""
                errors.append(f"Invalid tile count: {number}{suit} appears {count} times (max 4{red_note})")


def parse_hand(notation: str) -> Hand:
    """Convenience function to parse a hand notation."""
    parser = MahjongParser()
    return parser.parse(notation)
