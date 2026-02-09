"""Tile database and asset mapping for Riichi Mahjong tiles."""

from __future__ import annotations

from typing import Final, NamedTuple


class TileInfo(NamedTuple):
    """Information about a tile type."""

    asset_name: str
    display_name: str


_SUIT_NAMES: Final[dict[str, str]] = {"m": "Man", "p": "Pin", "s": "Sou"}
_HONOR_NAMES: Final[dict[int, str]] = {
    1: "East", 2: "South", 3: "West", 4: "North",
    5: "White Dragon", 6: "Green Dragon", 7: "Red Dragon",
}


def _build_tile_database() -> dict[tuple[str, int], TileInfo]:
    db: dict[tuple[str, int], TileInfo] = {}
    for suit, name in _SUIT_NAMES.items():
        for n in range(1, 10):
            db[(suit, n)] = TileInfo(f"{n}{suit}", f"{n} {name}")
        db[(suit, 0)] = TileInfo(f"0{suit}", f"Red 5 {name}")
    for n, name in _HONOR_NAMES.items():
        db[("z", n)] = TileInfo(f"{n}z", name)
    return db

TILE_DATABASE: Final[dict[tuple[str, int], TileInfo]] = _build_tile_database()


def get_tile_info(suit: str, number: int) -> TileInfo | None:
    """Get tile information for a given suit and number."""
    return TILE_DATABASE.get((suit, number))
