"""Tests for utility functions."""

import pytest

from pymdownx_mahjong.parser import Hand, MahjongParser, Tile
from pymdownx_mahjong.utils import apply_hand_options, parse_block_content


class TestParseBlockContent:
    """Tests for the parse_block_content function."""

    def test_simple_notation(self):
        """Test parsing simple notation string."""
        notation, options = parse_block_content("123m456p789s11222z")

        assert notation == "123m456p789s11222z"
        assert options == {}

    def test_yaml_style_hand(self):
        """Test parsing YAML-style hand notation."""
        notation, options = parse_block_content("hand: 123m456p")

        assert notation == "123m456p"
        assert options == {}

    def test_yaml_style_with_title(self):
        """Test parsing with title option."""
        content = """hand: 123m456p
title: My Test Hand"""
        notation, options = parse_block_content(content)

        assert notation == "123m456p"
        assert options["title"] == "My Test Hand"

    def test_yaml_style_with_dora(self):
        """Test parsing with dora option."""
        content = """hand: 123m456p
dora: 5m"""
        notation, options = parse_block_content(content)

        assert notation == "123m456p"
        assert options["dora"] == "5m"

    def test_yaml_style_with_uradora(self):
        """Test parsing with uradora option."""
        content = """hand: 123m456p
uradora: 3p"""
        notation, options = parse_block_content(content)

        assert notation == "123m456p"
        assert options["uradora"] == "3p"

    def test_yaml_style_with_draw(self):
        """Test parsing with draw option."""
        content = """hand: 123m456p
draw: 1z"""
        notation, options = parse_block_content(content)

        assert notation == "123m456p"
        assert options["draw"] == "1z"

    def test_all_options_combined(self):
        """Test parsing with all options."""
        content = """hand: 123m
title: Complete Hand
dora: 5m
uradora: 3p
draw: 1z"""
        notation, options = parse_block_content(content)

        assert notation == "123m"
        assert options["title"] == "Complete Hand"
        assert options["dora"] == "5m"
        assert options["uradora"] == "3p"
        assert options["draw"] == "1z"

    def test_mixed_notation_first(self):
        """Test notation on first line followed by options."""
        content = """123m456p
title: Mixed Style"""
        notation, options = parse_block_content(content)

        assert notation == "123m456p"
        assert options["title"] == "Mixed Style"

    def test_quoted_title(self):
        """Test that quotes are stripped from title."""
        content = 'title: "Quoted Title"'
        notation, options = parse_block_content(content)

        assert options["title"] == "Quoted Title"

    def test_single_quoted_title(self):
        """Test that single quotes are stripped from title."""
        content = "title: 'Single Quoted'"
        notation, options = parse_block_content(content)

        assert options["title"] == "Single Quoted"

    def test_empty_content(self):
        """Test parsing empty content."""
        notation, options = parse_block_content("")

        assert notation == ""
        assert options == {}

    def test_whitespace_only(self):
        """Test parsing whitespace-only content."""
        notation, options = parse_block_content("   \n  \n  ")

        assert notation == ""
        assert options == {}

    def test_case_insensitive_keys(self):
        """Test that keys are case-insensitive."""
        content = """HAND: 123m
TITLE: Uppercase Keys
DORA: 5m"""
        notation, options = parse_block_content(content)

        assert notation == "123m"
        assert options["title"] == "Uppercase Keys"
        assert options["dora"] == "5m"


class TestApplyHandOptions:
    """Tests for the apply_hand_options function."""

    def test_apply_dora(self):
        """Test applying dora indicators."""
        hand = Hand()
        parser = MahjongParser()
        options = {"dora": "5m"}

        apply_hand_options(hand, parser, options)

        assert len(hand.dora_indicators) == 1
        assert hand.dora_indicators[0].notation == "5m"

    def test_apply_multiple_dora(self):
        """Test applying multiple dora indicators."""
        hand = Hand()
        parser = MahjongParser()
        options = {"dora": "5m3p"}

        apply_hand_options(hand, parser, options)

        assert len(hand.dora_indicators) == 2

    def test_apply_uradora(self):
        """Test applying uradora indicators."""
        hand = Hand()
        parser = MahjongParser()
        options = {"uradora": "3p"}

        apply_hand_options(hand, parser, options)

        assert len(hand.uradora_indicators) == 1
        assert hand.uradora_indicators[0].notation == "3p"

    def test_apply_draw(self):
        """Test applying draw tile."""
        hand = Hand()
        parser = MahjongParser()
        options = {"draw": "1z"}

        apply_hand_options(hand, parser, options)

        assert hand.draw_tile is not None
        assert hand.draw_tile.notation == "1z"

    def test_apply_all_options(self):
        """Test applying all options together."""
        hand = Hand()
        parser = MahjongParser()
        options = {
            "dora": "5m",
            "uradora": "3p",
            "draw": "1z",
        }

        apply_hand_options(hand, parser, options)

        assert len(hand.dora_indicators) == 1
        assert len(hand.uradora_indicators) == 1
        assert hand.draw_tile is not None

    def test_invalid_dora_ignored(self):
        """Test that invalid dora notation is silently ignored."""
        hand = Hand()
        parser = MahjongParser()
        options = {"dora": "8z"}  # Invalid honor tile

        # Should not raise, just ignore
        apply_hand_options(hand, parser, options)

        assert len(hand.dora_indicators) == 0

    def test_invalid_draw_ignored(self):
        """Test that invalid draw notation is silently ignored."""
        hand = Hand()
        parser = MahjongParser()
        options = {"draw": "9z"}  # Invalid honor tile

        apply_hand_options(hand, parser, options)

        assert hand.draw_tile is None

    def test_empty_options(self):
        """Test applying empty options does nothing."""
        hand = Hand()
        hand.closed_tiles = [Tile(suit="m", number=1)]
        parser = MahjongParser()

        apply_hand_options(hand, parser, {})

        assert len(hand.dora_indicators) == 0
        assert len(hand.uradora_indicators) == 0
        assert hand.draw_tile is None
