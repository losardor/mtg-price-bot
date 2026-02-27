from price_checker import is_acceptable


class TestIsAcceptable:
    def test_nm_en_correct_foil_not_vacation(self, product_nm_en):
        assert is_acceptable(product_nm_en, want_foil=False) is True

    def test_sp_it_correct_foil_not_vacation(self, product_sp_it):
        assert is_acceptable(product_sp_it, want_foil=False) is True

    def test_played_condition_rejected(self, product_played):
        assert is_acceptable(product_played, want_foil=False) is False

    def test_german_language_rejected(self, product_german):
        assert is_acceptable(product_german, want_foil=False) is False

    def test_wrong_foil_status_rejected(self, product_nm_en):
        # product_nm_en is non-foil, asking for foil -> reject
        assert is_acceptable(product_nm_en, want_foil=True) is False

    def test_foil_product_when_want_foil(self, product_foil):
        assert is_acceptable(product_foil, want_foil=True) is True

    def test_foil_product_when_not_want_foil(self, product_foil):
        assert is_acceptable(product_foil, want_foil=False) is False

    def test_vacation_rejected(self, product_vacation):
        assert is_acceptable(product_vacation, want_foil=False) is False

    def test_all_wrong(self):
        """Played, German, wrong foil, on vacation."""
        product = {
            "properties_hash": {
                "condition": "Played",
                "mtg_language": "de",
                "mtg_foil": True,
            },
            "on_vacation": True,
        }
        assert is_acceptable(product, want_foil=False) is False

    def test_only_condition_wrong(self):
        product = {
            "properties_hash": {
                "condition": "Heavily Played",
                "mtg_language": "en",
                "mtg_foil": False,
            },
            "on_vacation": False,
        }
        assert is_acceptable(product, want_foil=False) is False

    def test_only_language_wrong(self):
        product = {
            "properties_hash": {
                "condition": "Near Mint",
                "mtg_language": "ja",
                "mtg_foil": False,
            },
            "on_vacation": False,
        }
        assert is_acceptable(product, want_foil=False) is False

    def test_only_foil_wrong(self):
        product = {
            "properties_hash": {
                "condition": "Near Mint",
                "mtg_language": "en",
                "mtg_foil": True,
            },
            "on_vacation": False,
        }
        assert is_acceptable(product, want_foil=False) is False

    def test_only_vacation_wrong(self):
        product = {
            "properties_hash": {
                "condition": "Near Mint",
                "mtg_language": "en",
                "mtg_foil": False,
            },
            "on_vacation": True,
        }
        assert is_acceptable(product, want_foil=False) is False
