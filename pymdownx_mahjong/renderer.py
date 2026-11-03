"""Renderer for Mahjong hands."""

from __future__ import annotations

import html
from typing import Final

from .parser import MAX_DORA_INDICATORS, OPPONENT_SEATS, SEAT_WINDS, Hand, Meld, MeldSource, MeldType, Tile
from .sprite import MARKER_THEME, TileSprite

THEMES: Final[tuple[str, ...]] = ("auto", "light", "dark")
CLOSED_KAN_STYLES: Final[tuple[str, ...]] = ("outer", "inner")

# The first two discard rows hold 6 tiles each; the third holds the rest.
_DISCARD_ROW_SIZE: Final = 6

# Point sticks (tenbou) shown above the hand: Hand attribute, asset name, label.
_STICKS: Final[tuple[tuple[str, str, str], ...]] = (
    ("riichi", "1000", "Riichi sticks"),
    ("honba", "100", "Honba"),
)
_SEAT_WIND_KANJI: Final[dict[str, str]] = {"east": "東", "south": "南", "west": "西", "north": "北"}
_ROUND_NUMBER_KANJI: Final[dict[int, str]] = {1: "一", 2: "二", 3: "三", 4: "四"}

# Accessible names for the players on a table: the bottom player, then the others in turn order.
_PLAYER_NAMES: Final[dict[str, str]] = {
    "self": "Bottom player",
    "shimo": "Shimocha (right)",
    "toimen": "Toimen (across)",
    "kami": "Kamicha (left)",
}

# Intrinsic size of the stick artwork (65.45 x 7.3 mm); CSS sets the rendered size.
_STICK_WIDTH: Final = 72
_STICK_HEIGHT: Final = 8

# Round markers kept by the original dealer: round wind -> asset (assets/<name>.png), and the
# artwork's intrinsic size; CSS sets the rendered size. West and north rounds have none.
_ROUND_MARKERS: Final[dict[str, str]] = {"east": "East", "south": "South"}
_MARKER_WIDTH: Final = 45  # the artwork is 567 x 374; this keeps it tile-sized without the CSS
_MARKER_HEIGHT: Final = 30

_MELD_NAMES: Final[dict[MeldType, str]] = {
    MeldType.CHI: "Chi",
    MeldType.PON: "Pon",
    MeldType.KAN_OPEN: "Open kan",
    MeldType.KAN_CLOSED: "Closed kan",
    MeldType.KAN_ADDED: "Added kan",
}
_SOURCE_NAMES: Final[dict[MeldSource, str]] = {
    MeldSource.LEFT: "from left",
    MeldSource.ACROSS: "from across",
    MeldSource.RIGHT: "from right",
}


class MahjongRenderer:
    """Renders mahjong hands as HTML with SVG tiles.

    Tile artwork is referenced from a TileSprite. Pass a page-wide sprite to share
    symbols across calls; without one, each call embeds the symbols it uses.

    Configuration options:
        theme: 'light', 'dark', or 'auto'
        closed_kan_style: 'outer' (default) or 'inner'
    """

    _BACK_TILE_HTML = (
        '<span class="mahjong-tile mahjong-tile-back" role="img" '
        'aria-label="Face-down tile" title="Face-down tile"></span>'
    )
    # The other players' hidden hand tiles, drawn standing up (see the CSS for .mahjong-tile-standing).
    _STANDING_BACK_TILE_HTML = (
        '<span class="mahjong-tile mahjong-tile-back mahjong-tile-standing" role="img" '
        'aria-label="Face-down tile" title="Face-down tile"></span>'
    )
    # Decorative filler in the dead wall next to the dora indicators.
    _WALL_BACK_TILE_HTML = '<span class="mahjong-tile mahjong-tile-back" aria-hidden="true"></span>'

    def __init__(
        self,
        theme: str = "light",
        closed_kan_style: str = "outer",
        css_class: str = "mahjong-hand",
    ) -> None:
        if theme not in THEMES:
            raise ValueError(f"Invalid theme {theme!r} (expected one of: {', '.join(THEMES)})")
        if closed_kan_style not in CLOSED_KAN_STYLES:
            raise ValueError(
                f"Invalid closed_kan_style {closed_kan_style!r} (expected one of: {', '.join(CLOSED_KAN_STYLES)})"
            )
        self.theme = theme
        self.css_class = css_class
        self.closed_kan_style = closed_kan_style

    def render(
        self,
        hand: Hand,
        title: str | None = None,
        notation: str | None = None,
        sprite: TileSprite | None = None,
    ) -> str:
        """Render a hand as HTML."""
        page_sprite = sprite
        sprite = sprite or TileSprite()
        parts: list[str] = []

        data_attr = f' data-notation="{html.escape(notation, quote=True)}"' if notation else ""
        theme_class = f" mahjong-theme-{self.theme}" if self.theme in ("light", "dark") else ""
        # A figcaption names the figure; otherwise give it a generic accessible name.
        label_attr = "" if title else ' aria-label="Mahjong hand"'
        parts.append(f'<figure class="{self.css_class}{theme_class}"{data_attr}{label_attr}>')

        # With other players, the same pieces sit on a square table: the dora row in the
        # center, and each player's discards, status and hand along their own edge.
        on_table = bool(hand.opponents)
        players = [("self", hand), *((seat, hand.opponents[seat]) for seat in OPPONENT_SEATS if seat in hand.opponents)]
        # The riichi and honba sticks sit with the dealer (east), or the bottom player when
        # no one is east; the round marker with the original dealer, found from the round.
        dealer = next((seat for seat, player in players if player.seat_wind == "east"), "self")
        marker_wind = self._original_dealer_wind(hand)

        if on_table:
            parts.append('<div class="mahjong-table">')
        parts.extend(self._render_dora_row(hand, sprite))
        for seat, player in players:
            if on_table and seat == "self" and not self._has_content(player, hand, dealer, marker_wind):
                # A table given only the other players: no empty area for the bottom player.
                continue
            body = self._render_player(
                player,
                sprite,
                sticks=hand if seat == dealer else None,
                marker=hand.round_wind if marker_wind and player.seat_wind == marker_wind else None,
                standing=seat != "self",
            )
            if on_table:
                name = _PLAYER_NAMES[seat]
                body = [
                    f'<div class="mahjong-player mahjong-player-{seat}" role="group" aria-label="{name}">',
                    *body,
                    "</div>",
                ]
            parts.extend(body)
        if on_table:
            parts.append("</div>")

        if title:
            parts.append(f'<figcaption class="mahjong-caption">{html.escape(title, quote=True)}</figcaption>')

        parts.append("</figure>")

        return self._join(parts, sprite, page_sprite)

    def _render_dora_row(self, hand: Hand, sprite: TileSprite) -> list[str]:
        """Render the dora indicators, with the round and tiles remaining beside them."""
        has_round_info = hand.round_wind is not None or hand.remaining is not None
        if not (hand.dora_indicators or has_round_info):
            return []
        parts = ['<div class="mahjong-dora-row">']
        if hand.dora_indicators:
            parts.extend(self._render_dora_section(hand.dora_indicators, sprite))
        if has_round_info:
            parts.extend(self._render_round_info(hand))
        parts.append("</div>")
        return parts

    @staticmethod
    def _has_content(player: Hand, hand: Hand, dealer: str, marker_wind: str | None) -> bool:
        """Whether the bottom player has anything to show: tiles, discards, a seat or score,
        the sticks (as dealer) or the round marker."""
        return bool(
            player.closed_tiles
            or player.melds
            or player.draw_tile
            or player.discards
            or player.seat_wind
            or player.score is not None
            or (dealer == "self" and (hand.riichi or hand.honba))
            or (marker_wind and player.seat_wind == marker_wind)
        )

    @staticmethod
    def _original_dealer_wind(hand: Hand) -> str | None:
        """The original dealer's seat wind this hand, for a round with a marker: the deal
        passes one seat each hand, so in hand N they sit N - 1 winds before east, e.g. north
        in East 2."""
        if hand.round_wind not in _ROUND_MARKERS or hand.round_number is None:
            return None
        return SEAT_WINDS[(1 - hand.round_number) % len(SEAT_WINDS)]

    def _render_player(
        self, hand: Hand, sprite: TileSprite, sticks: Hand | None, marker: str | None, standing: bool
    ) -> list[str]:
        """Render one player: discards, then the status row (with the riichi and honba sticks
        from ``sticks`` and the round ``marker``, if given), then the hand, whose face-down
        tiles stand up for the other players."""
        parts: list[str] = []
        if hand.discards:
            parts.extend(self._render_discards(hand.discards, sprite))

        sticks = sticks if sticks is not None and (sticks.riichi or sticks.honba) else None
        if hand.seat_wind or hand.score is not None or sticks or marker:
            parts.append('<div class="mahjong-status">')
            if hand.seat_wind or hand.score is not None:
                parts.extend(self._render_seat(hand))
            if sticks:
                parts.extend(self._render_sticks(sticks, sprite))
            if marker:
                parts.append(self._render_round_marker(marker, sprite))
            parts.append("</div>")

        if hand.closed_tiles or hand.melds or hand.draw_tile:
            parts.extend(self._render_hand_row(hand, sprite, standing=standing))
        return parts

    @staticmethod
    def _render_round_marker(round_wind: str, sprite: TileSprite) -> str:
        """Render the round marker (East or South) at the right of the status row."""
        name = round_wind.capitalize()
        label = f"Round marker: {name}"
        artwork = sprite.use(_ROUND_MARKERS[round_wind], MARKER_THEME, _MARKER_WIDTH, _MARKER_HEIGHT)
        return f'<span class="mahjong-round-marker" role="img" aria-label="{label}" title="{label}">{artwork}</span>'

    @staticmethod
    def _render_round_info(hand: Hand) -> list[str]:
        """Render the round (e.g. 南二局) and the tiles remaining in the wall (e.g. 残 35)."""
        parts = ['<span class="mahjong-round-info">']
        if hand.round_wind is not None and hand.round_number is not None:
            name = f"{hand.round_wind.capitalize()} {hand.round_number}"
            kanji = f"{_SEAT_WIND_KANJI[hand.round_wind]}{_ROUND_NUMBER_KANJI[hand.round_number]}局"
            parts.append(
                f'<span class="mahjong-round" lang="ja" role="img" aria-label="Round: {name}" title="{name}">'
                f"{kanji}</span>"
            )
        if hand.remaining is not None:
            label = f"{hand.remaining} tiles remaining"
            parts.append(
                f'<span class="mahjong-remaining" lang="ja" role="img" aria-label="{label}" title="{label}">'
                f"残 {hand.remaining}</span>"
            )
        parts.append("</span>")
        return parts

    def _render_hand_row(self, hand: Hand, sprite: TileSprite, standing: bool = False) -> list[str]:
        """Render the closed tiles, draw tile and melds; ``standing`` draws face-down closed
        and draw tiles standing up (melds' face-down tiles stay lying down)."""
        parts = ['<div class="mahjong-hand-row">']

        parts.append('<div class="mahjong-hand-left">')
        parts.append('<div class="mahjong-tiles">')
        parts.extend(self._render_tile(tile, sprite, standing=standing) for tile in hand.closed_tiles)
        parts.append("</div>")
        parts.append("</div>")

        if hand.draw_tile:
            # Name the group so the draw tile is distinguishable from the closed tiles.
            parts.append('<div class="mahjong-hand-draw" role="group" aria-label="Draw">')
            parts.append('<div class="mahjong-tiles">')
            parts.append(self._render_tile(hand.draw_tile, sprite, standing=standing))
            parts.append("</div>")
            parts.append("</div>")

        if hand.melds:
            parts.append('<div class="mahjong-hand-melds">')
            parts.append('<div class="mahjong-tiles">')
            parts.extend(self._render_meld(meld, sprite) for meld in hand.melds)
            parts.append("</div>")
            parts.append("</div>")

        parts.append("</div>")
        return parts

    def _render_discards(self, tiles: list[Tile], sprite: TileSprite) -> list[str]:
        """Render a discard pile: two rows of up to 6 tiles, then a row with the rest."""
        rows = [
            tiles[:_DISCARD_ROW_SIZE],
            tiles[_DISCARD_ROW_SIZE : 2 * _DISCARD_ROW_SIZE],
            tiles[2 * _DISCARD_ROW_SIZE :],
        ]
        parts = ['<div class="mahjong-discards" role="group" aria-label="Discards">']
        for row in rows:
            if row:
                parts.append('<div class="mahjong-discard-row">')
                parts.extend(self._render_tile(tile, sprite, discard=True) for tile in row)
                parts.append("</div>")
        parts.append("</div>")
        return parts

    def render_tiles(self, tiles: list[Tile], sprite: TileSprite | None = None) -> str:
        """Render a simple list of tiles as HTML."""
        page_sprite = sprite
        sprite = sprite or TileSprite()
        parts = [f'<span class="{self.css_class}">']
        parts.extend(self._render_tile(tile, sprite) for tile in tiles)
        parts.append("</span>")
        return self._join(parts, sprite, page_sprite)

    @staticmethod
    def _join(parts: list[str], sprite: TileSprite, page_sprite: TileSprite | None) -> str:
        """Join output parts, embedding the symbols inside the root element unless a
        page-wide sprite emits them."""
        if page_sprite is None:
            parts.insert(1, sprite.render())
        return "".join(parts)

    def _render_dora_section(self, tiles: list[Tile], sprite: TileSprite) -> list[str]:
        """Render the dora indicators as a stretch of the dead wall: two-high stacks, with
        face-down tiles filling the 5 slots to the left of the indicators."""
        label = "Dora indicator" if len(tiles) == 1 else "Dora indicators"
        parts = [
            f'<div class="mahjong-dora" role="group" aria-label="{label}">',
            '<span class="mahjong-dora-tiles mahjong-dora-wall">',
        ]
        parts.extend([self._WALL_BACK_TILE_HTML] * (MAX_DORA_INDICATORS - len(tiles)))
        parts.extend(self._render_tile(tile, sprite) for tile in tiles)
        parts.extend(["</span>", "</div>"])
        return parts

    @staticmethod
    def _render_seat(hand: Hand) -> list[str]:
        """Render the seat wind kanji and score at the left of the status row."""
        parts = ['<div class="mahjong-seat">']
        if hand.seat_wind:
            name = hand.seat_wind.capitalize()
            parts.append(
                f'<span class="mahjong-seat-wind" lang="ja" role="img" '
                f'aria-label="Seat wind: {name}" title="{name}">{_SEAT_WIND_KANJI[hand.seat_wind]}</span>'
            )
        if hand.score is not None:
            parts.append(
                f'<span class="mahjong-score" role="img" aria-label="Score: {hand.score}">'
                f"{MahjongRenderer._score_digits(hand.score)}</span>"
            )
        parts.append("</div>")
        return parts

    @staticmethod
    def _score_digits(score: int) -> str:
        """Format a score with comma separators and split off its last three digits (with
        their comma), so the thousands can stand out, e.g. 25000 -> 25 and ,000; below 1000
        there's no thousands part."""
        sign = "-" if score < 0 else ""
        digits = f"{abs(score):,}"
        if abs(score) < 1000:
            # No thousands part: the sign stays with the digits, e.g. -500.
            thousands, hundreds = "", sign + digits
        else:
            thousands, hundreds = sign + digits[:-4], digits[-4:]
        parts = []
        if thousands:
            parts.append(f'<span class="mahjong-score-thousands">{thousands}</span>')
        parts.append(f'<span class="mahjong-score-hundreds">{hundreds}</span>')
        return "".join(parts)

    @staticmethod
    def _render_sticks(hand: Hand, sprite: TileSprite) -> list[str]:
        """Render riichi and honba sticks, each followed by its count, at the right of the status row."""
        parts = ['<div class="mahjong-sticks">']
        for attr, asset_name, name in _STICKS:
            count = getattr(hand, attr)
            if count:
                label = f"{name}: {count}"
                parts.append(
                    f'<span class="mahjong-stick mahjong-stick-{attr}" role="img" '
                    f'aria-label="{label}" title="{label}">'
                    f"{sprite.use(asset_name, 'tenbou', _STICK_WIDTH, _STICK_HEIGHT)}"
                    f'<span class="mahjong-stick-count">&times;{count}</span></span>'
                )
        parts.append("</div>")
        return parts

    def _render_tile(self, tile: Tile, sprite: TileSprite, discard: bool = False, standing: bool = False) -> str:
        """Render a single tile as HTML with an SVG referencing the sprite."""
        if tile.is_back:
            return self._STANDING_BACK_TILE_HTML if standing else self._BACK_TILE_HTML

        info = tile.info
        if not info:
            return (
                f'<span class="mahjong-tile mahjong-tile-unknown" data-tile="{tile.notation}" '
                f'role="img" aria-label="Unknown tile">?</span>'
            )

        classes = ["mahjong-tile"]
        if tile.is_rotated:
            classes.append("mahjong-tile-rotated")
        if tile.is_added:
            classes.append("mahjong-tile-added")
        if tile.is_tsumogiri:
            classes.append("mahjong-tile-tsumogiri")
        if tile.is_called:
            classes.append("mahjong-tile-called")
        if self.theme in ("light", "dark"):
            classes.append(f"mahjong-theme-{self.theme}")

        class_str = " ".join(classes)
        label = html.escape(info.display_name + (self._discard_note(tile) if discard else ""), quote=True)
        if self.theme == "auto":
            svg_content = (
                f'<span class="mahjong-tile-light">{sprite.use(info.asset_name, "light")}</span>'
                f'<span class="mahjong-tile-dark">{sprite.use(info.asset_name, "dark")}</span>'
            )
        else:
            svg_content = sprite.use(info.asset_name, self.theme)
        return (
            f'<span class="{class_str}" data-tile="{tile.notation}" role="img" '
            f'aria-label="{label}" title="{label}">{svg_content}</span>'
        )

    @staticmethod
    def _discard_note(tile: Tile) -> str:
        """Describe a tile's discard markers for its accessible name, e.g. ' (riichi, called)'."""
        notes = []
        if tile.is_rotated:
            notes.append("riichi")
        if tile.is_tsumogiri:
            notes.append("tsumogiri")
        if tile.is_called:
            notes.append("called")
        return f" ({', '.join(notes)})" if notes else ""

    def _render_meld(self, meld: Meld, sprite: TileSprite) -> str:
        """Render a meld (called tile group)."""
        state = "open" if meld.is_open else "closed"
        class_str = f"mahjong-meld mahjong-meld-{state}"
        label = " ".join(filter(None, [_MELD_NAMES[meld.meld_type], _SOURCE_NAMES.get(meld.source)]))
        parts = [f'<span class="{class_str}" role="group" aria-label="{label}">']

        if meld.meld_type == MeldType.KAN_ADDED:
            parts.extend(self._render_added_kan(meld, sprite))
        else:
            parts.extend(self._render_standard_meld(meld, sprite))

        parts.append("</span>")
        return "".join(parts)

    def _render_added_kan(self, meld: Meld, sprite: TileSprite) -> list[str]:
        """Render an added kan (shouminkan) — stacked pair position depends on source."""
        t = [self._render_tile(tile, sprite) for tile in meld.tiles]
        stack_open = '<span class="mahjong-tile-stack">'
        if meld.tiles[0].is_rotated:
            return [stack_open, t[0], t[3], "</span>", t[1], t[2]]
        if meld.tiles[2].is_rotated:
            return [t[0], t[1], stack_open, t[2], t[3], "</span>"]
        return [t[0], stack_open, t[1], t[3], "</span>", t[2]]

    def _render_standard_meld(self, meld: Meld, sprite: TileSprite) -> list[str]:
        """Render a standard meld (non-added kan)."""
        parts: list[str] = []
        for i, tile in enumerate(meld.tiles):
            if meld.meld_type == MeldType.KAN_CLOSED:
                # inner: front, back, back, front; outer: back, front, front, back
                is_back = i in (1, 2) if self.closed_kan_style == "inner" else i in (0, 3)
                if is_back:
                    parts.append(self._BACK_TILE_HTML)
                else:
                    parts.append(self._render_tile(tile, sprite))
            else:
                parts.append(self._render_tile(tile, sprite))

        return parts
