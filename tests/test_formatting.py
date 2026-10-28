from utils.formatting import GBP, format_currency, format_percent


def test_default_currency_is_pound():
    assert format_currency(1234.5) == "£1,234.50"


def test_other_symbol_still_possible():
    assert format_currency(1234.5, "$") == "$1,234.50"


def test_pound_symbol():
    assert format_currency(1234.5, GBP) == "£1,234.50"


def test_negative_puts_minus_first():
    assert format_currency(-5, GBP) == "-£5.00"


def test_tiny_negative_rounds_to_zero_without_minus():
    assert format_currency(-0.001, GBP) == "£0.00"


def test_percent():
    assert format_percent(12.3) == "12.30%"
