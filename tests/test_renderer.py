"""Tests for the Mahjong renderer."""

from pymdownx_mahjong.parser import Tile, parse_hand
from pymdownx_mahjong.renderer import MahjongRenderer


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

    def test_render_dora_and_ura(self):
        renderer = MahjongRenderer()
        hand = parse_hand("123m456p789s11222z")
        hand.dora_indicators = [Tile(suit="m", number=5)]
        hand.ura_indicators = [Tile(suit="p", number=3)]
        html = renderer.render(hand)

        assert 'class="mahjong-dora-row"' in html
        assert "Dora" in html
        assert "mahjong-ura" in html
        assert "Ura" in html


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

            assert f'mahjong-theme-{theme}' in html.split(">")[0], (
                f"figure should have mahjong-theme-{theme} class"
            )

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
        assert html.count('<use href="#mj-light-1m"/>') == 3

    def test_auto_theme_references_both_themes(self):
        html = MahjongRenderer(theme="auto").render(parse_hand("1m"))

        assert '<symbol id="mj-light-1m"' in html
        assert '<symbol id="mj-dark-1m"' in html

    def test_shared_sprite_is_not_embedded(self):
        from pymdownx_mahjong.sprite import TileSprite

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
        assert "xlink:href" not in html


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
