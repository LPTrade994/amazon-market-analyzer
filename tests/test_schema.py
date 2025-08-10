import pandas as pd
from schema import (
    parse_eu_price,
    parse_percent,
    parse_bool,
    validate_and_standardize,
)


def test_parse_eu_price():
    assert parse_eu_price("1.000,00 €") == 1000.0


def test_parse_percent():
    assert parse_percent("7,00 %") == 7.0


def test_parse_bool_yes_no():
    assert parse_bool("yes") is True
    assert parse_bool("no") is False


def test_validate_and_standardize_emoji_header():
    df = pd.DataFrame({"Buy Box 🚚 : current": ["1.000,00 €"]})
    out = validate_and_standardize(df)
    assert "bb_now" in out.columns
    assert out.loc[0, "bb_now"] == 1000.0

