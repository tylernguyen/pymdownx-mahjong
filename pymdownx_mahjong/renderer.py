"""Renderer for Mahjong hands."""

from __future__ import annotations

import html
import itertools
import re
from typing import TYPE_CHECKING, Final

from .parser import MAX_DORA_INDICATORS, OPPONENT_SEATS, SEAT_WINDS, Hand, Meld, MeldSource, MeldType, Tile
from .sprite import MARKER_THEME, TileSprite

if TYPE_CHECKING:
    from collections.abc import Sequence

THEMES: Final[tuple[str, ...]] = ("auto", "light", "dark")
CLOSED_KAN_STYLES: Final[tuple[str, ...]] = ("outer", "inner")

# A CSS color for tile_back_color and table_color: hex (#e7b246), a named color (teal), or a color function
# (rgb(...), oklch(...), color-mix(...)). It lands in a style attribute and feeds background
# rules, so nothing else (e.g. url(...)) is accepted.
_CSS_COLOR: Final[re.Pattern[str]] = re.compile(
    r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})"
    r"|[a-zA-Z]+"
    r"|(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color|color-mix)\([#0-9a-zA-Z.,%/+\s()-]*\)",
    re.IGNORECASE,  # CSS function names are case-insensitive, like its color names
)
# Functions allowed inside a color value, so nothing like url(...) can be nested in one.
_COLOR_FUNCTIONS: Final = frozenset(
    ("rgb", "rgba", "hsl", "hsla", "hwb", "lab", "lch", "oklab", "oklch", "color", "color-mix")
)
_CSS_FUNCTION: Final[re.Pattern[str]] = re.compile(r"([a-zA-Z-]+)\s*\(")
# CSS named colors (plus transparent and currentcolor), so a misspelt name is caught.
_CSS_NAMED_COLORS: Final = frozenset(
    """aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue
    blueviolet brown burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk
    crimson cyan darkblue darkcyan darkgoldenrod darkgray darkgreen darkgrey darkkhaki
    darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen
    darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink deepskyblue
    dimgray dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite
    gold goldenrod gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki
    lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan
    lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen
    lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime limegreen linen
    magenta maroon mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen
    mediumslateblue mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream
    mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid
    palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum
    powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown
    seagreen seashell sienna silver skyblue slateblue slategray slategrey snow springgreen
    steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow
    yellowgreen transparent currentcolor""".split()  # noqa: SIM905 - a word list reads far better than 150 strings
)

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

# Intrinsic size of the stick artwork (65.45 x 7.3 mm, plus a 0.5 mm margin all round so its
# outline is never clipped); CSS sets the rendered size.
_STICK_WIDTH: Final = 72
_STICK_HEIGHT: Final = 9

# Round markers kept by the original dealer: round wind -> asset (assets/<name>.svg), and the
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


def _is_css_color(value: str) -> bool:
    """Whether ``value`` is a CSS color: a hex color, a named color, or a color function
    (possibly with colors nested in it) that ends the value."""
    if not _CSS_COLOR.fullmatch(value):
        return False
    if "(" not in value:
        return value.startswith("#") or value.lower() in _CSS_NAMED_COLORS
    functions = [name.lower() for name in _CSS_FUNCTION.findall(value)]
    # Every parenthesis opens a known function, with something inside it.
    if value.count("(") != len(functions) or re.search(r"\(\s*\)", value):
        return False
    return _COLOR_FUNCTIONS.issuperset(functions) and _closes_at_end(value)


def _closes_at_end(value: str) -> bool:
    """Whether a color function's first parenthesis closes at the very end of the value, so
    nothing (e.g. a url(...)) can follow it."""
    depth = 0
    for i, char in enumerate(value):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0 or (depth == 0 and i != len(value) - 1):
                return False
    return depth == 0


class MahjongRenderer:
    """Renders mahjong hands as HTML with SVG tiles.

    Tile artwork is referenced from a TileSprite. Pass a page-wide sprite to share
    symbols across calls; without one, each call embeds the symbols it uses.

    Configuration options:
        theme: 'light', 'dark', or 'auto'
        closed_kan_style: 'outer' (default) or 'inner'
        tile_back_color: a CSS color for face-down tiles (default: the stylesheet's)
        table_color: a CSS color for the table's background (default: transparent)
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
        tile_back_color: str | None = None,
        table_color: str | None = None,
    ) -> None:
        if theme not in THEMES:
            raise ValueError(f"Invalid theme {theme!r} (expected one of: {', '.join(THEMES)})")
        if closed_kan_style not in CLOSED_KAN_STYLES:
            raise ValueError(
                f"Invalid closed_kan_style {closed_kan_style!r} (expected one of: {', '.join(CLOSED_KAN_STYLES)})"
            )
        tile_back_color = self._css_color("tile_back_color", tile_back_color)
        table_color = self._css_color("table_color", table_color)
        self.theme = theme
        self.css_class = css_class
        self.closed_kan_style = closed_kan_style
        # On each root element, for what's inherited rather than set per tile (e.g. face-down tiles).
        self._theme_class = f" mahjong-theme-{theme}" if theme in ("light", "dark") else ""
        # Set on each rendered block, overriding the stylesheet's defaults.
        style_vars = [
            f"--mahjong-tile-back: {tile_back_color}" if tile_back_color else "",
            f"--mahjong-table-bg: {table_color}" if table_color else "",
        ]
        style = "; ".join(filter(None, style_vars))
        self._style_attr = f' style="{html.escape(style)}"' if style else ""
        # A table with a background keeps its tiles a little in from its edge.
        self._table_class = "mahjong-table mahjong-table-filled" if table_color else "mahjong-table"

    @staticmethod
    def _css_color(option: str, value: str | None) -> str:
        """Validate an optional CSS color option, returning it stripped ('' when unset).

        Raises:
            ValueError: If the value isn't a CSS color
        """
        value = (value or "").strip()
        if value and not _is_css_color(value):
            raise ValueError(
                f"Invalid {option} {value!r} (expected a CSS color, e.g. '#e7b246', 'teal' or 'rgb(231 178 70)')"
            )
        return value

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
        # A figcaption names the figure; otherwise give it a generic accessible name.
        label_attr = "" if title else ' aria-label="Mahjong hand"'
        parts.append(f'<figure class="{self.css_class}{self._theme_class}"{self._style_attr}{data_attr}{label_attr}>')

        # With other players, the same pieces sit on a square table: the dora row in the
        # center, and each player's discards, status and hand along their own edge.
        on_table = bool(hand.opponents)
        players = [("self", hand), *((seat, hand.opponents[seat]) for seat in OPPONENT_SEATS if seat in hand.opponents)]
        # The riichi and honba sticks sit with the dealer (east), or the bottom player when
        # no one is east; the round marker with the original dealer, found from the round.
        dealer = next((seat for seat, player in players if player.seat_wind == "east"), "self")
        marker_wind = self._original_dealer_wind(hand)

        if on_table:
            parts.append(f'<div class="{self._table_class}">')
        parts.extend(self._render_dora_row(hand, sprite))
        for seat, player in players:
            body = self._render_player(
                player,
                sprite,
                sticks=hand if seat == dealer else None,
                marker=hand.round_wind if marker_wind and player.seat_wind == marker_wind else None,
                standing=seat != "self",
                starting_score=hand.starting_score,
            )
            if not body:
                # A table given only the other players: no empty area for the bottom player.
                continue
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
    def _original_dealer_wind(hand: Hand) -> str | None:
        """The original dealer's seat wind this hand, for a round with a marker: the deal
        passes one seat each hand, so in hand N they sit N - 1 winds before east, e.g. north
        in East 2."""
        if hand.round_wind not in _ROUND_MARKERS or hand.round_number is None:
            return None
        return SEAT_WINDS[(1 - hand.round_number) % len(SEAT_WINDS)]

    def _render_player(
        self,
        hand: Hand,
        sprite: TileSprite,
        sticks: Hand | None,
        marker: str | None,
        standing: bool,
        starting_score: int,
    ) -> list[str]:
        """Render one player: discards, then the status row (with the riichi and honba sticks
        from ``sticks`` and the round ``marker``, if given), then the hand, whose face-down
        tiles stand up for the other players. The score shows its delta from ``starting_score``
        on hover."""
        sticks = sticks if sticks is not None and (sticks.riichi or sticks.honba) else None
        has_tiles = hand.closed_tiles or hand.melds or hand.draw_tile
        # An inferred wind doesn't earn a player an area of their own.
        if hand.seat_wind_inferred and not (has_tiles or hand.discards or hand.score is not None or sticks or marker):
            return []

        parts: list[str] = []
        if hand.discards:
            parts.extend(self._render_discards(hand.discards, sprite))

        if hand.seat_wind or hand.score is not None or sticks or marker:
            parts.append('<div class="mahjong-status">')
            if hand.seat_wind or hand.score is not None:
                parts.extend(self._render_seat(hand, starting_score))
            if sticks:
                parts.extend(self._render_sticks(sticks, sprite))
            if marker:
                parts.append(self._render_round_marker(marker, sprite))
            parts.append("</div>")

        if has_tiles:
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
                f'<span class="mahjong-round" role="img" aria-label="Round: {name}" title="Round: {name}">'
                f'<span lang="ja">{kanji}</span></span>'
            )
        if hand.remaining is not None:
            label = f"{hand.remaining} tiles remaining"
            parts.append(
                f'<span class="mahjong-remaining" role="img" aria-label="{label}" title="{label}">'
                f'<span lang="ja">残 {hand.remaining}</span></span>'
            )
        parts.append("</span>")
        return parts

    def _render_hand_row(self, hand: Hand, sprite: TileSprite, standing: bool = False) -> list[str]:
        """Render the closed tiles, draw tile and melds; ``standing`` draws face-down closed
        and draw tiles standing up (melds' face-down tiles stay lying down)."""
        parts = ['<div class="mahjong-hand-row">']

        # Name the group so the closed tiles are distinguishable from the draw and melds.
        group_attrs = ' role="group" aria-label="Hand"' if hand.closed_tiles else ""
        parts.append(f'<div class="mahjong-hand-left"{group_attrs}>')
        parts.append('<div class="mahjong-tiles">')
        parts.extend(self._render_closed_tiles(hand.closed_tiles, sprite, standing))
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

    def _render_closed_tiles(self, tiles: list[Tile], sprite: TileSprite, standing: bool) -> list[str]:
        """Render closed tiles, with each run of face-down tiles announced once."""
        parts: list[str] = []
        for is_back, run in itertools.groupby(tiles, key=lambda tile: tile.is_back):
            if is_back:
                parts.extend(self._render_back_run(sum(1 for _ in run), standing))
            else:
                parts.extend(self._render_tile(tile, sprite, standing=standing) for tile in run)
        return parts

    def _render_back_run(self, count: int, standing: bool) -> list[str]:
        """Render a run of face-down tiles: the first carries the count for screen readers, so
        a hidden hand is one stop rather than 13, and the rest are hidden from them. No wrapper,
        as the CSS relies on tiles being direct children of their row."""
        if count == 1:
            return [self._STANDING_BACK_TILE_HTML if standing else self._BACK_TILE_HTML]
        classes = "mahjong-tile mahjong-tile-back" + (" mahjong-tile-standing" if standing else "")
        label = f"{count} face-down tiles"
        first = f'<span class="{classes}" role="img" aria-label="{label}" title="{label}"></span>'
        rest = f'<span class="{classes}" aria-hidden="true" title="{label}"></span>'
        return [first, *[rest] * (count - 1)]

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
                parts.extend(self._render_tile(tile, sprite, note=self._discard_note(tile)) for tile in row)
                parts.append("</div>")
        parts.append("</div>")
        return parts

    def render_tiles(self, tiles: list[Tile], sprite: TileSprite | None = None, melds: Sequence[Meld] = ()) -> str:
        """Render a simple list of tiles, followed by any melds, as HTML."""
        page_sprite = sprite
        sprite = sprite or TileSprite()
        parts = [f'<span class="{self.css_class}{self._theme_class}"{self._style_attr}>']
        parts.extend(self._render_closed_tiles(tiles, sprite, standing=False))
        parts.extend(self._render_meld(meld, sprite) for meld in melds)
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
    def _render_seat(hand: Hand, starting_score: int) -> list[str]:
        """Render the seat wind kanji and score at the left of the status row."""
        parts = ['<div class="mahjong-seat">']
        if hand.seat_wind:
            label = f"Seat Wind: {hand.seat_wind.capitalize()}"
            parts.append(
                f'<span class="mahjong-seat-wind" role="img" aria-label="{label}" title="{label}">'
                f'<span lang="ja">{_SEAT_WIND_KANJI[hand.seat_wind]}</span></span>'
            )
        if hand.score is not None:
            parts.append(MahjongRenderer._render_score(hand.score, starting_score, hand.borrowed))
        parts.append("</div>")
        return parts

    @staticmethod
    def _render_score(score: int, starting_score: int, borrowed: int) -> str:
        """Render a score and its delta from ``starting_score``, which the CSS swaps in on hover.
        Points ``borrowed`` from the bank are owed back, so they don't count toward the delta and
        are shown beside it."""
        delta = score - borrowed - starting_score
        sign_class = ""
        if delta:
            sign_class = f" mahjong-score-delta-{'positive' if delta > 0 else 'negative'}"
        loan = f" with {borrowed} borrowed" if borrowed else ""
        loan_html = ""
        if borrowed:
            loan_html = f'<span class="mahjong-score-loan" title="Borrowed {borrowed:,}">({borrowed:,})</span>'
        label = f"Score: {score}{loan}, {f'{delta:+}' if delta else '±0'} from {starting_score}"
        return (
            f'<span class="mahjong-score" role="img" aria-label="{label}">'
            f'<span class="mahjong-score-value">{MahjongRenderer._score_digits(score)}</span>'
            f'<span class="mahjong-score-delta{sign_class}">'
            f"{MahjongRenderer._score_digits(delta, signed=True)}{loan_html}</span>"
            "</span>"
        )

    @staticmethod
    def _score_digits(score: int, signed: bool = False) -> str:
        """Format a score with comma separators and split off its last three digits (with
        their comma), so the thousands can stand out, e.g. 25000 -> 25 and ,000; below 1000
        there's no thousands part. ``signed`` marks a delta: +1,200 or ±0 as well as -1,200."""
        if score < 0:
            sign = "-"
        elif signed:
            sign = "+" if score else "±"
        else:
            sign = ""
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

    def _render_tile(self, tile: Tile, sprite: TileSprite, note: str = "", standing: bool = False) -> str:
        """Render a single tile as HTML with an SVG referencing the sprite; ``note`` is
        appended to its accessible name."""
        if tile.is_back:
            if not note:
                return self._STANDING_BACK_TILE_HTML if standing else self._BACK_TILE_HTML
            # A face-down discard keeps its markers.
            class_str = " ".join(["mahjong-tile", "mahjong-tile-back", *self._marker_classes(tile)])
            label = f"Face-down tile{note}"
            return f'<span class="{class_str}" role="img" aria-label="{label}" title="{label}"></span>'

        info = tile.info
        if not info:
            return (
                f'<span class="mahjong-tile mahjong-tile-unknown" data-tile="{tile.notation}" '
                f'role="img" aria-label="Unknown tile">?</span>'
            )

        classes = ["mahjong-tile", *self._marker_classes(tile)]
        if self.theme in ("light", "dark"):
            classes.append(f"mahjong-theme-{self.theme}")

        class_str = " ".join(classes)
        label = html.escape(info.display_name + note, quote=True)
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
    def _marker_classes(tile: Tile) -> list[str]:
        """The CSS classes for a tile's position and discard markers."""
        classes = []
        if tile.is_rotated:
            classes.append("mahjong-tile-rotated")
        if tile.is_added:
            classes.append("mahjong-tile-added")
        if tile.is_tsumogiri:
            classes.append("mahjong-tile-tsumogiri")
        if tile.is_called:
            classes.append("mahjong-tile-called")
        return classes

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

    @staticmethod
    def _meld_note(tile: Tile) -> str:
        """Describe a meld tile's sideways position for its accessible name: the tile added to
        a kan, or the tile called from another player."""
        if tile.is_added:
            return " (added)"
        return " (called)" if tile.is_rotated else ""

    def _render_meld(self, meld: Meld, sprite: TileSprite) -> str:
        """Render a meld (called tile group)."""
        state = "open" if meld.is_open else "closed"
        class_str = f"mahjong-meld mahjong-meld-{state}"
        label = " ".join(filter(None, [_MELD_NAMES[meld.meld_type], _SOURCE_NAMES.get(meld.source)]))
        parts = [f'<span class="{class_str}" role="group" aria-label="{label}">']

        if meld.meld_type == MeldType.KAN_ADDED:
            parts.extend(self._render_added_kan(meld, sprite))
        elif meld.meld_type == MeldType.KAN_CLOSED:
            parts.extend(self._render_closed_kan(meld, sprite))
        else:
            parts.extend(self._render_standard_meld(meld, sprite))

        parts.append("</span>")
        return "".join(parts)

    def _render_added_kan(self, meld: Meld, sprite: TileSprite) -> list[str]:
        """Render an added kan (shouminkan): the added tile stacked on top of the called tile,
        whose position depends on the source."""
        t = [self._render_tile(tile, sprite, note=self._meld_note(tile)) for tile in meld.tiles]
        stack_open = '<span class="mahjong-tile-stack">'
        if meld.tiles[0].is_rotated:
            return [stack_open, t[3], t[0], "</span>", t[1], t[2]]
        if meld.tiles[2].is_rotated:
            return [t[0], t[1], stack_open, t[3], t[2], "</span>"]
        return [t[0], stack_open, t[3], t[1], "</span>", t[2]]

    def _render_closed_kan(self, meld: Meld, sprite: TileSprite) -> list[str]:
        """Render a closed kan, with any red fives among the two face-up tiles so they show."""
        fronts = sorted(meld.tiles, key=lambda tile: tile.number != 0)[:2]
        first, second = (self._render_tile(tile, sprite) for tile in fronts)
        back = self._BACK_TILE_HTML
        return [first, back, back, second] if self.closed_kan_style == "inner" else [back, first, second, back]

    def _render_standard_meld(self, meld: Meld, sprite: TileSprite) -> list[str]:
        """Render a chi, pon or open kan."""
        return [self._render_tile(tile, sprite, note=self._meld_note(tile)) for tile in meld.tiles]
