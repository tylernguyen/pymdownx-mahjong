"""MPSZ notation parser for Riichi Mahjong hands."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from .tiles import TileInfo, get_tile_info, is_valid_tile


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


@dataclass
class Tile:
    """Represents a single mahjong tile."""

    suit: str  # m, p, s, z
    number: int  # 0-9 for suited, 1-7 for honors
    is_rotated: bool = False  # Is this tile rotated (called)?
    is_added: bool = False  # Is this the added tile in a shouminkan?

    @property
    def notation(self) -> str:
        """Return the MPSZ notation for this tile."""
        return f"{self.number}{self.suit}"

    @property
    def info(self) -> TileInfo | None:
        """Get the tile info from the database."""
        return get_tile_info(self.suit, self.number)

    @property
    def display_name(self) -> str:
        """Get the human-readable tile name."""
        info = self.info
        return info.display_name if info else f"Unknown ({self.notation})"

    def __str__(self) -> str:
        return self.notation


@dataclass
class Meld:
    """Represents a called tile group (meld)."""

    tiles: list[Tile]
    meld_type: MeldType
    source: MeldSource = MeldSource.SELF

    @property
    def is_open(self) -> bool:
        """Check if this meld is open (visible to other players)."""
        return self.meld_type != MeldType.KAN_CLOSED

    @property
    def tile_count(self) -> int:
        """Return the number of tiles in this meld."""
        return len(self.tiles)


@dataclass
class Hand:
    """Represents a complete mahjong hand."""

    closed_tiles: list[Tile] = field(default_factory=list)
    melds: list[Meld] = field(default_factory=list)
    dora_indicators: list[Tile] = field(default_factory=list)
    uradora_indicators: list[Tile] = field(default_factory=list)
    draw_tile: Tile | None = None  # The drawn tile (tsumo), displayed separately

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
    def meld_count(self) -> int:
        """Return the number of melds in the hand."""
        return len(self.melds)

    @property
    def total_tile_count(self) -> int:
        """Return total number of tiles in the hand (closed + melds + draw)."""
        count = len(self.closed_tiles) + sum(m.tile_count for m in self.melds)
        if self.draw_tile:
            count += 1
        return count


class ParseError(Exception):
    """Exception raised when parsing fails."""

    pass


class MahjongParser:
    """Parser for MPSZ mahjong notation.

    Supports notation like:
    - Basic: 123m456p789s1122z
    - Red dora: 1230m (0 = red 5)
    - Melds: (123m<) for chi, [1111m] for closed kan
    - Separators: | before melds, _ for gaps
    """

    # Pattern for a group of numbers followed by a suit
    TILE_GROUP_PATTERN = re.compile(r"([0-9]+)([mpsz])")

    # Pattern for melds: (tiles<) or [tiles] with optional source marker inside brackets
    # For added kan, use + to mark the added tile: (111+1m<)
    MELD_PATTERN = re.compile(r"(\[|\()([0-9]+)(\+)?([0-9])?([mpsz])([<^>])?(\]|\))")

    def __init__(self) -> None:
        self.errors: list[str] = []

    def parse(self, notation: str) -> Hand:
        """Parse a hand notation string into a Hand object.

        Args:
            notation: MPSZ notation string

        Returns:
            Parsed Hand object

        Raises:
            ParseError: If the notation is invalid
        """
        self.errors = []
        hand = Hand()

        # Normalize whitespace
        notation = notation.strip()

        # Extract melds first (they're unambiguous with brackets)
        hand.melds = self._parse_melds(notation)

        # Remove meld notation from string to get closed tiles
        closed_part = self.MELD_PATTERN.sub("", notation).strip()

        # Parse closed tiles
        hand.closed_tiles = self._parse_tiles(closed_part)

        if self.errors:
            raise ParseError("; ".join(self.errors))

        return hand

    def parse_tiles(self, notation: str) -> list[Tile]:
        """Parse a simple tile notation string.

        Args:
            notation: MPSZ notation like "123m456p"

        Returns:
            List of Tile objects
        """
        self.errors = []
        return self._parse_tiles(notation)

    def _parse_tiles(self, notation: str) -> list[Tile]:
        """Internal method to parse tile notation.

        Args:
            notation: Tile notation string

        Returns:
            List of tiles
        """
        tiles: list[Tile] = []

        # Remove separators and whitespace
        clean = notation.replace("_", "").replace(" ", "")

        # Find all tile groups
        for match in self.TILE_GROUP_PATTERN.finditer(clean):
            numbers = match.group(1)
            suit = match.group(2)

            for num_char in numbers:
                number = int(num_char)

                if not is_valid_tile(suit, number):
                    self.errors.append(f"Invalid tile: {number}{suit}")
                    continue

                tiles.append(Tile(suit=suit, number=number))

        return tiles

    def _parse_melds(self, notation: str) -> list[Meld]:
        """Parse meld notation.

        Args:
            notation: Meld notation like "(123m<) [1111z]"
            For added kan (shouminkan), use + before the added tile: "(111+1m<)"

        Returns:
            List of Meld objects
        """
        melds: list[Meld] = []

        for match in self.MELD_PATTERN.finditer(notation):
            open_bracket = match.group(1)
            base_numbers = match.group(2)  # Numbers before the +
            plus_marker = match.group(3)  # The + if present
            added_number = match.group(4)  # Number after + if present
            suit = match.group(5)
            source_char = match.group(6) or ""
            close_bracket = match.group(7)

            # Reject mismatched brackets
            if (open_bracket == "[" and close_bracket != "]") or (open_bracket == "(" and close_bracket != ")"):
                self.errors.append(f"Mismatched brackets in meld: {match.group(0)}")
                continue

            # Reject added kan notation without digit after '+'
            if plus_marker and not added_number:
                self.errors.append(f"Added kan notation requires digit after '+': {match.group(0)}")
                continue

            # Build the tile notation
            if plus_marker and added_number:
                # Added kan: combine base tiles and added tile
                tile_notation = base_numbers + added_number + suit
                is_added_kan = True
            else:
                tile_notation = base_numbers + suit
                is_added_kan = False

            # Parse the tiles in the meld
            tiles = self._parse_tiles(tile_notation)

            if not tiles:
                continue

            # Determine meld type
            is_closed = open_bracket == "[" and close_bracket == "]"
            tile_count = len(tiles)

            if is_added_kan and tile_count == 4:
                meld_type = MeldType.KAN_ADDED
            elif is_closed and tile_count == 4:
                meld_type = MeldType.KAN_CLOSED
            elif tile_count == 4:
                meld_type = MeldType.KAN_OPEN
            elif tile_count == 3:
                # Check if it's a sequence (chi) or triplet (pon)
                if self._is_sequence(tiles):
                    meld_type = MeldType.CHI
                else:
                    meld_type = MeldType.PON
            else:
                self.errors.append(f"Invalid meld size: {tile_count} tiles")
                continue

            # Determine source
            source = MeldSource.SELF
            if source_char == "<":
                source = MeldSource.LEFT
            elif source_char == "^":
                source = MeldSource.ACROSS
            elif source_char == ">":
                source = MeldSource.RIGHT

            # Mark the called tile(s) as rotated based on source direction
            # Position indicates which player the tile was called from:
            #   < (left/kamicha): rotated tile on the left (index 0)
            #   ^ (across/toimen): rotated tile in the middle (index 1)
            #   > (right/shimocha): rotated tile on the right (index 2 for 3-tile melds, index 3 for open kan)
            if source != MeldSource.SELF and tiles:
                # Determine rotated tile index based on source
                if source == MeldSource.LEFT:
                    rotated_idx = 0
                elif source == MeldSource.ACROSS:
                    rotated_idx = 1
                elif meld_type == MeldType.KAN_OPEN:
                    # Open kan has 4 tiles, rotated tile at index 3 for RIGHT
                    rotated_idx = 3
                else:
                    # Chi, pon, added kan: rotated tile at index 2 for RIGHT
                    rotated_idx = 2

                tiles[rotated_idx].is_rotated = True

                # Added kan: also mark the last tile as rotated and added
                if meld_type == MeldType.KAN_ADDED:
                    tiles[-1].is_rotated = True
                    tiles[-1].is_added = True

            melds.append(Meld(tiles=tiles, meld_type=meld_type, source=source))

        return melds

    def _is_sequence(self, tiles: list[Tile]) -> bool:
        """Check if tiles form a sequence (chi).

        Args:
            tiles: List of 3 tiles

        Returns:
            True if tiles form a consecutive sequence
        """
        if len(tiles) != 3:
            return False

        # All tiles must be same suit and not honors
        suits = {t.suit for t in tiles}
        if len(suits) != 1 or "z" in suits:
            return False

        # Check for consecutive numbers (red dora 0 is treated as 5)
        numbers = sorted(5 if t.number == 0 else t.number for t in tiles)

        return numbers[1] == numbers[0] + 1 and numbers[2] == numbers[1] + 1


def parse_hand(notation: str) -> Hand:
    """Convenience function to parse a hand notation.

    Args:
        notation: MPSZ notation string

    Returns:
        Parsed Hand object
    """
    parser = MahjongParser()
    return parser.parse(notation)


def parse_tiles(notation: str) -> list[Tile]:
    """Convenience function to parse tile notation.

    Args:
        notation: MPSZ notation string

    Returns:
        List of Tile objects
    """
    parser = MahjongParser()
    return parser.parse_tiles(notation)
