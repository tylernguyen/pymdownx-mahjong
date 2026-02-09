"""Tests for utility functions."""

from pymdownx_mahjong.parser import Hand, MahjongParser, Tile
from pymdownx_mahjong.utils import apply_hand_options, parse_block_content


class TestParseBlockContent:
    def test_simple_notation(self):
        notation, options = parse_block_content("123m456p789s11222z")

        assert notation == "123m456p789s11222z"
        assert options == {}

    def test_yaml_style_hand(self):
        notation, options = parse_block_content("hand: 123m456p")

        assert notation == "123m456p"
        assert options == {}

    def test_all_options_combined(self):
        content = "hand: 123m\ntitle: Complete Hand\ndora: 5m\nuradora: 3p\ndraw: 1z"
        notation, options = parse_block_content(content)

        assert notation == "123m"
        assert options["title"] == "Complete Hand"
        assert options["dora"] == "5m"
        assert options["uradora"] == "3p"
        assert options["draw"] == "1z"

    def test_mixed_notation_first(self):
        content = "123m456p\ntitle: Mixed Style"
        notation, options = parse_block_content(content)

        assert notation == "123m456p"
        assert options["title"] == "Mixed Style"

    def test_quoted_titles(self):
        assert parse_block_content('title: "Quoted"')[1]["title"] == "Quoted"
        assert parse_block_content("title: 'Single'")[1]["title"] == "Single"

    def test_empty_and_whitespace(self):
        assert parse_block_content("") == ("", {})
        assert parse_block_content("   \n  \n  ") == ("", {})

    def test_case_insensitive_keys(self):
        content = "HAND: 123m\nTITLE: Uppercase Keys\nDORA: 5m"
        notation, options = parse_block_content(content)

        assert notation == "123m"
        assert options["title"] == "Uppercase Keys"
        assert options["dora"] == "5m"


class TestApplyHandOptions:
    def test_apply_all_options(self):
        hand = Hand()
        parser = MahjongParser()
        errors = apply_hand_options(hand, parser, {"dora": "5m3p", "uradora": "3p", "draw": "1z"})

        assert errors == []
        assert len(hand.dora_indicators) == 2
        assert len(hand.uradora_indicators) == 1
        assert hand.draw_tile is not None
        assert hand.draw_tile.notation == "1z"

    def test_invalid_dora_reports_error(self):
        hand = Hand()
        errors = apply_hand_options(hand, MahjongParser(), {"dora": "8z"})

        assert "Invalid dora notation" in errors[0]
        assert len(hand.dora_indicators) == 0

    def test_invalid_draw_reports_error(self):
        hand = Hand()
        errors = apply_hand_options(hand, MahjongParser(), {"draw": "9z"})

        assert "Invalid draw notation" in errors[0]
        assert hand.draw_tile is None
