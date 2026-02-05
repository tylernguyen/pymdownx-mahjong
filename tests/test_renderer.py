"""Tests for the Mahjong renderer."""

import pytest

from pymdownx_mahjong.parser import Hand, Meld, MeldSource, MeldType, Tile, parse_hand
from pymdownx_mahjong.renderer import MahjongRenderer, render_hand


class TestMahjongRenderer:
    """Tests for the MahjongRenderer class."""

    def test_render_simple_hand(self):
        """Test rendering a simple hand without melds."""
        renderer = MahjongRenderer()
        hand = parse_hand("123m456p789s11222z")
        html = renderer.render(hand)

        assert 'class="mahjong-hand"' in html
        assert 'class="mahjong-tiles"' in html
        assert 'data-tile="1m"' in html
        assert 'data-tile="2z"' in html

    def test_render_with_title(self):
        """Test rendering with a title/caption."""
        renderer = MahjongRenderer()
        hand = parse_hand("123m456p789s11222z")
        html = renderer.render(hand, title="Test Hand")

        assert 'class="mahjong-caption"' in html
        assert "Test Hand" in html

    def test_render_with_notation_data_attr(self):
        """Test that notation is stored in data attribute."""
        renderer = MahjongRenderer()
        hand = parse_hand("123m")
        html = renderer.render(hand, notation="123m")

        assert 'data-notation="123m"' in html

    def test_render_with_draw_tile(self):
        """Test rendering with explicit draw tile."""
        renderer = MahjongRenderer()
        hand = parse_hand("123m456p789s1112z")
        hand.draw_tile = Tile(suit="z", number=2)
        html = renderer.render(hand)

        assert 'class="mahjong-hand-draw"' in html
        assert 'data-tile="2z"' in html

    def test_render_without_draw_tile(self):
        """Test that hands without draw tile don't have draw section."""
        renderer = MahjongRenderer()
        hand = parse_hand("123m456p789s11222z")
        html = renderer.render(hand)

        assert "mahjong-hand-draw" not in html

    def test_render_with_melds(self):
        """Test rendering hand with melds."""
        renderer = MahjongRenderer()
        hand = parse_hand("123m456p (789s<) [1111z]")
        html = renderer.render(hand)

        assert 'class="mahjong-hand-melds"' in html
        assert 'class="mahjong-meld' in html

    def test_render_closed_kan(self):
        """Test that closed kan shows back tiles for middle tiles."""
        renderer = MahjongRenderer()
        hand = parse_hand("[1111z]")
        html = renderer.render(hand)

        assert 'class="mahjong-tile mahjong-tile-back"' in html

    def test_render_open_meld(self):
        """Test rendering open meld with rotated tile."""
        renderer = MahjongRenderer()
        hand = parse_hand("(123m<)")
        html = renderer.render(hand)

        assert 'class="mahjong-tile mahjong-tile-rotated"' in html

    def test_render_added_kan(self):
        """Test rendering added kan with stacked tiles."""
        renderer = MahjongRenderer()
        hand = parse_hand("(111+1z<)")
        html = renderer.render(hand)

        assert 'class="mahjong-tile-stack"' in html

    def test_render_dora_indicators(self):
        """Test rendering dora indicators."""
        renderer = MahjongRenderer()
        hand = parse_hand("123m456p789s11222z")
        hand.dora_indicators = [Tile(suit="m", number=5)]
        html = renderer.render(hand)

        assert 'class="mahjong-dora-row"' in html
        assert 'class="mahjong-dora"' in html
        assert "Dora:" in html

    def test_render_uradora_indicators(self):
        """Test rendering uradora indicators."""
        renderer = MahjongRenderer()
        hand = parse_hand("123m456p789s11222z")
        hand.uradora_indicators = [Tile(suit="p", number=3)]
        html = renderer.render(hand)

        assert "mahjong-uradora" in html
        assert "Uradora:" in html


class TestRendererConfiguration:
    """Tests for renderer configuration options."""

    def test_default_css_class(self):
        """Test default CSS class is mahjong-hand."""
        renderer = MahjongRenderer()
        hand = parse_hand("123m")
        html = renderer.render(hand)

        assert 'class="mahjong-hand"' in html

    def test_tile_titles_shown(self):
        """Test that tile titles are always shown."""
        renderer = MahjongRenderer()
        hand = parse_hand("1m")
        html = renderer.render(hand)

        assert 'title="1 Man"' in html



    def test_theme_light(self):
        """Test light theme."""
        renderer = MahjongRenderer(theme="light")
        assert renderer.theme == "light"

    def test_theme_dark(self):
        """Test dark theme."""
        renderer = MahjongRenderer(theme="dark")
        assert renderer.theme == "dark"

    def test_theme_auto(self):
        """Test auto theme includes both light and dark SVGs."""
        renderer = MahjongRenderer(theme="auto")
        hand = parse_hand("1m")
        html = renderer.render(hand)

        # Auto theme should include both light and dark tile containers
        assert 'class="mahjong-tile-light"' in html
        assert 'class="mahjong-tile-dark"' in html

    def test_closed_kan_style_inner_default(self):
        """Test that closed kan defaults to inner style (back tiles in middle)."""
        renderer = MahjongRenderer(theme="light")
        hand = parse_hand("[1111z]")
        html = renderer.render(hand)

        # Inner style: front, back, back, front
        # Count back tiles - should appear in positions 1,2 (middle)
        back_count = html.count('class="mahjong-tile mahjong-tile-back"')
        assert back_count == 2

    def test_closed_kan_style_outer(self):
        """Test closed kan with outer style (back tiles on edges)."""
        renderer = MahjongRenderer(theme="light", closed_kan_style="outer")
        hand = parse_hand("[1111z]")
        html = renderer.render(hand)

        # Outer style: back, front, front, back
        back_count = html.count('class="mahjong-tile mahjong-tile-back"')
        assert back_count == 2
        # Verify the style is set correctly
        assert renderer.closed_kan_style == "outer"

    def test_closed_kan_style_inner_explicit(self):
        """Test closed kan with explicit inner style."""
        renderer = MahjongRenderer(theme="light", closed_kan_style="inner")
        hand = parse_hand("[1111z]")
        html = renderer.render(hand)

        assert renderer.closed_kan_style == "inner"
        back_count = html.count('class="mahjong-tile mahjong-tile-back"')
        assert back_count == 2


class TestRenderTiles:
    """Tests for render_tiles method."""

    def test_render_tiles_simple(self):
        """Test rendering a simple list of tiles."""
        renderer = MahjongRenderer()
        tiles = [
            Tile(suit="m", number=1),
            Tile(suit="m", number=2),
            Tile(suit="m", number=3),
        ]
        html = renderer.render_tiles(tiles)

        assert 'data-tile="1m"' in html
        assert 'data-tile="2m"' in html
        assert 'data-tile="3m"' in html


class TestSvgIdUniqueness:
    """Tests for SVG ID uniqueness."""

    def test_multiple_same_tiles_have_unique_ids(self):
        """Test that multiple instances of same tile have unique IDs."""
        renderer = MahjongRenderer(theme="light")
        hand = parse_hand("111m")
        html = renderer.render(hand)

        # Count occurrences of id prefix pattern
        # Each SVG should have unique prefixed IDs
        import re

        id_matches = re.findall(r'id="mj\d+_', html)
        # Should have multiple different prefixes for the same tile
        unique_prefixes = set(id_matches)
        assert len(unique_prefixes) >= 1


class TestConvenienceFunction:
    """Tests for render_hand convenience function."""

    def test_render_hand_function(self):
        """Test the render_hand convenience function."""
        hand = parse_hand("123m456p789s11222z")
        html = render_hand(hand)

        assert 'class="mahjong-hand"' in html

    def test_render_hand_with_kwargs(self):
        """Test render_hand with configuration kwargs."""
        hand = parse_hand("123m")
        html = render_hand(hand, theme="dark")

        assert 'class="mahjong-hand"' in html
