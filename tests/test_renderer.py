"""Tests for the Mahjong renderer."""

from pymdownx_mahjong.parser import Tile, parse_hand
from pymdownx_mahjong.renderer import MahjongRenderer


class TestMahjongRenderer:
    def test_render_simple_hand(self):
        renderer = MahjongRenderer()
        hand = parse_hand("123m456p789s11222z")
        html = renderer.render(hand)

        assert 'class="mahjong-hand"' in html
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

    def test_render_dora_and_uradora(self):
        renderer = MahjongRenderer()
        hand = parse_hand("123m456p789s11222z")
        hand.dora_indicators = [Tile(suit="m", number=5)]
        hand.uradora_indicators = [Tile(suit="p", number=3)]
        html = renderer.render(hand)

        assert 'class="mahjong-dora-row"' in html
        assert "Dora:" in html
        assert "mahjong-uradora" in html
        assert "Uradora:" in html


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


class TestSvgIdUniqueness:
    def test_multiple_same_tiles_have_unique_ids(self, monkeypatch):
        import re

        import pymdownx_mahjong.renderer as renderer_mod

        monkeypatch.setattr(
            renderer_mod,
            "_load_and_process_svg",
            lambda asset_name, theme: '<svg id="root"><g id="layer1"></g></svg>',
        )

        renderer = MahjongRenderer(theme="light")
        hand = parse_hand("111m")
        html = renderer.render(hand)

        id_matches = re.findall(r'id="mj\d+_', html)
        unique_prefixes = set(id_matches)
        assert len(unique_prefixes) >= 1
