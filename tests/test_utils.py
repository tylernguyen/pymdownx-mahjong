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
        content = "hand: 123m\ntitle: Complete Hand\ndora: 5m\ndraw: 1z"
        notation, options = parse_block_content(content)

        assert notation == "123m"
        assert options["title"] == "Complete Hand"
        assert options["dora"] == "5m"
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
        errors = apply_hand_options(hand, parser, {"dora": "5m3p", "draw": "1z"})

        assert errors == []
        assert len(hand.dora_indicators) == 2
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


class TestDiscardsOption:
    def test_discards_with_hand(self):
        hand, options, notation = parse_hand_block("discards: 19m r4z\nhand: 123m", MahjongParser())

        assert notation == "123m"
        assert options["discards"] == "19m r4z"
        assert [t.notation for t in hand.discards] == ["1m", "9m", "4z"]
        assert hand.discards[2].is_rotated

    def test_discards_only(self):
        hand, _, notation = parse_hand_block("discards: 19m4z", MahjongParser())

        assert notation == ""
        assert hand.closed_tiles == []
        assert len(hand.discards) == 3

    def test_no_hand_or_discards(self):
        with pytest.raises(ParseError, match="No hand notation provided"):
            parse_hand_block("dora: 1m", MahjongParser())

    def test_invalid_discards(self):
        with pytest.raises(ParseError, match="Invalid discards notation"):
            parse_hand_block("discards: 1x", MahjongParser())

    def test_combined_tile_count(self):
        with pytest.raises(ParseError, match="1z appears 5 times"):
            parse_hand_block("hand: 111z\ndiscards: 1z1z", MahjongParser())


class TestSticksOptions:
    def test_honba_and_riichi(self):
        hand, _, _ = parse_hand_block("123m\nhonba: 3\nriichi: 1", MahjongParser())

        assert hand.honba == 3
        assert hand.riichi == 1

    def test_defaults_to_zero(self):
        hand, _, _ = parse_hand_block("123m", MahjongParser())

        assert hand.honba == 0
        assert hand.riichi == 0

    @pytest.mark.parametrize("value", ["x", "-1", "1.5", "", "²"])
    def test_invalid_value(self, value):
        errors = apply_hand_options(Hand(), MahjongParser(), {"honba": value})

        assert errors == [f"Invalid honba value: expected a non-negative integer, got {value!r}"]

    @pytest.mark.parametrize(("value", "wind"), [("east", "east"), ("S", "south"), ("West", "west"), ("n", "north")])
    def test_seat(self, value, wind):
        hand, _, _ = parse_hand_block(f"123m\nseat: {value}", MahjongParser())

        assert hand.seat_wind == wind

    @pytest.mark.parametrize("value", ["", "1z", "eastt", "x"])
    def test_invalid_seat_reports_error(self, value):
        errors = apply_hand_options(Hand(), MahjongParser(), {"seat": value})

        assert len(errors) == 1
        assert "Invalid seat value" in errors[0]

    @pytest.mark.parametrize(("value", "score"), [("25000", 25000), ("0", 0), ("-1200", -1200)])
    def test_score(self, value, score):
        hand, _, _ = parse_hand_block(f"123m\nscore: {value}", MahjongParser())

        assert hand.score == score

    @pytest.mark.parametrize("value", ["", "-", "25,000", "1.5", "+100", "２５"])
    def test_invalid_score_reports_error(self, value):
        errors = apply_hand_options(Hand(), MahjongParser(), {"score": value})

        assert errors == [f"Invalid score value: expected an integer, got {value!r}"]

    def test_seat_and_score_default_unset(self):
        hand, _, _ = parse_hand_block("123m", MahjongParser())

        assert hand.seat_wind is None
        assert hand.score is None

    def test_sticks_alone_need_a_hand(self):
        with pytest.raises(ParseError, match="No hand notation provided"):
            parse_hand_block("riichi: 1", MahjongParser())


class TestDoraLimit:
    def test_five_dora_allowed(self):
        hand, _, _ = parse_hand_block("123m\ndora: 12345z", MahjongParser())

        assert len(hand.dora_indicators) == 5

    def test_more_than_five_dora_rejected(self):
        errors = apply_hand_options(Hand(), MahjongParser(), {"dora": "123456z"})

        assert errors == ["Invalid dora notation: expected at most 5 tiles, got 6"]

    def test_block_with_too_many_dora_raises(self):
        with pytest.raises(ParseError, match="expected at most 5 tiles, got 6"):
            parse_hand_block("123m\ndora: 123456z", MahjongParser())


class TestRemovedOptions:
    @pytest.mark.parametrize("option", ["ura: 3p", "waits: 52z"])
    def test_removed_option_rejected(self, option):
        key = option.split(":")[0]
        with pytest.raises(ParseError, match=f"Unknown option '{key}'"):
            parse_hand_block(f"123m\n{option}", MahjongParser())


class TestBoardOptions:
    def test_player_keys_parsed(self):
        _, options = parse_block_content("123m\nshimo.hand: 456p\nKami.Score: 27600")

        assert options == {"shimo.hand": "456p", "kami.score": "27600"}

    def test_unknown_player_rejected(self):
        with pytest.raises(ParseError, match=r"Unknown player 'right' in 'right\.hand'"):
            parse_block_content("123m\nright.hand: 13")

    def test_unknown_player_key_rejected(self):
        with pytest.raises(ParseError, match=r"Unknown option 'shimo.dora' \(expected one of: hand, draw, discards"):
            parse_block_content("123m\nshimo.dora: 3m")

    def test_opponents_built_in_turn_order(self):
        block = "123m\nkami.hand: 456p\nshimo.hand:\ntoimen.discards: 1z"
        hand, _, _ = parse_hand_block(block, MahjongParser())

        assert list(hand.opponents) == ["shimo", "toimen", "kami"]
        assert len(hand.opponents["shimo"].closed_tiles) == 13
        assert [t.notation for t in hand.opponents["toimen"].discards] == ["1z"]

    @staticmethod
    def _shimo(notation):
        hand, _, _ = parse_hand_block(f"123m\nshimo.hand: {notation}", MahjongParser())
        shimo = hand.opponents["shimo"]
        return sum(t.is_back for t in shimo.closed_tiles), [t.notation for t in shimo.closed_tiles if not t.is_back]

    def test_empty_hand_is_13_hidden(self):
        assert self._shimo("") == (13, [])

    def test_unknown_is_not_a_keyword(self):
        with pytest.raises(ParseError, match="shimo: Invalid tile notation"):
            parse_hand_block("123m\nshimo.hand: unknown", MahjongParser())

    def test_hand_without_hand_option_is_13_hidden(self):
        hand, _, _ = parse_hand_block("123m\nkami.score: 25000", MahjongParser())

        assert len(hand.opponents["kami"].closed_tiles) == 13
        assert all(t.is_back for t in hand.opponents["kami"].closed_tiles)

    @pytest.mark.parametrize(
        ("notation", "hidden"),
        [("(777z<)", 10), ("(777z<) (123p<)", 7), ("(777z<) (123p<) [1111s]", 4)],
    )
    def test_melds_leave_the_rest_hidden(self, notation, hidden):
        assert self._shimo(notation) == (hidden, [])

    def test_revealed_tiles_follow_hidden_ones(self):
        assert self._shimo("123m (777z<)") == (7, ["1m", "2m", "3m"])

    def test_full_hand_not_padded(self):
        assert self._shimo("123m456p789s1122z") == (
            0,
            ["1m", "2m", "3m", "4p", "5p", "6p", "7s", "8s", "9s", "1z", "1z", "2z", "2z"],
        )

    @pytest.mark.parametrize("notation", ["10", "10 (777z<)", "13"])
    def test_bare_number_rejected(self, notation):
        with pytest.raises(ParseError, match=r"shimo: Invalid tile notation: 1[03] \(did you forget a suit\?\)"):
            self._shimo(notation)

    def test_opponents_only_block_is_valid(self):
        hand, _, _ = parse_hand_block("shimo.hand:", MahjongParser())

        assert hand.closed_tiles == []
        assert "shimo" in hand.opponents

    def test_seat_winds_follow_bottom_player(self):
        block = "123m\nseat: west\nshimo.hand:\ntoimen.hand:\nkami.hand:"
        hand, _, _ = parse_hand_block(block, MahjongParser())

        assert {seat: p.seat_wind for seat, p in hand.opponents.items()} == {
            "shimo": "north",
            "toimen": "east",
            "kami": "south",
        }

    def test_explicit_seat_overrides_inferred(self):
        block = "123m\nseat: east\nshimo.hand:\nshimo.seat: W\ntoimen.hand:"
        with pytest.raises(ParseError, match=r"west \(shimo, toimen\)"):
            parse_hand_block(block, MahjongParser())

    def test_no_seat_wind_without_bottom_seat(self):
        hand, _, _ = parse_hand_block("123m\nshimo.hand:", MahjongParser())

        assert hand.opponents["shimo"].seat_wind is None

    def test_duplicate_seat_wind_rejected(self):
        with pytest.raises(ParseError, match=r"Seat wind given to more than one player: east \(hand, kami\)"):
            parse_hand_block("123m\nseat: E\nkami.hand:\nkami.seat: east", MahjongParser())

    def test_opponent_errors_carry_prefix(self):
        block = "123m\nshimo.hand: 1x\ntoimen.hand:\ntoimen.score: lots"
        with pytest.raises(ParseError) as exc:
            parse_hand_block(block, MahjongParser())

        message = str(exc.value)
        assert message.startswith("shimo: Invalid tile notation")
        assert "toimen: Invalid score value: expected an integer, got 'lots'" in message

    def test_tile_count_checked_across_table(self):
        block = "1111m\nshimo.hand:\nshimo.discards: 1m"
        with pytest.raises(ParseError, match="1m appears 5 times"):
            parse_hand_block(block, MahjongParser())

    def test_dora_counted_on_a_board(self):
        block = "1111m\ndora: 1m\nshimo.hand:"
        with pytest.raises(ParseError, match="1m appears 5 times"):
            parse_hand_block(block, MahjongParser())


class TestRoundAndRemaining:
    @pytest.mark.parametrize(
        ("value", "wind", "number"),
        [("E1", "east", 1), ("S2", "south", 2), ("south 2", "south", 2), ("north4", "north", 4), ("w 3", "west", 3)],
    )
    def test_round_parsed(self, value, wind, number):
        hand = Hand()
        assert apply_hand_options(hand, MahjongParser(), {"round": value}) == []

        assert (hand.round_wind, hand.round_number) == (wind, number)

    @pytest.mark.parametrize("value", ["", "E", "E5", "E0", "2", "up 1", "東一"])
    def test_invalid_round_reports_error(self, value):
        errors = apply_hand_options(Hand(), MahjongParser(), {"round": value})

        assert errors == [f"Invalid round value: expected a wind and a number 1-4 (e.g. E1, south 2), got {value!r}"]

    @pytest.mark.parametrize("value", ["0", "35", "70"])
    def test_remaining_parsed(self, value):
        hand = Hand()
        assert apply_hand_options(hand, MahjongParser(), {"remaining": value}) == []

        assert hand.remaining == int(value)

    @pytest.mark.parametrize("value", ["71", "-1", "a lot", ""])
    def test_invalid_remaining_reports_error(self, value):
        errors = apply_hand_options(Hand(), MahjongParser(), {"remaining": value})

        assert errors == [f"Invalid remaining value: expected an integer from 0 to 70, got {value!r}"]


class TestHandLimits:
    def test_dora_counted_on_a_single_hand(self):
        with pytest.raises(ParseError, match="1m appears 5 times"):
            parse_hand_block("1111m\ndora: 1m", MahjongParser())

    def test_dora_counted_on_a_single_hand_without_draw_or_discards(self):
        with pytest.raises(ParseError, match="5z appears 5 times"):
            parse_hand_block("555z\ndora: 55z", MahjongParser())

    def test_opponent_hand_over_13_rejected(self):
        with pytest.raises(ParseError, match="shimo: Hand has 16 tiles"):
            parse_hand_block("123m\nshimo.hand: 123456789m1234567z", MahjongParser())

    def test_opponent_with_five_melds_rejected(self):
        block = "123m\nshimo.hand: (111p<) (222p<) (333p<) (444p<) (555p<)"
        with pytest.raises(ParseError, match="shimo: Hand has 15 tiles"):
            parse_hand_block(block, MahjongParser())

    def test_opponent_full_hand_plus_draw_allowed(self):
        hand, _, _ = parse_hand_block("123m\nshimo.hand: 123456789m1122z\nshimo.draw: 3z", MahjongParser())

        assert len(hand.opponents["shimo"].closed_tiles) == 13
        assert hand.opponents["shimo"].draw_tile is not None

    def test_bare_number_rejected_on_own_hand(self):
        with pytest.raises(ParseError, match="did you forget a suit"):
            parse_hand_block("11", MahjongParser())

    def test_opponent_hidden_hand_with_draw_allowed(self):
        hand, _, _ = parse_hand_block("123m\nshimo.hand:\nshimo.draw: 1z", MahjongParser())

        assert len(hand.opponents["shimo"].closed_tiles) == 13
        assert hand.opponents["shimo"].draw_tile is not None

    def test_repeated_option_rejected(self):
        with pytest.raises(ParseError, match="Option 'score' given more than once: score: 2"):
            parse_hand_block("123m\nscore: 1\nscore: 2", MahjongParser())

    def test_repeated_player_option_rejected(self):
        with pytest.raises(ParseError, match=r"Option 'shimo\.hand' given more than once"):
            parse_hand_block("123m\nshimo.hand: 1m\nshimo.hand: 2m", MahjongParser())

    def test_called_discard_not_counted_twice(self):
        # Three 5z in the bottom player's pon (one called from kamicha) plus one in their
        # discards is all four 5z; kamicha's c5z is the same tile as the pon's called one.
        block = "123456789m11p (555z<)\ndiscards: 5z\nkami.discards: c5z"
        hand, _, _ = parse_hand_block(block, MahjongParser())

        assert hand.opponents["kami"].discards[0].is_called

    def test_uncalled_fifth_tile_still_rejected(self):
        with pytest.raises(ParseError, match="5z appears 5 times"):
            parse_hand_block("123456789m11p (555z<)\ndiscards: 5z\nkami.discards: 5z", MahjongParser())
