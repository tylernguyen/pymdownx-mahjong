"""Tests for utility functions."""

import pytest

from pymdownx_mahjong.parser import Hand, MahjongParser, ParseError
from pymdownx_mahjong.utils import apply_hand_options, parse_block_content, parse_hand_block


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
        content = "hand: 123m\ntitle: Complete Hand\ndora: 5m\nura: 3p\ndraw: 1z"
        notation, options = parse_block_content(content)

        assert notation == "123m"
        assert options["title"] == "Complete Hand"
        assert options["dora"] == "5m"
        assert options["ura"] == "3p"
        assert options["draw"] == "1z"

    def test_mixed_notation_first(self):
        content = "123m456p\ntitle: Mixed Style"
        notation, options = parse_block_content(content)

        assert notation == "123m456p"
        assert options["title"] == "Mixed Style"

    def test_unpaired_quotes_kept(self):
        assert parse_block_content("title: The players'")[1]["title"] == "The players'"
        assert parse_block_content("title: 'Tis riichi")[1]["title"] == "'Tis riichi"
        assert parse_block_content("title: \"Mixed'")[1]["title"] == "\"Mixed'"

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

    def test_unknown_key_rejected(self):
        with pytest.raises(ParseError, match="Unknown option 'doras'"):
            parse_block_content("123m\ndoras: 5z")

    def test_second_notation_line_rejected(self):
        with pytest.raises(ParseError, match="Hand notation given more than once: 456p"):
            parse_block_content("123m\n456p")

    def test_notation_line_and_hand_key_rejected(self):
        with pytest.raises(ParseError, match="Hand notation given more than once"):
            parse_block_content("123m\nhand: 456p")


class TestParseHandBlock:
    def test_draw_counted_toward_tile_limit(self):
        with pytest.raises(ParseError, match="1m appears 5 times"):
            parse_hand_block("1111m\ndraw: 1m", MahjongParser())

    def test_draw_within_limit_accepted(self):
        hand, _, _ = parse_hand_block("111m\ndraw: 1m", MahjongParser())
        assert hand.draw_tile is not None
        assert hand.draw_tile.notation == "1m"


class TestApplyHandOptions:
    def test_apply_all_options(self):
        hand = Hand()
        parser = MahjongParser()
        errors = apply_hand_options(hand, parser, {"dora": "5m3p", "ura": "3p", "draw": "1z"})

        assert errors == []
        assert len(hand.dora_indicators) == 2
        assert len(hand.ura_indicators) == 1
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

    def test_multi_tile_draw_reports_error(self):
        hand = Hand()
        errors = apply_hand_options(hand, MahjongParser(), {"draw": "45m"})

        assert errors == ["Invalid draw notation: expected 1 tile, got 2"]
        assert hand.draw_tile is None
