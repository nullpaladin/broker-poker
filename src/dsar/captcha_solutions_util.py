"""CAPTCHA helpers kept out of SuperScraper: the text/math solver and the image-CAPTCHA stub."""

import re
import time

_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19,
}
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
# "zero".."nineteen", plus "twenty".."ninety" optionally followed by "-"/space + a unit 1-9
# (longest alternatives first so "twenty-one" wins over "twenty").
_WORD_NUMBER = (
    r"(?:(?:" + "|".join(_TENS) + r")(?:[\s-]+(?:one|two|three|four|five|six|seven|eight|nine))?"
    r"|" + "|".join(sorted(_UNITS, key=len, reverse=True)) + r")"
)
_NUM = rf"-?\d+|{_WORD_NUMBER}"

_OPS = {
    "+": "add", "plus": "add", "add": "add", "sum": "add",
    "-": "sub", "minus": "sub", "subtract": "sub", "less": "sub",
    "*": "mul", "x": "mul", "×": "mul", "times": "mul",
    "multiplied by": "mul", "multiply": "mul",
    "/": "div", "÷": "div", "divided by": "div", "divide": "div", "over": "div",
}
_OP_ALT = "|".join(re.escape(k) for k in sorted(_OPS, key=len, reverse=True))


def parse_number(token: str):
    """``"7"`` / ``"seven"`` / ``"twenty-one"`` / ``"ninety nine"`` -> int (0-99 by word), else None."""
    token = token.strip().lower()
    if token.lstrip("-").isdigit():
        return int(token)
    parts = [p for p in re.split(r"[\s-]+", token) if p]
    if len(parts) == 1:
        return _UNITS.get(parts[0], _TENS.get(parts[0]))
    if len(parts) == 2 and parts[0] in _TENS and parts[1] in _UNITS and 1 <= _UNITS[parts[1]] <= 9:
        return _TENS[parts[0]] + _UNITS[parts[1]]
    return None


def solve_math_captcha(question: str):
    """Parse "<a> <op> <b>" (digits or words zero..ninety-nine; op = add/sub/mul/div,
    symbol or word) and return the integer answer as a string, or None."""
    if not question:
        return None
    text = question.strip().lower().rstrip("=?").strip()
    m = re.search(rf"({_NUM})\s*({_OP_ALT})\s*({_NUM})", text)
    if not m:
        return None
    a, b = parse_number(m.group(1)), parse_number(m.group(3))
    if a is None or b is None:
        return None
    op = _OPS[m.group(2)]
    if op == "add":
        return str(a + b)
    if op == "sub":
        return str(a - b)
    if op == "mul":
        return str(a * b)
    if op == "div":
        if b == 0:
            return None
        return str(a // b if a % b == 0 else round(a / b))
    return None


async def solve_image_captcha(tab, image_xpath, input_field_xpath, *, oops="Oops!", sleep=0, timeout=10):
    """Placeholder for 2captcha integration (the former ``SuperScraper.solve_captcha``)."""
    captcha_image = await tab.find(xpath=image_xpath, timeout=timeout, raise_exc=False)
    if not captcha_image:
        print(f"{oops} The captcha image with xpath {image_xpath} was not found.")
        return
    # TODO: need to integrate 2captcha
    if sleep:
        time.sleep(sleep)
    captcha_input_field = await tab.find(xpath=input_field_xpath, timeout=timeout, raise_exc=False)
    if not captcha_input_field:
        print(f"{oops} The captcha input field with xpath {input_field_xpath} was not found.")
        return
    await captcha_input_field.click()
    await tab.keyboard.type_text("Here's the solved captcha!")
    print(f"Here's where I do the captcha stuff: {captcha_image}")
