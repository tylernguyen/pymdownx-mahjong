"""Tests for the Markdown extension."""

import markdown
import pytest


class TestMahjongExtension:
    def test_block_processor_not_registered(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        assert "mahjong" not in md.parser.blockprocessors

    def test_inline_processor_registered_by_default(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        assert "mahjong_inline" in md.inlinePatterns

    def test_inline_code_processor_registered_by_default(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        assert "mahjong_inline_code" in md.inlinePatterns

    def test_inline_processor_disabled(self):
        md = markdown.Markdown(
            extensions=["pymdownx_mahjong"],
            extension_configs={"pymdownx_mahjong": {"enable_inline": "false"}},
        )
        assert "mahjong_inline" not in md.inlinePatterns
        assert "mahjong_inline_code" not in md.inlinePatterns

    def test_inline_code_renders_hand_as_tiles(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert("A hand `mj:1112345678999p` here")
        assert "mahjong-inline" in out
        assert "<code" not in out

    def test_inline_face_down_tile(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert("a :Xz: b")
        assert out.count("mahjong-tile-back") == 1
        assert "mahjong-inline" in out

    def test_inline_face_down_outside_z_suit_stays_text(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert("a :Xm: b `mj:Xm` c")
        assert "mahjong-inline" not in out
        assert ":Xm:" in out
        assert "<code>mj:Xm</code>" in out

    def test_inline_face_down_mixed_with_tiles(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert(":1mXz3m:")
        assert out.count("mahjong-tile-back") == 1
        assert out.count('data-tile="1m"') == 1
        assert out.count('data-tile="3m"') == 1

    @pytest.mark.parametrize("text", ["at 10:30m:15", "ratio 1:2m:3", "a:1m:", ":1m:b", ":1m:2m:"])
    def test_inline_tiles_not_matched_inside_text(self, text):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert(text)
        assert "mahjong-inline" not in out
        assert text in out

    @pytest.mark.parametrize(
        ("text", "count"),
        [
            (":1m:", 1),
            ("(:1m:), :2p:.", 2),
            (":1m::2m:", 2),
            ("**:1m:**", 1),
            ("手牌:1m:です", 1),
        ],
    )
    def test_inline_tiles_matched_beside_non_alphanumerics(self, text, count):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        assert md.convert(text).count('class="mahjong-inline"') == count

    def test_double_backtick_escapes_mj_code(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert("``mj:123456789m``")
        assert "mahjong-inline" not in out
        assert "<code>mj:123456789m</code>" in out

    def test_plain_code_span_is_not_rendered(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert("Plain `123m` code")
        assert "<code>123m</code>" in out
        assert "mahjong-inline" not in out

    @pytest.mark.parametrize(
        ("text", "kind"),
        [
            ("`mj:(123m<)`", "Chi from left"),
            ("`mj:(111p^)`", "Pon from across"),
            ("`mj:(999s>)`", "Pon from right"),
            ("`mj:(1111m<)`", "Open kan from left"),
            ("`mj:[1111z]`", "Closed kan"),
            ("`mj:(666+6z^)`", "Added kan from across"),
        ],
    )
    def test_inline_meld(self, text, kind):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert(text)
        assert out.count('class="mahjong-inline"') == 1
        assert f'aria-label="{kind}"' in out
        assert "<code" not in out

    def test_inline_closed_tiles_precede_melds(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert("`mj:(640m<) [3333z] 11p`")
        assert out.count("mahjong-meld ") == 2
        assert out.index('data-tile="1p"') < out.index("mahjong-meld ")

    def test_inline_melds_on_one_line_stay_separate(self):
        """`<` and `>` in two spans mustn't be taken for an HTML tag between them."""
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert("a `mj:(123m<)` b `mj:(111p>)` c")
        assert out.count('class="mahjong-inline"') == 2
        assert "&lt;" not in out

    def test_inline_closed_kan_uses_closed_kan_style(self):
        md = markdown.Markdown(
            extensions=["pymdownx_mahjong"],
            extension_configs={"pymdownx_mahjong": {"closed_kan_style": "inner"}},
        )
        out = md.convert("`mj:[1111z]`")
        # inner: front, back, back, front
        assert out.count("mahjong-tile-back") == 2
        assert out.index('data-tile="1z"') < out.index("mahjong-tile-back")

    @pytest.mark.parametrize(
        "notation",
        ["(123m]", "(124m<)", "(123m^)", "[111z]", "(XXXz)", "(111m<) (111m^)", "(123m<"],
    )
    def test_invalid_inline_meld_stays_code(self, notation):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert(f"`mj:{notation}`")
        assert "mahjong-inline" not in out
        assert "<code>mj:" in out

    def test_double_backtick_escapes_inline_meld(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert("``mj:[1111z]``")
        assert "mahjong-inline" not in out
        assert "<code>mj:[1111z]</code>" in out

    def test_inline_plain_tiles_needn_t_be_a_legal_hand(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        assert md.convert("`mj:11111m`").count('data-tile="1m"') == 5

    def test_inline_meld_symbols_join_the_page_sprite(self):
        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        out = md.convert(":1m: `mj:(123m<)`")
        assert out.count('<symbol id="mj-light-1m"') == 1

    def test_extension_registered_for_superfences(self):
        from pymdownx_mahjong import MahjongExtension

        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        assert any(isinstance(ext, MahjongExtension) for ext in md.registeredExtensions)


class TestPageSprite:
    def _md(self):
        from pymdownx_mahjong import superfences_formatter

        config = {"custom_fences": [{"name": "mahjong", "class": "mahjong", "format": superfences_formatter}]}
        return markdown.Markdown(
            extensions=["pymdownx_mahjong", "pymdownx.superfences"],
            extension_configs={"pymdownx_mahjong": {"theme": "light"}, "pymdownx.superfences": config},
        )

    def test_symbols_emitted_once_per_page(self):
        md = self._md()
        out = md.convert(":1m: and :1m2m:\n\n```mahjong\n111m\n```\n\n```mahjong\n1m\n```")

        assert out.count('<symbol id="mj-light-1m"') == 1
        assert out.count('<symbol id="mj-light-2m"') == 1
        assert out.count('class="mahjong-sprite"') == 1
        assert out.startswith('<div aria-hidden="true" class="mahjong-sprite"')

    def test_sprite_survives_toc(self):
        """toc runs postprocessors on its own fragment; the sprite must stay in the page."""
        md = markdown.Markdown(extensions=["toc", "pymdownx_mahjong"])
        out = md.convert("# Title :1m:\n\n:2p:")

        assert '<symbol id="mj-light-1m"' in out
        assert '<symbol id="mj-light-2p"' in out
        assert "mahjong-sprite" not in md.toc

    def test_sprite_does_not_hide_first_heading(self):
        """MkDocs takes the page title from the first element, which must stay the h1."""
        from markdown.treeprocessors import Treeprocessor

        seen = []

        class FirstTag(Treeprocessor):
            def run(self, root):
                seen.append(root[0].tag)

        md = markdown.Markdown(extensions=["pymdownx_mahjong"])
        md.treeprocessors.register(FirstTag(md), "first_tag", 1)
        md.convert("# Title\n\n:1m:")

        assert seen == ["h1"]

    def test_sprite_resets_between_pages(self):
        md = self._md()
        md.convert(":1m:")
        out = md.reset().convert(":2p:")

        assert "mj-light-1m" not in out
        assert '<symbol id="mj-light-2p"' in out

    def test_no_sprite_without_tiles(self):
        md = self._md()
        assert "mahjong-sprite" not in md.convert("plain text")


class TestMakeExtension:
    def test_make_extension_with_config(self):
        from pymdownx_mahjong import makeExtension

        ext = makeExtension(theme="dark", enable_inline="false", closed_kan_style="inner")
        assert ext.getConfig("theme") == "dark"
        assert ext.getConfig("enable_inline") == "false"
        assert ext.getConfig("closed_kan_style") == "inner"


class TestConfigPropagation:
    """Extension config must flow through to the superfences renderer of the same Markdown instance."""

    @staticmethod
    def _md(**config):
        from pymdownx_mahjong import superfences_formatter, superfences_validator

        fences = [
            {
                "name": "mahjong",
                "class": "mahjong",
                "format": superfences_formatter,
                "validator": superfences_validator,
            }
        ]
        return markdown.Markdown(
            extensions=["pymdownx_mahjong", "pymdownx.superfences"],
            extension_configs={"pymdownx_mahjong": config, "pymdownx.superfences": {"custom_fences": fences}},
        )

    def test_fence_uses_extension_config(self):
        out = self._md(theme="dark", closed_kan_style="inner").convert("```mahjong\n[1111z]\n```")
        assert "mahjong-theme-dark" in out
        # inner: front, back, back, front
        assert out.count("mahjong-tile-back") == 2

    def test_fence_uses_tile_back_color(self):
        out = self._md(tile_back_color="#2e7d6b").convert("```mahjong\n[1111z]\n```")
        assert '<figure class="mahjong-hand" style="--mahjong-tile-back: #2e7d6b"' in out

    def test_inline_tiles_use_tile_back_color(self):
        out = self._md(tile_back_color="teal").convert("Tile :Xz: here")
        assert '<span class="mahjong-inline" style="--mahjong-tile-back: teal">' in out

    def test_fence_uses_table_color(self):
        out = self._md(table_color="#2b7a78").convert("```mahjong\n123m\nshimo.hand:\n```")
        assert '<figure class="mahjong-hand" style="--mahjong-table-bg: #2b7a78"' in out
        assert '<div class="mahjong-table mahjong-table-filled">' in out

    def test_table_transparent_by_default(self):
        out = self._md().convert("```mahjong\n123m\nshimo.hand:\n```")
        assert "--mahjong-table-bg" not in out
        assert '<div class="mahjong-table">' in out

    def test_both_colors_share_one_style(self):
        out = self._md(tile_back_color="teal", table_color="#2b7a78").convert("```mahjong\n123m\n```")
        assert 'style="--mahjong-tile-back: teal; --mahjong-table-bg: #2b7a78"' in out

    def test_no_style_without_tile_back_color(self):
        out = self._md().convert("```mahjong\n123m\n```\n\n:1m:")
        assert "--mahjong-tile-back" not in out

    def test_config_does_not_leak_between_instances(self):
        dark = self._md(theme="dark")
        self._md(theme="light")
        out = dark.convert("```mahjong\n123m\n```")
        assert "mahjong-theme-dark" in out
        assert "mahjong-theme-light" not in out


class TestConfigValidation:
    def test_invalid_theme_rejected(self):
        with pytest.raises(ValueError, match="theme"):
            markdown.Markdown(
                extensions=["pymdownx_mahjong"],
                extension_configs={"pymdownx_mahjong": {"theme": "Dark"}},
            )

    @pytest.mark.parametrize(
        "color",
        [
            "url(x.png)",
            "red; color: blue",
            "#12345",
            "var(--x)",
            '"><script>',
            "rgb(1 2 3) url(//evil.example/x.png)",
            "color-mix(in srgb, red, red) url(x.png)",
            "rgb(1 2 3))",
            "rgb(url(x))",
            "color-mix(in srgb, url(x.png), red)",
            "teall",
            "foo",
        ],
    )
    def test_invalid_tile_back_color_rejected(self, color):
        with pytest.raises(ValueError, match="tile_back_color"):
            markdown.Markdown(
                extensions=["pymdownx_mahjong"],
                extension_configs={"pymdownx_mahjong": {"tile_back_color": color}},
            )

    @pytest.mark.parametrize("color", ["url(x.png)", "red; color: blue", '"><script>'])
    def test_invalid_table_color_rejected(self, color):
        with pytest.raises(ValueError, match="table_color"):
            markdown.Markdown(
                extensions=["pymdownx_mahjong"],
                extension_configs={"pymdownx_mahjong": {"table_color": color}},
            )

    @pytest.mark.parametrize(
        "color",
        [
            "#e7b246",
            "#abc",
            "teal",
            "Teal",
            "transparent",
            "rgb(231 178 70)",
            "oklch(70% 0.1 200)",
            "color-mix(in srgb, teal, #000 10%)",
            "color-mix(in srgb, rgb(1 2 3), hsl(0 0% 50%))",
        ],
    )
    def test_valid_tile_back_color_accepted(self, color):
        markdown.Markdown(
            extensions=["pymdownx_mahjong"], extension_configs={"pymdownx_mahjong": {"tile_back_color": color}}
        )

    def test_invalid_closed_kan_style_rejected(self):
        with pytest.raises(ValueError, match="closed_kan_style"):
            markdown.Markdown(
                extensions=["pymdownx_mahjong"],
                extension_configs={"pymdownx_mahjong": {"closed_kan_style": "inside"}},
            )
