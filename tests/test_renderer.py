"""Tests for the Mahjong renderer."""

import re

import pytest

from pymdownx_mahjong.parser import Hand, MahjongParser, Tile, parse_hand
from pymdownx_mahjong.renderer import MahjongRenderer
from pymdownx_mahjong.sprite import TileSprite


class TestMahjongRenderer:
    def test_render_simple_hand(self):
        renderer = MahjongRenderer()
        hand = parse_hand("123m456p789s11222z")
        html = renderer.render(hand)

        assert "mahjong-hand" in html
        assert 'class="mahjong-tiles"' in html
        assert 'data-tile="1m"' in html

    def test_render_with_title(self):
        renderer = MahjongRenderer()
        hand = parse_hand("123m456p789s11222z")
        html = renderer.render(hand, title="Test Hand")

        assert 'class="mahjong-caption"' in html
        assert "Test Hand" in html

    def test_render_with_notation_data_attr(self):
        renderer = MahjongRenderer()
        hand = parse_hand("123m")
        html = renderer.render(hand, notation="123m")

        assert 'data-notation="123m"' in html

    def test_render_draw_tile(self):
        renderer = MahjongRenderer()
        hand = parse_hand("123m456p789s1112z")
        hand.draw_tile = Tile(suit="z", number=2)
        html = renderer.render(hand)

        assert 'class="mahjong-hand-draw"' in html

        # Without draw tile
        hand2 = parse_hand("123m456p789s11222z")
        html2 = renderer.render(hand2)
        assert "mahjong-hand-draw" not in html2

    def test_render_with_melds(self):
        renderer = MahjongRenderer()
        hand = parse_hand("123m456p (789s<) [1111z]")
        html = renderer.render(hand)

        assert 'class="mahjong-hand-melds"' in html
        assert 'class="mahjong-meld' in html

    def test_render_closed_kan(self):
        renderer = MahjongRenderer()
        hand = parse_hand("[1111z]")
        html = renderer.render(hand)

        assert 'class="mahjong-tile mahjong-tile-back"' in html

    def test_render_open_meld(self):
        renderer = MahjongRenderer()
        hand = parse_hand("(123m<)")
        html = renderer.render(hand)

        assert "mahjong-tile-rotated" in html

    def test_render_added_kan(self):
        renderer = MahjongRenderer()
        hand = parse_hand("(111+1z<)")
        html = renderer.render(hand)

        assert 'class="mahjong-tile-stack"' in html

    @pytest.mark.parametrize(
        ("notation", "tiles_before_stack"),
        [("(111+1m<)", 0), ("(111+1m^)", 1), ("(111+1m>)", 2)],
    )
    def test_added_kan_stacks_on_the_called_tile(self, notation, tiles_before_stack):
        html = MahjongRenderer(theme="light").render(parse_hand(notation), sprite=TileSprite())

        stack = re.search(r'<span class="mahjong-tile-stack">(.*?</svg></span>.*?</svg></span>)</span>(.*)', html)
        assert stack is not None
        assert html[: stack.start()].count("data-tile=") == tiles_before_stack
        assert stack.group(2).count("data-tile=") == 2 - tiles_before_stack
        # Both stacked tiles lie sideways: the called tile and the one added to it.
        assert stack.group(1).count("data-tile=") == 2
        assert stack.group(1).count("mahjong-tile-rotated") == 2
        assert stack.group(1).count("mahjong-tile-added") == 1

    def test_render_dora(self):
        renderer = MahjongRenderer()
        hand = parse_hand("123m456p789s11222z")
        hand.dora_indicators = [Tile(suit="m", number=5)]
        html = renderer.render(hand)

        assert 'class="mahjong-dora-row"' in html
        assert "Dora" in html


class TestRendererConfiguration:
    def test_tile_titles_shown(self):
        renderer = MahjongRenderer()
        hand = parse_hand("1m")
        html = renderer.render(hand)

        assert 'title="1 Man"' in html

    def test_theme_auto(self):
        renderer = MahjongRenderer(theme="auto")
        hand = parse_hand("1m")
        html = renderer.render(hand)

        assert 'class="mahjong-tile-light"' in html
        assert 'class="mahjong-tile-dark"' in html
        # auto theme: no theme class on the container
        assert "mahjong-theme-" not in html.split(">")[0]

    def test_theme_class_on_container(self):
        """Figure container should carry the theme class for CSS targeting."""
        for theme in ("light", "dark"):
            renderer = MahjongRenderer(theme=theme)
            hand = parse_hand("1m")
            html = renderer.render(hand)

            assert f"mahjong-theme-{theme}" in html.split(">")[0], f"figure should have mahjong-theme-{theme} class"

    def test_closed_kan_styles(self):
        for style in ("outer", "inner"):
            renderer = MahjongRenderer(theme="light", closed_kan_style=style)
            hand = parse_hand("[1111z]")
            html = renderer.render(hand)

            back_count = html.count('class="mahjong-tile mahjong-tile-back"')
            assert back_count == 2
            assert renderer.closed_kan_style == style


class TestRenderTiles:
    def test_render_tiles_simple(self):
        renderer = MahjongRenderer()
        tiles = [Tile(suit="m", number=i) for i in (1, 2, 3)]
        html = renderer.render_tiles(tiles)

        assert 'data-tile="1m"' in html
        assert 'data-tile="3m"' in html


class TestSprite:
    def test_symbols_embedded_once_per_call(self):
        renderer = MahjongRenderer(theme="light")
        html = renderer.render(parse_hand("111m"))

        assert html.count('<symbol id="mj-light-1m"') == 1
        assert html.count('<use xlink:href="#mj-light-1m"/>') == 3

    def test_auto_theme_references_both_themes(self):
        html = MahjongRenderer(theme="auto").render(parse_hand("1m"))

        assert '<symbol id="mj-light-1m"' in html
        assert '<symbol id="mj-dark-1m"' in html

    def test_shared_sprite_is_not_embedded(self):
        sprite = TileSprite()
        html = MahjongRenderer(theme="light").render(parse_hand("1m2p"), sprite=sprite)

        assert "<symbol" not in html
        assert 'href="#mj-light-1m"' in html
        assert '<symbol id="mj-light-1m"' in sprite.render()
        assert '<symbol id="mj-light-2p"' in sprite.render()

    def test_output_is_deterministic(self):
        renderer = MahjongRenderer(theme="auto")
        first = renderer.render(parse_hand("123p (111+1z<)"))
        second = renderer.render(parse_hand("123p (111+1z<)"))

        assert first == second

    def test_internal_ids_are_namespaced(self):
        import re

        html = MahjongRenderer(theme="light").render(parse_hand("1p2p"))
        ids = re.findall(r'id="([^"]+)"', html)

        assert len(ids) == len(set(ids))
        assert all(i.startswith(("mj-light-1p", "mj-light-2p")) for i in ids)
        assert 'xlink:href="#mj-light-1p-' in html

    def test_no_plain_fragment_hrefs(self):
        """Zensical's blog rewrites href="#..." in excerpts to point at the post, blanking tiles."""
        html = MahjongRenderer(theme="light").render(parse_hand("1p1s2p"))

        assert ' href="#' not in html


class TestAccessibility:
    def test_tiles_are_labelled_images(self):
        html = MahjongRenderer(theme="light").render(parse_hand("1m"))

        assert 'role="img" aria-label="1 Man"' in html
        assert 'aria-hidden="true"' in html

    def test_face_down_tile_labelled(self):
        html = MahjongRenderer().render(parse_hand("[1111z]"))

        assert 'aria-label="Face-down tile"' in html

    def test_meld_group_labelled(self):
        html = MahjongRenderer().render(parse_hand("(111p^) [1111z]"))

        assert 'role="group" aria-label="Pon from across"' in html
        assert 'role="group" aria-label="Closed kan"' in html

    def test_draw_group_labelled(self):
        hand = parse_hand("123m")
        hand.draw_tile = Tile(suit="z", number=2)
        html = MahjongRenderer().render(hand)

        assert 'class="mahjong-hand-draw" role="group" aria-label="Draw"' in html

    def test_figure_label_only_without_caption(self):
        renderer = MahjongRenderer()

        assert 'aria-label="Mahjong hand"' in renderer.render(parse_hand("1m"))
        assert 'aria-label="Mahjong hand"' not in renderer.render(parse_hand("1m"), title="T")

    def test_face_down_run_announced_once(self):
        html = MahjongRenderer().render(parse_hand("XXXz"))

        assert html.count('role="img"') == 1
        assert 'role="img" aria-label="3 face-down tiles" title="3 face-down tiles"' in html
        assert html.count('aria-hidden="true" title="3 face-down tiles"') == 2
        assert html.count("mahjong-tile-back") == 3

    def test_single_face_down_tile_is_singular(self):
        html = MahjongRenderer().render(parse_hand("Xz"))

        assert 'aria-label="Face-down tile"' in html
        assert "face-down tiles" not in html

    def test_table_hidden_hand_is_one_stop(self):
        html = _block_html("1m\ntoimen.hand:")

        assert html.count("mahjong-tile-standing") == 13
        assert html.count('aria-label="13 face-down tiles"') == 1

    def test_face_down_runs_split_by_face_up_tiles(self):
        hand = parse_hand("XXz")
        hand.closed_tiles.insert(1, Tile(suit="m", number=1))
        html = MahjongRenderer().render(hand)

        assert html.count('aria-label="Face-down tile"') == 2
        assert 'aria-label="1 Man"' in html

    @pytest.mark.parametrize("theme", ["light", "dark", "auto"])
    def test_lang_excludes_english_labels(self, theme):
        html = _block_html("1m\nseat: south\nround: E1\nremaining: 35", theme=theme)

        assert '<span lang="ja">南</span>' in html
        assert '<span lang="ja">東一局</span>' in html
        assert '<span lang="ja">残 35</span>' in html
        assert not re.search(r'<span [^>]*lang="ja"[^>]*aria-label', html)

    def test_title_matches_label(self):
        html = _block_html("1m\nseat: south\nround: E1")

        assert 'aria-label="Seat Wind: South" title="Seat Wind: South"' in html
        assert 'aria-label="Round: East 1" title="Round: East 1"' in html

    def test_closed_tiles_group_labelled(self):
        html = MahjongRenderer().render(parse_hand("123m"))

        assert '<div class="mahjong-hand-left" role="group" aria-label="Hand">' in html

    def test_no_closed_tiles_group_without_closed_tiles(self):
        html = MahjongRenderer().render(parse_hand("(111p^)"))

        assert 'aria-label="Hand"' not in html

    def test_called_meld_tile_labelled(self):
        html = MahjongRenderer().render(parse_hand("(123m<)"))

        assert 'aria-label="1 Man (called)"' in html
        assert 'aria-label="2 Man"' in html
        assert 'aria-label="3 Man"' in html

    def test_added_kan_tiles_labelled(self):
        html = MahjongRenderer().render(parse_hand("(111+1z<)"))

        assert html.count('aria-label="East (called)"') == 1
        assert html.count('aria-label="East (added)"') == 1
        assert html.count('aria-label="East"') == 2

    def test_closed_kan_tiles_have_no_note(self):
        html = MahjongRenderer().render(parse_hand("[1111z]"))

        assert html.count('aria-label="East"') == 2


class TestRendererValidation:
    def test_invalid_theme(self):
        with pytest.raises(ValueError, match="theme"):
            MahjongRenderer(theme="Dark")

    def test_invalid_closed_kan_style(self):
        with pytest.raises(ValueError, match="closed_kan_style"):
            MahjongRenderer(closed_kan_style="inside")


class TestDiscards:
    @staticmethod
    def _render(discards: str, hand: str = "") -> str:
        parser = MahjongParser()
        parsed = parser.parse(hand) if hand else Hand()
        parsed.discards = parser.parse_discards(discards)
        return MahjongRenderer().render(parsed)

    @staticmethod
    def _row_sizes(html: str) -> list[int]:
        rows = html.split('<div class="mahjong-discard-row">')[1:]
        return [row.split("</div>")[0].count("data-tile=") for row in rows]

    @pytest.mark.parametrize(
        ("discards", "sizes"),
        [
            ("12345m", [5]),
            ("123456m", [6]),
            ("123456789m1234p", [6, 6, 1]),
            ("123456789m123456789p1234s", [6, 6, 10]),
        ],
    )
    def test_row_split(self, discards, sizes):
        assert self._row_sizes(self._render(discards)) == sizes

    def test_markers(self):
        html = self._render("t2m c3m r1m")

        assert 'class="mahjong-tile mahjong-tile-rotated mahjong-theme-light"' in html
        assert 'aria-label="1 Man (riichi)"' in html
        assert 'class="mahjong-tile mahjong-tile-tsumogiri mahjong-theme-light"' in html
        assert 'aria-label="2 Man (tsumogiri)"' in html
        assert 'class="mahjong-tile mahjong-tile-called mahjong-theme-light"' in html
        assert 'aria-label="3 Man (called)"' in html

    def test_discards_after_riichi_render_as_tsumogiri(self):
        html = self._render("r1m 2m c3m")

        assert 'class="mahjong-tile mahjong-tile-tsumogiri mahjong-theme-light"' in html
        assert 'aria-label="2 Man (tsumogiri)"' in html
        assert 'aria-label="3 Man (tsumogiri, called)"' in html

    def test_discards_only_has_no_hand_row(self):
        html = self._render("123m")

        assert 'class="mahjong-discards"' in html
        assert "mahjong-hand-row" not in html

    def test_discards_above_hand(self):
        html = self._render("123m", "456p (789s<)")

        assert html.index("mahjong-discards") < html.index("mahjong-hand-row")
        # The riichi note only applies to discards, not to rotated meld tiles.
        assert "(riichi)" not in html


class TestSticks:
    @staticmethod
    def _render(riichi: int = 0, honba: int = 0, hand: str = "123m") -> str:
        parsed = parse_hand(hand)
        parsed.riichi = riichi
        parsed.honba = honba
        return MahjongRenderer().render(parsed)

    def test_riichi_and_honba(self):
        html = self._render(riichi=1, honba=3)

        assert 'aria-label="Riichi sticks: 1"' in html
        assert 'aria-label="Honba: 3"' in html
        assert '<use xlink:href="#mj-tenbou-1000"/>' in html
        assert '<use xlink:href="#mj-tenbou-100"/>' in html
        assert "&times;1" in html
        assert "&times;3" in html
        # Riichi sticks stack above honba.
        assert html.index("mahjong-stick-riichi") < html.index("mahjong-stick-honba")

    def test_sticks_without_dora(self):
        html = self._render(honba=2)

        assert "mahjong-dora-row" not in html
        assert "mahjong-stick-honba" in html
        assert "mahjong-stick-riichi" not in html

    def test_sticks_between_discards_and_hand(self):
        parsed = parse_hand("123m")
        parser = MahjongParser()
        parsed.dora_indicators = parser.parse_tiles("1z")
        parsed.discards = parser.parse_discards("19m")
        parsed.riichi = 2
        html = MahjongRenderer().render(parsed)

        assert (
            html.index('class="mahjong-dora-row"')
            < html.index('class="mahjong-discards"')
            < html.index('class="mahjong-sticks"')
            < html.index('class="mahjong-hand-row"')
        )

    def test_no_sticks(self):
        html = self._render()

        assert "mahjong-sticks" not in html


class TestSeat:
    @staticmethod
    def _render(**attrs) -> str:
        parsed = parse_hand("123m")
        for key, value in attrs.items():
            setattr(parsed, key, value)
        return MahjongRenderer().render(parsed)

    def test_seat_wind_and_score(self):
        html = self._render(seat_wind="south", score=25000)

        assert 'aria-label="Seat Wind: South"' in html
        assert ">南</span>" in html
        assert (
            '<span class="mahjong-score" role="img" aria-label="Score: 25000">'
            '<span class="mahjong-score-thousands">25</span><span class="mahjong-score-hundreds">,000</span></span>'
        ) in html
        assert html.index("mahjong-seat-wind") < html.index("mahjong-score")

    @pytest.mark.parametrize(
        ("score", "thousands", "hundreds"),
        [
            (2500, "2", ",500"),
            (50900, "50", ",900"),
            (1000, "1", ",000"),
            (1250000, "1,250", ",000"),
            (-1000, "-1", ",000"),
        ],
    )
    def test_score_split_at_thousands_with_commas(self, score, thousands, hundreds):
        html = self._render(score=score)

        assert (
            f'<span class="mahjong-score-thousands">{thousands}</span>'
            f'<span class="mahjong-score-hundreds">{hundreds}</span>'
        ) in html

    @pytest.mark.parametrize("score", [0, 500, -500])
    def test_score_below_thousand_has_no_thousands(self, score):
        html = self._render(score=score)

        assert "mahjong-score-thousands" not in html
        assert f'<span class="mahjong-score-hundreds">{score}</span>' in html

    def test_zero_score_shown(self):
        html = self._render(score=0)

        assert 'aria-label="Score: 0"' in html
        assert "mahjong-seat-wind" not in html

    def test_seat_left_of_sticks_in_status_row(self):
        html = self._render(seat_wind="east", riichi=1)

        status = html[html.index('class="mahjong-status"') : html.index('class="mahjong-hand-row"')]
        assert status.index('class="mahjong-seat"') < status.index('class="mahjong-sticks"')

    def test_seat_without_sticks(self):
        html = self._render(seat_wind="north")

        assert 'class="mahjong-status"' in html
        assert "mahjong-sticks" not in html

    def test_no_status_row(self):
        html = self._render()

        assert "mahjong-status" not in html
        assert "mahjong-seat" not in html


class TestDoraWall:
    @staticmethod
    def _dora_tiles(dora: str) -> str:
        parsed = parse_hand("123m")
        parsed.dora_indicators = MahjongParser().parse_tiles(dora)
        html = MahjongRenderer().render(parsed)
        return html.split('<span class="mahjong-dora-tiles mahjong-dora-wall">')[1].split("</span></div>")[0]

    @pytest.mark.parametrize(("dora", "backs"), [("3m", 4), ("3m7z1p", 2), ("12345m", 0), ("123456m", 0)])
    def test_pads_to_five_slots_with_face_down_tiles(self, dora, backs):
        tiles = self._dora_tiles(dora)

        assert tiles.count("mahjong-tile-back") == backs
        # Face-down filler comes first, so the indicators sit at the right end.
        if backs:
            assert tiles.rindex("mahjong-tile-back") < tiles.index("data-tile=")

    def test_filler_is_hidden_from_screen_readers(self):
        tiles = self._dora_tiles("3m")

        assert tiles.count('aria-hidden="true"></span>') == 4
        assert "Face-down tile" not in tiles


class TestDoraLabel:
    @pytest.mark.parametrize(("dora", "label"), [("3m", "Dora indicator"), ("3m7z", "Dora indicators")])
    def test_accessible_label_pluralizes(self, dora, label):
        parsed = parse_hand("123m")
        parsed.dora_indicators = MahjongParser().parse_tiles(dora)
        html = MahjongRenderer().render(parsed)

        assert f'<div class="mahjong-dora" role="group" aria-label="{label}">' in html

    def test_no_visible_label(self):
        parsed = parse_hand("123m")
        parsed.dora_indicators = MahjongParser().parse_tiles("3m")
        html = MahjongRenderer().render(parsed)

        assert "mahjong-dora-label" not in html


def _owning_player(css_class, html):
    """The table player ("self", "shimo", ...) whose area holds the one element with ``css_class``."""
    marker = f'class="{css_class}"'
    assert html.count(marker) == 1
    before = html[: html.index(marker)]
    return re.findall(r'class="mahjong-player mahjong-player-(\w+)"', before)[-1]


def _block_html(block, **kwargs):
    from pymdownx_mahjong.utils import parse_hand_block

    hand, _, _ = parse_hand_block(block, MahjongParser())
    return MahjongRenderer(**kwargs).render(hand)


class TestTable:
    BLOCK = (
        "123m456p789s11z\nseat: west\nscore: 2500\nriichi: 1\ndora: 3m\nround: S2\nremaining: 35\n"
        "shimo.hand:\nshimo.score: 50900\ntoimen.hand: (777z<)\nkami.hand: 1155m\nkami.discards: 9p"
    )

    def test_single_hand_has_no_table(self):
        html = MahjongRenderer().render(parse_hand("123m"))

        assert "mahjong-table" not in html
        assert "mahjong-player" not in html

    def test_same_figure_as_a_single_hand(self):
        html = _block_html(self.BLOCK)

        assert html.startswith('<figure class="mahjong-hand mahjong-theme-light" aria-label="Mahjong hand">')
        assert '<div class="mahjong-table">' in html

    def test_players_in_turn_order(self):
        html = _block_html(self.BLOCK)

        players = [
            '<div class="mahjong-player mahjong-player-self" role="group" aria-label="Bottom player">',
            '<div class="mahjong-player mahjong-player-shimo" role="group" aria-label="Shimocha (right)">',
            '<div class="mahjong-player mahjong-player-toimen" role="group" aria-label="Toimen (across)">',
            '<div class="mahjong-player mahjong-player-kami" role="group" aria-label="Kamicha (left)">',
        ]
        positions = [html.index(player) for player in players]
        assert positions == sorted(positions)

    def test_missing_player_omitted(self):
        html = _block_html("123m\nshimo.hand:")

        assert "mahjong-player-shimo" in html
        assert "mahjong-player-toimen" not in html
        assert "mahjong-player-kami" not in html

    def test_bottom_player_matches_single_hand(self):
        block = "123m456p789s11z\nseat: west\nscore: 2500\nriichi: 1\ndiscards: 1z 9p"
        single = _block_html(block)
        table = _block_html(block + "\nshimo.hand:")

        single_body = single[single.index('<div class="mahjong-discards"') : single.index("</figure>")]
        assert f'aria-label="Bottom player">{single_body}</div>' in table

    def test_dora_row_holds_round_and_remaining(self):
        html = _block_html(self.BLOCK)
        dora_row = html[html.index('<div class="mahjong-dora-row">') : html.index("mahjong-player-self")]

        assert '<div class="mahjong-dora"' in dora_row
        assert '<span class="mahjong-round" role="img" aria-label="Round: South 2"' in dora_row
        assert ">南二局</span>" in dora_row
        assert ">残 35</span>" in dora_row
        assert 'aria-label="35 tiles remaining"' in dora_row

    def test_opponent_labels(self):
        html = _block_html(self.BLOCK)
        shimo = html[html.index("mahjong-player-shimo") : html.index("mahjong-player-toimen")]

        assert 'aria-label="Seat Wind: North"' in shimo
        assert 'aria-label="Score: 50900"' in shimo

    def test_sticks_with_dealer(self):
        # The bottom player is west, so toimen is east.
        assert _owning_player("mahjong-sticks", _block_html(self.BLOCK)) == "toimen"

    def test_sticks_with_bottom_player_as_dealer(self):
        html = _block_html("123m\nseat: east\nriichi: 1\nshimo.hand:")

        assert _owning_player("mahjong-sticks", html) == "self"

    def test_sticks_with_explicit_east_opponent(self):
        html = _block_html("123m\nhonba: 2\nkami.hand:\nkami.seat: east")

        assert _owning_player("mahjong-sticks", html) == "kami"

    def test_sticks_with_bottom_player_without_dealer(self):
        html = _block_html("123m\nriichi: 1\nshimo.hand:")

        assert _owning_player("mahjong-sticks", html) == "self"

    def test_dealer_status_row_holds_only_sticks_without_seat_or_score(self):
        html = _block_html("123m\nseat: west\nriichi: 1\ntoimen.hand:\ntoimen.seat: east")
        toimen = html[html.index("mahjong-player-toimen") :]

        assert '<div class="mahjong-status"><div class="mahjong-sticks">' not in toimen
        assert 'aria-label="Seat Wind: East"' in toimen

    def test_face_down_opponent_hand(self):
        html = _block_html(self.BLOCK)
        shimo = html[html.index("mahjong-player-shimo") : html.index("mahjong-player-toimen")]

        assert shimo.count('class="mahjong-tile mahjong-tile-back mahjong-tile-standing"') == 13

    def test_only_other_players_hidden_tiles_stand(self):
        html = _block_html("XXXz123m\nshimo.hand: (777z<)")
        self_part = html[html.index("mahjong-player-self") : html.index("mahjong-player-shimo")]
        shimo = html[html.index("mahjong-player-shimo") :]

        assert "mahjong-tile-standing" not in self_part
        assert shimo.count("mahjong-tile-standing") == 10

    def test_closed_kan_backs_do_not_stand(self):
        html = _block_html("123m\nshimo.hand: [7777z]")
        meld = html[html.index('class="mahjong-hand-melds"') :]

        assert "mahjong-tile-back" in meld
        assert "mahjong-tile-standing" not in meld

    def test_opponent_discards(self):
        html = _block_html(self.BLOCK)
        kami = html[html.index("mahjong-player-kami") :]

        assert '<div class="mahjong-discards" role="group" aria-label="Discards">' in kami
        assert 'data-tile="9p"' in kami


class TestRoundInfo:
    def test_round_and_remaining_beside_dora(self):
        html = _block_html("123m\ndora: 3m\nround: E1\nremaining: 70")
        dora_row = html[html.index('<div class="mahjong-dora-row">') : html.index('<div class="mahjong-hand-row">')]

        assert dora_row.index('class="mahjong-dora"') < dora_row.index('<span class="mahjong-round-info">')
        assert ">東一局</span>" in dora_row
        assert ">残 70</span>" in dora_row

    def test_round_without_dora(self):
        html = _block_html("123m\nround: N4")

        assert '<div class="mahjong-dora-row"><span class="mahjong-round-info">' in html
        assert 'class="mahjong-dora"' not in html


class TestEmptyBottomPlayer:
    def test_no_bottom_area_with_only_other_players(self):
        html = _block_html("toimen.discards: 1m 2m")

        assert "mahjong-player-self" not in html
        assert "mahjong-player-toimen" in html

    def test_no_bottom_area_when_another_player_has_a_seat(self):
        assert "mahjong-player-self" not in _block_html("toimen.seat: east\ntoimen.discards: 1m 2m")

    @pytest.mark.parametrize("option", ["score: 0", "seat: west", "riichi: 1", "discards: 1m"])
    def test_bottom_area_kept_with_content(self, option):
        assert "mahjong-player-self" in _block_html(f"{option}\ntoimen.discards: 2m")


class TestRoundMarker:
    BASE = "123m\nseat: west\nshimo.hand:\ntoimen.hand:\nkami.hand:"

    @pytest.mark.parametrize(
        ("round_", "player"),
        # The bottom player is west, so shimocha is north, toimen east and kamicha south.
        [("E1", "toimen"), ("E2", "shimo"), ("E3", "self"), ("E4", "kami"), ("S1", "toimen"), ("S2", "shimo")],
    )
    def test_marker_with_original_dealer(self, round_, player):
        html = _block_html(f"{self.BASE}\nround: {round_}")

        assert _owning_player("mahjong-round-marker", html) == player

    @pytest.mark.parametrize(("round_", "name"), [("E2", "East"), ("S3", "South")])
    def test_marker_matches_round_wind(self, round_, name):
        html = _block_html(f"{self.BASE}\nround: {round_}")

        assert f'aria-label="Round marker: {name}"' in html
        assert f'href="#mj-marker-{name}"' in html

    def test_marker_has_tile_sized_default(self):
        html = _block_html(f"{self.BASE}\nround: E1")
        marker = html[html.index('class="mahjong-round-marker"') :]

        assert marker.startswith('class="mahjong-round-marker"')
        assert '<svg width="45" height="30"' in marker

    @pytest.mark.parametrize("round_", ["W1", "N2"])
    def test_no_marker_for_west_or_north_rounds(self, round_):
        assert "mahjong-round-marker" not in _block_html(f"{self.BASE}\nround: {round_}")

    def test_no_marker_without_seat_winds(self):
        assert "mahjong-round-marker" not in _block_html("123m\nround: E1\nshimo.hand:")

    def test_marker_after_sticks_when_original_dealer_deals(self):
        html = _block_html(f"{self.BASE}\nround: S1\nriichi: 1")
        toimen = html[html.index("mahjong-player-toimen") : html.index("mahjong-player-kami")]

        assert toimen.index('class="mahjong-sticks"') < toimen.index('class="mahjong-round-marker"')

    def test_marker_without_sticks_when_dealer_moved_on(self):
        html = _block_html(f"{self.BASE}\nround: E2\nriichi: 1")
        shimo = html[html.index("mahjong-player-shimo") : html.index("mahjong-player-toimen")]

        assert "mahjong-sticks" not in shimo
        assert 'class="mahjong-round-marker"' in shimo

    def test_single_hand_marker_when_original_dealer(self):
        html = _block_html("123m\nseat: north\nround: E2")
        status = html[html.index('<div class="mahjong-status">') :]

        assert 'aria-label="Round marker: East"' in status

    def test_single_hand_no_marker_otherwise(self):
        assert "mahjong-round-marker" not in _block_html("123m\nseat: east\nround: E2")


class TestMarkerSymbol:
    def test_svg_symbol_keeps_viewbox(self):
        from pymdownx_mahjong.sprite import load_symbol

        symbol = load_symbol("East", "marker")

        assert symbol.startswith('<symbol id="mj-marker-East" viewBox="0 0 567 374">')
        assert "<path" in symbol
        assert "<image" not in symbol

    def test_missing_svg_uses_placeholder(self):
        from pymdownx_mahjong.sprite import load_symbol

        assert "<rect" in load_symbol("West", "marker")
