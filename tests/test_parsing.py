import pytest
from bot import parse_add_args, parse_check_args, parse_remove_args


# ---------------------------------------------------------------------------
# parse_add_args
# ---------------------------------------------------------------------------

class TestParseAddArgs:
    def test_simple_card(self):
        name, threshold, foil = parse_add_args("/add Ragavan, Nimble Pilferer 45")
        assert name == "Ragavan, Nimble Pilferer"
        assert threshold == 45.0
        assert foil is False

    def test_foil_card(self):
        name, threshold, foil = parse_add_args("/add Ragavan, Nimble Pilferer 120 foil")
        assert name == "Ragavan, Nimble Pilferer"
        assert threshold == 120.0
        assert foil is True

    def test_foil_case_insensitive(self):
        name, threshold, foil = parse_add_args("/add Lightning Bolt 5 FOIL")
        assert name == "Lightning Bolt"
        assert threshold == 5.0
        assert foil is True

    def test_decimal_threshold(self):
        name, threshold, foil = parse_add_args("/add Sol Ring 2.50")
        assert name == "Sol Ring"
        assert threshold == 2.50
        assert foil is False

    def test_card_name_with_commas(self):
        name, threshold, foil = parse_add_args("/add Jace, the Mind Sculptor 30")
        assert name == "Jace, the Mind Sculptor"
        assert threshold == 30.0

    def test_card_name_with_special_chars(self):
        name, threshold, foil = parse_add_args("/add Uro, Titan of Nature's Wrath 15")
        assert name == "Uro, Titan of Nature's Wrath"
        assert threshold == 15.0

    def test_without_command_prefix(self):
        name, threshold, foil = parse_add_args("Lightning Bolt 5")
        assert name == "Lightning Bolt"
        assert threshold == 5.0

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            parse_add_args("")

    def test_only_command_raises(self):
        with pytest.raises(ValueError):
            parse_add_args("/add")

    def test_missing_threshold_raises(self):
        with pytest.raises(ValueError):
            parse_add_args("/add Lightning Bolt")

    def test_only_foil_no_threshold_raises(self):
        with pytest.raises(ValueError):
            parse_add_args("/add Lightning Bolt foil")


# ---------------------------------------------------------------------------
# parse_check_args
# ---------------------------------------------------------------------------

class TestParseCheckArgs:
    def test_no_args_returns_none(self):
        assert parse_check_args("/check") is None

    def test_no_args_with_space_returns_none(self):
        assert parse_check_args("/check  ") is None

    def test_with_card_name(self):
        assert parse_check_args("/check Lightning Bolt") == "Lightning Bolt"

    def test_without_command_prefix(self):
        assert parse_check_args("Lightning Bolt") == "Lightning Bolt"

    def test_empty_string_returns_none(self):
        assert parse_check_args("") is None


# ---------------------------------------------------------------------------
# parse_remove_args
# ---------------------------------------------------------------------------

class TestParseRemoveArgs:
    def test_simple_remove(self):
        name, foil = parse_remove_args("/remove The One Ring")
        assert name == "The One Ring"
        assert foil is False

    def test_remove_foil(self):
        name, foil = parse_remove_args("/remove The One Ring foil")
        assert name == "The One Ring"
        assert foil is True

    def test_remove_foil_case_insensitive(self):
        name, foil = parse_remove_args("/remove Lightning Bolt Foil")
        assert name == "Lightning Bolt"
        assert foil is True

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_remove_args("")

    def test_only_command_raises(self):
        with pytest.raises(ValueError):
            parse_remove_args("/remove")

    def test_only_foil_raises(self):
        with pytest.raises(ValueError):
            parse_remove_args("/remove foil")
