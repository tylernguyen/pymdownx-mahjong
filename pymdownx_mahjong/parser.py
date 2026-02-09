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

    suit: str  # m, p, s, z
    number: int  # 0-9 for suited, 1-7 for honors
    is_rotated: bool = False
    is_added: bool = False

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
    uradora_indicators: list[Tile] = field(default_factory=list)
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

    @property
    def total_tile_count(self) -> int:
        count = len(self.closed_tiles) + sum(len(m.tiles) for m in self.melds)
        if self.draw_tile:
            count += 1
        return count


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

        for match in self.TILE_GROUP_PATTERN.finditer(clean):
            if match.start() != last_end:
                invalid_notation = True
            matched_any = True
            numbers = match.group(1)
            suit = match.group(2)

            for num_char in numbers:
                number = int(num_char)

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

            is_closed = open_bracket == "[" and close_bracket == "]"
            tile_count = len(tiles)

            if is_closed and source_char:
                self.errors.append(f"Closed kan cannot have source marker: {match.group(0)}")
                continue

            if is_added_kan and tile_count == 4:
                meld_type = MeldType.KAN_ADDED
            elif is_closed and tile_count == 4:
                meld_type = MeldType.KAN_CLOSED
            elif tile_count == 4:
                meld_type = MeldType.KAN_OPEN
            elif tile_count == 3:
                meld_type = MeldType.CHI if self._is_sequence(tiles) else MeldType.PON
            else:
                self.errors.append(f"Invalid meld size: {tile_count} tiles")
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

    def _is_sequence(self, tiles: list[Tile]) -> bool:
        """Check if tiles form a consecutive sequence (chi)."""
        if len(tiles) != 3:
            return False

        suits = {t.suit for t in tiles}
        if len(suits) != 1 or "z" in suits:
            return False

        # Red dora 0 is treated as 5
        numbers = sorted(5 if t.number == 0 else t.number for t in tiles)

        return numbers[1] == numbers[0] + 1 and numbers[2] == numbers[1] + 1

    def _validate_tile_counts(self, hand: Hand) -> None:
        """Validate that no tile appears more than 4 times."""
        # Red 5 (0) and regular 5 are different tiles
        counts = Counter((t.suit, t.number) for t in hand.all_tiles)

        for (suit, number), count in counts.items():
            if count > 4:
                tile_notation = f"{number}{suit}"
                self.errors.append(
                    f"Invalid tile count: {tile_notation} appears {count} times (max 4)"
                )


def parse_hand(notation: str) -> Hand:
    """Convenience function to parse a hand notation."""
    parser = MahjongParser()
    return parser.parse(notation)
