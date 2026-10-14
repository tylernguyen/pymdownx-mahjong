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


_SOURCE_MAP: Final[dict[str, MeldSource]] = {
    "<": MeldSource.LEFT,
    "^": MeldSource.ACROSS,
    ">": MeldSource.RIGHT,
}


@dataclass
class Tile:
    """Represents a single mahjong tile."""

    suit: str  # m, p, s, z (empty for a face-down tile)
    number: int  # 0-9 for suited, 1-7 for honors
    is_rotated: bool = False
    is_added: bool = False
    is_back: bool = False  # face-down tile (notation: Xz)

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
    ura_indicators: list[Tile] = field(default_factory=list)
    waits: list[Tile] = field(default_factory=list)
    draw_tile: Tile | None = None

    @property
    def all_tiles(self) -> list[Tile]:
        """Get all tiles in the hand (including draw tile if present)."""
        tiles = list(self.closed_tiles)
        for meld in self.melds:
            tiles.extend(meld.tiles)
        if self.draw_tile:
            tiles.append(self.draw_tile)
        return tiles


def _rank(tile: Tile) -> int:
    """A tile's rank, with a red 5 (0) ranked as a 5."""
    return 5 if tile.number == 0 else tile.number


class ParseError(Exception):
    """Exception raised when parsing fails."""


class MahjongParser:
    """Parser for MPSZ mahjong notation.

    Supports notation like:
    - Basic: 123m456p789s1122z
    - Red dora: 1230m (0 = red 5)
    - Melds: (123m<) for chi, [1111m] for closed kan
    - Separators: | before melds, _ for gaps
    """

    TILE_GROUP_PATTERN: Final[re.Pattern[str]] = re.compile(r"([0-9]+)([mpsz])")
    # Tile groups: ranks + suit, where a rank is a digit or 'X' (a face-down tile).
    # 'X' is only valid with the z suit (Xz); e.g. 123m, 1234567z, Xz, or 1234567Xz.
    _TILE_OR_BACK_PATTERN: Final[re.Pattern[str]] = re.compile(r"([0-9X]+)([mpsz])")

    # For added kan, use + to mark the added tile: (111+1m<)
    MELD_PATTERN: Final[re.Pattern[str]] = re.compile(r"(\[|\()([0-9]+)(\+)?([0-9])?([mpsz])([<^>])?(\]|\))")

    def __init__(self) -> None:
        self.errors: list[str] = []

    def parse(self, notation: str) -> Hand:
        """Parse a hand notation string into a Hand object.

        Raises:
            ParseError: If the notation is invalid
        """
        self.errors = []
        hand = Hand()

        notation = notation.strip()

        # Extract melds first (they're unambiguous with brackets)
        hand.melds = self._parse_melds(notation)

        # Remove meld notation to get closed tiles
        closed_part = self.MELD_PATTERN.sub("", notation).strip()
        hand.closed_tiles = self._parse_tiles(closed_part)

        self._validate_tile_counts(hand)

        if self.errors:
            raise ParseError("; ".join(self.errors))

        return hand

    def parse_tiles(self, notation: str) -> list[Tile]:
        """Parse a simple tile notation string.

        Raises:
            ParseError: If the notation is invalid
        """
        self.errors = []
        tiles = self._parse_tiles(notation)
        if self.errors:
            raise ParseError("; ".join(self.errors))
        return tiles

    def _parse_tiles(self, notation: str) -> list[Tile]:
        """Parse tile notation into a list of Tile objects."""
        tiles: list[Tile] = []

        clean = notation.replace("_", "").replace(" ", "").replace("|", "")
        if not clean:
            return tiles

        invalid_notation = False
        last_end = 0
        matched_any = False

        for match in self._TILE_OR_BACK_PATTERN.finditer(clean):
            if match.start() != last_end:
                invalid_notation = True
            matched_any = True

            ranks = match.group(1)
            suit = match.group(2)

            for rank in ranks:
                if rank == "X":  # face-down tile — only valid with the z suit (Xz)
                    if suit != "z":
                        self.errors.append(f"Invalid tile: X{suit}")
                        continue
                    tiles.append(Tile(suit="", number=0, is_back=True))
                    continue

                number = int(rank)

                if get_tile_info(suit, number) is None:
                    self.errors.append(f"Invalid tile: {number}{suit}")
                    continue

                tiles.append(Tile(suit=suit, number=number))

            last_end = match.end()

        if not matched_any or last_end != len(clean):
            invalid_notation = True

        if invalid_notation:
            self.errors.append(f"Invalid tile notation: {clean}")

        return tiles

    def _parse_melds(self, notation: str) -> list[Meld]:
        """Parse meld notation from a hand string.

        For added kan (shouminkan), use + before the added tile: (111+1m<)
        """
        melds: list[Meld] = []

        for match in self.MELD_PATTERN.finditer(notation):
            open_bracket = match.group(1)
            base_numbers = match.group(2)
            plus_marker = match.group(3)
            added_number = match.group(4)
            suit = match.group(5)
            source_char = match.group(6) or ""
            close_bracket = match.group(7)

            if (open_bracket == "[" and close_bracket != "]") or (open_bracket == "(" and close_bracket != ")"):
                self.errors.append(f"Mismatched brackets in meld: {match.group(0)}")
                continue

            if plus_marker and not added_number:
                self.errors.append(f"Added kan notation requires digit after '+': {match.group(0)}")
                continue

            if plus_marker and added_number:
                tile_notation = base_numbers + added_number + suit
                is_added_kan = True
            else:
                tile_notation = base_numbers + suit
                is_added_kan = False

            tiles = self._parse_tiles(tile_notation)

            if not tiles:
                continue

            meld_type = self._classify_meld(match.group(0), tiles, open_bracket == "[", is_added_kan, source_char)
            if meld_type is None:
                continue

            source = _SOURCE_MAP.get(source_char, MeldSource.SELF)

            # Rotated tile position indicates which player the tile was called from:
            #   < (kamicha): index 0, ^ (toimen): index 1, > (shimocha): last position
            if source != MeldSource.SELF and tiles:
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
        self, meld: str, tiles: list[Tile], is_closed: bool, is_added_kan: bool, source_char: str
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

        self.errors.append(f"{error}: {meld}")
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

    def validate(self, hand: Hand) -> None:
        """Validate tile counts for a hand changed after parse(), e.g. with a draw tile.

        Raises:
            ParseError: If any tile appears more than 4 times
        """
        self.errors = []
        self._validate_tile_counts(hand)
        if self.errors:
            raise ParseError("; ".join(self.errors))

    def _validate_tile_counts(self, hand: Hand) -> None:
        """Validate that no tile appears more than 4 times."""
        # A red 5 (0) replaces one of the four 5s, so it counts as a 5. Face-down tiles
        # are unknown, so they don't count toward the per-tile limit.
        tiles = [t for t in hand.all_tiles if not t.is_back]
        counts = Counter((t.suit, _rank(t)) for t in tiles)
        has_red = {t.suit for t in tiles if t.number == 0}

        for (suit, number), count in counts.items():
            if count > 4:
                red_note = ", including red 5s" if number == 5 and suit in has_red else ""
                self.errors.append(
                    f"Invalid tile count: {number}{suit} appears {count} times (max 4{red_note})"
                )


def parse_hand(notation: str) -> Hand:
    """Convenience function to parse a hand notation."""
    parser = MahjongParser()
    return parser.parse(notation)
