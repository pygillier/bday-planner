import re

_FR_MOBILE_LOCAL = re.compile(r"^0[1-9]\d{8}$")


def to_e164_fr(raw):
    """Normalize a French phone number to E.164 (+33XXXXXXXXX).

    Accepts local (0X XX XX XX XX), +33, or 0033 forms with arbitrary
    spaces/dots/dashes/parens as separators. Returns None if the input
    doesn't match a valid 10-digit French number.
    """
    if not raw:
        return None
    digits = re.sub(r"[^\d+]", "", raw)

    if digits.startswith("+33"):
        digits = "0" + digits[3:]
    elif digits.startswith("0033"):
        digits = "0" + digits[4:]

    if not _FR_MOBILE_LOCAL.match(digits):
        return None

    return "+33" + digits[1:]
