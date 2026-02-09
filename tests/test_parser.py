"""Tests for the MPSZ notation parser."""

import pytest

from pymdownx_mahjong.parser import (
    MahjongParser,
    MeldSource,
    MeldType,
    ParseError,
    Tile,
    parse_hand,
)


class TestTile:
    def test_tile_properties(self):
        tile = Tile(suit="m", number=1)
        assert tile.notation == "1m"
        assert tile.display_name == "1 Man"

    def test_tile_honor(self):
        tile = Tile(suit="z", number=1)
        assert tile.display_name == "East"

    def test_tile_red_dora(self):
        tile = Tile(suit="m", number=0)
        assert tile.display_name == "Red 5 Man"


class TestMahjongParser:
    def test_parse_multiple_suits(self):
        parser = MahjongParser()
        tiles = parser.parse_tiles("123m456p789s")

        assert len(tiles) == 9
        assert tiles[0].suit == "m"
        assert tiles[3].suit == "p"
        assert tiles[6].suit == "s"

    def test_parse_honors(self):
        parser = MahjongParser()
        tiles = parser.parse_tiles("1234567z")

        assert len(tiles) == 7
        assert tiles[0].display_name == "East"
        assert tiles[3].display_name == "North"
        assert tiles[6].display_name == "Red Dragon"

    def test_parse_red_dora(self):
        parser = MahjongParser()
        tiles = parser.parse_tiles("0m0p0s")

        assert len(tiles) == 3
        assert all(t.number == 0 for t in tiles)

    def test_parse_full_hand(self):
        hand = parse_hand("123m456p789s11222z")

        assert len(hand.closed_tiles) == 14
        suits = {t.suit for t in hand.closed_tiles}
        assert suits == {"m", "p", "s", "z"}

    def test_parse_with_separators(self):
        parser = MahjongParser()
        assert len(parser.parse_tiles("123m 456p_789s")) == 9

    def test_parse_chi_meld(self):
        hand = parse_hand("123m (456p<)")

        assert len(hand.closed_tiles) == 3
        assert len(hand.melds) == 1
        meld = hand.melds[0]
        assert meld.meld_type == MeldType.CHI
        assert meld.source == MeldSource.LEFT

    def test_parse_pon_meld(self):
        hand = parse_hand("123m (111p^)")

        meld = hand.melds[0]
        assert meld.meld_type == MeldType.PON
        assert meld.source == MeldSource.ACROSS

    def test_parse_closed_kan(self):
        hand = parse_hand("123m [1111z]")

        meld = hand.melds[0]
        assert meld.meld_type == MeldType.KAN_CLOSED
        assert not meld.is_open
        assert len(meld.tiles) == 4

    def test_closed_kan_with_source_rejected(self):
        with pytest.raises(ParseError):
            MahjongParser().parse("[1111z<]")

    def test_parse_open_kan(self):
        hand = parse_hand("123m (1111z>)")

        meld = hand.melds[0]
        assert meld.meld_type == MeldType.KAN_OPEN
        assert meld.is_open
        assert meld.source == MeldSource.RIGHT

    def test_parse_added_kan_left(self):
        hand = parse_hand("123m (111+1z<)")

        meld = hand.melds[0]
        assert meld.meld_type == MeldType.KAN_ADDED
        assert meld.source == MeldSource.LEFT
        assert meld.tiles[0].is_rotated is True
        assert meld.tiles[1].is_rotated is False
        assert meld.tiles[3].is_rotated is True
        assert meld.tiles[3].is_added is True

    def test_parse_added_kan_across(self):
        hand = parse_hand("123m (555+5p^)")

        meld = hand.melds[0]
        assert meld.meld_type == MeldType.KAN_ADDED
        assert meld.tiles[1].is_rotated is True
        assert meld.tiles[3].is_added is True

    def test_parse_added_kan_right(self):
        hand = parse_hand("123m (999+9s>)")

        meld = hand.melds[0]
        assert meld.meld_type == MeldType.KAN_ADDED
        assert meld.tiles[2].is_rotated is True
        assert meld.tiles[3].is_added is True

    def test_parse_multiple_melds(self):
        hand = parse_hand("11z (123m<) (555p^) [7777z]")

        assert len(hand.closed_tiles) == 2
        assert len(hand.melds) == 3

    def test_invalid_honor_number(self):
        with pytest.raises(ParseError):
            MahjongParser().parse("8z")

    def test_sequence_vs_triplet_detection(self):
        parser = MahjongParser()

        hand = parser.parse("123m (234p<)")
        assert hand.melds[0].meld_type == MeldType.CHI

        hand = parser.parse("123m (222p<)")
        assert hand.melds[0].meld_type == MeldType.PON


class TestHandProperties:
    def test_hand_properties(self):
        hand = parse_hand("123m456p11z (789s<) [2222z]")
        assert len(hand.melds) == 2
        assert hand.total_tile_count == 15

    def test_hand_with_draw_tile(self):
        hand = parse_hand("123m456p789s1112z")
        hand.draw_tile = Tile(suit="z", number=2)
        assert hand.total_tile_count == 14
        assert hand.all_tiles[-1].notation == "2z"


class TestTileCountValidation:
    def test_five_of_same_tile_raises_error(self):
        with pytest.raises(ParseError, match="1m appears 5 times"):
            MahjongParser().parse("11111m")

    def test_four_with_meld_total_five_raises_error(self):
        with pytest.raises(ParseError, match="1m appears 6 times"):
            MahjongParser().parse("111m (111m<)")

    def test_red_dora_counted_separately(self):
        # Red 5 (0) and regular 5 are different tile types
        hand = parse_hand("55550m")
        assert len(hand.closed_tiles) == 5

    def test_five_red_dora_raises_error(self):
        with pytest.raises(ParseError, match="0m appears 5 times"):
            MahjongParser().parse("00000m")

    def test_multiple_violations_reports_all(self):
        with pytest.raises(ParseError) as exc_info:
            MahjongParser().parse("11111m22222p")
        error_msg = str(exc_info.value)
        assert "1m appears 5 times" in error_msg
        assert "2p appears 5 times" in error_msg

    def test_valid_hand_with_kan(self):
        hand = parse_hand("123m456p [1111z]")
        assert len(hand.melds) == 1
