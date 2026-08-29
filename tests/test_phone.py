import pytest

from app.phone import to_e164_fr


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("06 12 34 56 78", "+33612345678"),
        ("0612345678", "+33612345678"),
        ("06.12.34.56.78", "+33612345678"),
        ("+33612345678", "+33612345678"),
        ("+33 6 12 34 56 78", "+33612345678"),
        ("0033612345678", "+33612345678"),
        ("01 23 45 67 89", "+33123456789"),
    ],
)
def test_to_e164_fr_valid(raw, expected):
    assert to_e164_fr(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        None,
        "not a phone number",
        "0612345",
        "061234567890",
        "0012345678",
        "+1 212 555 0100",
    ],
)
def test_to_e164_fr_invalid(raw):
    assert to_e164_fr(raw) is None
