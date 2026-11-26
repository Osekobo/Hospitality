def normalize_phone(phone: str, style: str = "international") -> str:
    digits = "".join(character for character in str(phone) if character.isdigit())
    if len(digits) == 10 and digits.startswith("0"):
        digits = "254" + digits[1:]
    elif len(digits) == 9:
        digits = "254" + digits
    if not (len(digits) == 12 and digits.startswith("254")):
        return digits
    return digits if style == "msisdn" else "+" + digits
