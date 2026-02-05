"""Tile database and asset mapping for Riichi Mahjong tiles."""

from __future__ import annotations

from typing import Final, NamedTuple


class TileInfo(NamedTuple):
    """Information about a tile type."""

    asset_name: str
    display_name: str


TILE_DATABASE: Final[dict[tuple[str, int], TileInfo]] = {
    # Manzu
    ("m", 1): TileInfo("1m", "1 Man"),
    ("m", 2): TileInfo("2m", "2 Man"),
    ("m", 3): TileInfo("3m", "3 Man"),
    ("m", 4): TileInfo("4m", "4 Man"),
    ("m", 5): TileInfo("5m", "5 Man"),
    ("m", 6): TileInfo("6m", "6 Man"),
    ("m", 7): TileInfo("7m", "7 Man"),
    ("m", 8): TileInfo("8m", "8 Man"),
    ("m", 9): TileInfo("9m", "9 Man"),
    ("m", 0): TileInfo("0m", "Red 5 Man"),
    # Pinzu
    ("p", 1): TileInfo("1p", "1 Pin"),
    ("p", 2): TileInfo("2p", "2 Pin"),
    ("p", 3): TileInfo("3p", "3 Pin"),
    ("p", 4): TileInfo("4p", "4 Pin"),
    ("p", 5): TileInfo("5p", "5 Pin"),
    ("p", 6): TileInfo("6p", "6 Pin"),
    ("p", 7): TileInfo("7p", "7 Pin"),
    ("p", 8): TileInfo("8p", "8 Pin"),
    ("p", 9): TileInfo("9p", "9 Pin"),
    ("p", 0): TileInfo("0p", "Red 5 Pin"),
    # Souzu
    ("s", 1): TileInfo("1s", "1 Sou"),
    ("s", 2): TileInfo("2s", "2 Sou"),
    ("s", 3): TileInfo("3s", "3 Sou"),
    ("s", 4): TileInfo("4s", "4 Sou"),
    ("s", 5): TileInfo("5s", "5 Sou"),
    ("s", 6): TileInfo("6s", "6 Sou"),
    ("s", 7): TileInfo("7s", "7 Sou"),
    ("s", 8): TileInfo("8s", "8 Sou"),
    ("s", 9): TileInfo("9s", "9 Sou"),
    ("s", 0): TileInfo("0s", "Red 5 Sou"),
    # Winds
    ("z", 1): TileInfo("1z", "East"),
    ("z", 2): TileInfo("2z", "South"),
    ("z", 3): TileInfo("3z", "West"),
    ("z", 4): TileInfo("4z", "North"),
    # Dragons
    ("z", 5): TileInfo("5z", "White Dragon"),
    ("z", 6): TileInfo("6z", "Green Dragon"),
    ("z", 7): TileInfo("7z", "Red Dragon"),
}

SPECIAL_TILES: Final[dict[str, TileInfo]] = {
    "back": TileInfo("back", "Face Down"),
}


def get_tile_info(suit: str, number: int) -> TileInfo | None:
    """Get tile information for a given suit and number."""
    return TILE_DATABASE.get((suit, number))


def get_special_tile(name: str) -> TileInfo | None:
    """Get special tile information."""
    return SPECIAL_TILES.get(name.lower())


def is_valid_tile(suit: str, number: int) -> bool:
    """Check if a tile notation is valid."""
    if suit not in ("m", "p", "s", "z"):
        return False

    if suit == "z":
        return 1 <= number <= 7
    else:
        return 0 <= number <= 9
