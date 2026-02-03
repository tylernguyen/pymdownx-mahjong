"""Tests for the MPSZ notation parser."""

import pytest

from pymdownx_mahjong.parser import (
    MahjongParser,
    Meld,
    MeldSource,
    MeldType,
    ParseError,
    Tile,
    parse_hand,
    parse_tiles,
)


class TestTile:
    """Tests for the Tile class."""

    def test_tile_notation(self):
        """Test tile notation property."""
        tile = Tile(suit="m", number=1)
        assert tile.notation == "1m"

    def test_tile_display_name(self):
        """Test tile display name."""
        tile = Tile(suit="m", number=1)
        assert tile.display_name == "1 Man"

    def test_tile_honor_display_name(self):
        """Test honor tile display name."""
        tile = Tile(suit="z", number=1)
        assert tile.display_name == "East"

    def test_tile_red_dora(self):
        """Test red dora tile."""
        tile = Tile(suit="m", number=0)
        assert tile.display_name == "Red 5 Man"


class TestMahjongParser:
    """Tests for the MahjongParser class."""

    def test_parse_simple_hand(self):
        """Test parsing a simple hand notation."""
        parser = MahjongParser()
        tiles = parser.parse_tiles("123m")

        assert len(tiles) == 3
        assert tiles[0].notation == "1m"
        assert tiles[1].notation == "2m"
        assert tiles[2].notation == "3m"

    def test_parse_multiple_suits(self):
        """Test parsing notation with multiple suits."""
        tiles = parse_tiles("123m456p789s")

        assert len(tiles) == 9
        assert tiles[0].suit == "m"
        assert tiles[3].suit == "p"
        assert tiles[6].suit == "s"

    def test_parse_honors(self):
        """Test parsing honor tiles."""
        tiles = parse_tiles("1234567z")

        assert len(tiles) == 7
        assert tiles[0].display_name == "East"
        assert tiles[3].display_name == "North"
        assert tiles[4].display_name == "White Dragon"
        assert tiles[6].display_name == "Red Dragon"

    def test_parse_red_dora(self):
        """Test parsing red dora tiles."""
        tiles = parse_tiles("0m0p0s")

        assert len(tiles) == 3
        assert all(t.number == 0 for t in tiles)
        assert tiles[0].display_name == "Red 5 Man"
        assert tiles[1].display_name == "Red 5 Pin"
        assert tiles[2].display_name == "Red 5 Sou"

    def test_parse_full_hand(self):
        """Test parsing a complete hand."""
        # 123m456p789s11222z = 3+3+3+5 = 14 tiles
        hand = parse_hand("123m456p789s11222z")

        assert len(hand.closed_tiles) == 14
        # Check composition
        man_tiles = [t for t in hand.closed_tiles if t.suit == "m"]
        pin_tiles = [t for t in hand.closed_tiles if t.suit == "p"]
        sou_tiles = [t for t in hand.closed_tiles if t.suit == "s"]
        honor_tiles = [t for t in hand.closed_tiles if t.suit == "z"]

        assert len(man_tiles) == 3
        assert len(pin_tiles) == 3
        assert len(sou_tiles) == 3
        assert len(honor_tiles) == 5

    def test_parse_with_spaces(self):
        """Test parsing notation with spaces."""
        tiles = parse_tiles("123m 456p 789s")
        assert len(tiles) == 9

    def test_parse_with_separators(self):
        """Test parsing notation with underscore separators."""
        tiles = parse_tiles("123m_456p_789s")
        assert len(tiles) == 9

    def test_parse_chi_meld(self):
        """Test parsing chi (sequence) meld."""
        hand = parse_hand("123m (456p<)")

        assert len(hand.closed_tiles) == 3
        assert len(hand.melds) == 1
        meld = hand.melds[0]
        assert meld.meld_type == MeldType.CHI
        assert meld.source == MeldSource.LEFT
        assert len(meld.tiles) == 3

    def test_parse_pon_meld(self):
        """Test parsing pon (triplet) meld."""
        hand = parse_hand("123m (111p^)")

        assert len(hand.melds) == 1
        meld = hand.melds[0]
        assert meld.meld_type == MeldType.PON
        assert meld.source == MeldSource.ACROSS

    def test_parse_closed_kan(self):
        """Test parsing closed kan."""
        hand = parse_hand("123m [1111z]")

        assert len(hand.melds) == 1
        meld = hand.melds[0]
        assert meld.meld_type == MeldType.KAN_CLOSED
        assert not meld.is_open
        assert len(meld.tiles) == 4

    def test_parse_open_kan(self):
        """Test parsing open kan."""
        hand = parse_hand("123m (1111z>)")

        assert len(hand.melds) == 1
        meld = hand.melds[0]
        assert meld.meld_type == MeldType.KAN_OPEN
        assert meld.is_open
        assert meld.source == MeldSource.RIGHT

    def test_parse_added_kan_left(self):
        """Test parsing added kan from player to the left."""
        hand = parse_hand("123m (111+1z<)")

        assert len(hand.melds) == 1
        meld = hand.melds[0]
        assert meld.meld_type == MeldType.KAN_ADDED
        assert meld.is_open
        assert meld.source == MeldSource.LEFT
        assert len(meld.tiles) == 4
        # Left source: rotated tile at index 0
        assert meld.tiles[0].is_rotated is True
        assert meld.tiles[1].is_rotated is False
        assert meld.tiles[2].is_rotated is False
        # Added tile (last) is both rotated and marked as added
        assert meld.tiles[3].is_rotated is True
        assert meld.tiles[3].is_added is True

    def test_parse_added_kan_across(self):
        """Test parsing added kan from player across."""
        hand = parse_hand("123m (555+5p^)")

        meld = hand.melds[0]
        assert meld.meld_type == MeldType.KAN_ADDED
        assert meld.source == MeldSource.ACROSS
        # Across source: rotated tile at index 1
        assert meld.tiles[0].is_rotated is False
        assert meld.tiles[1].is_rotated is True
        assert meld.tiles[2].is_rotated is False
        assert meld.tiles[3].is_rotated is True
        assert meld.tiles[3].is_added is True

    def test_parse_added_kan_right(self):
        """Test parsing added kan from player to the right."""
        hand = parse_hand("123m (999+9s>)")

        meld = hand.melds[0]
        assert meld.meld_type == MeldType.KAN_ADDED
        assert meld.source == MeldSource.RIGHT
        # Right source: rotated tile at index 2
        assert meld.tiles[0].is_rotated is False
        assert meld.tiles[1].is_rotated is False
        assert meld.tiles[2].is_rotated is True
        assert meld.tiles[3].is_rotated is True
        assert meld.tiles[3].is_added is True

    def test_parse_multiple_melds(self):
        """Test parsing hand with multiple melds."""
        hand = parse_hand("11z (123m<) (555p^) [7777z]")

        assert len(hand.closed_tiles) == 2
        assert len(hand.melds) == 3

    def test_invalid_honor_number(self):
        """Test that invalid honor tile numbers raise error."""
        parser = MahjongParser()
        with pytest.raises(ParseError):
            parser.parse("8z")

    def test_is_sequence_detection(self):
        """Test sequence detection for chi vs pon."""
        parser = MahjongParser()

        # Should be chi
        hand = parser.parse("123m (234p<)")
        assert hand.melds[0].meld_type == MeldType.CHI

        # Should be pon
        hand = parser.parse("123m (222p<)")
        assert hand.melds[0].meld_type == MeldType.PON


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_parse_hand_function(self):
        """Test the parse_hand convenience function."""
        # 123m456p789s11222z = 3+3+3+5 = 14 tiles
        hand = parse_hand("123m456p789s11222z")
        assert len(hand.closed_tiles) == 14

    def test_parse_tiles_function(self):
        """Test the parse_tiles convenience function."""
        tiles = parse_tiles("123m456p")
        assert len(tiles) == 6


class TestHandProperties:
    """Tests for Hand object properties."""

    def test_hand_properties(self):
        """Test Hand helper properties."""
        hand = parse_hand("123m456p11z (789s<) [1111z]")
        assert hand.meld_count == 2
        # closed: 8, chi: 3, kan: 4 = 15 total tiles
        assert hand.total_tile_count == 15

    def test_hand_with_draw_tile(self):
        """Test Hand with explicit draw tile."""
        hand = parse_hand("123m456p789s1112z")  # 13 closed tiles
        hand.draw_tile = Tile(suit="z", number=2)
        assert hand.meld_count == 0
        # closed: 13, draw: 1 = 14 total tiles
        assert hand.total_tile_count == 14
        assert hand.draw_tile.notation == "2z"

    def test_hand_all_tiles_includes_draw(self):
        """Test that all_tiles includes the draw tile."""
        hand = parse_hand("123m456p789s1112z")  # 13 closed tiles
        hand.draw_tile = Tile(suit="z", number=2)
        all_tiles = hand.all_tiles
        assert len(all_tiles) == 14
        assert all_tiles[-1].notation == "2z"
