"""
Writes an amount in words, the way it is printed on a check:
    1234.56 -> "One thousand two hundred thirty-four and 56/100"
"""

from decimal import Decimal

ONES = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
SCALES = [(1_000_000_000, "billion"), (1_000_000, "million"), (1_000, "thousand")]


def under_one_thousand(number: int) -> str:
    words = []
    if number >= 100:
        words.append(ONES[number // 100] + " hundred")
        number = number % 100
    if number >= 20:
        tens_word = TENS[number // 10]
        if number % 10:
            tens_word = tens_word + "-" + ONES[number % 10]
        words.append(tens_word)
    elif number > 0:
        words.append(ONES[number])
    return " ".join(words)


def whole_number_in_words(number: int) -> str:
    if number == 0:
        return "zero"
    words = []
    for scale_value, scale_name in SCALES:
        if number >= scale_value:
            words.append(under_one_thousand(number // scale_value) + " " + scale_name)
            number = number % scale_value
    if number > 0:
        words.append(under_one_thousand(number))
    return " ".join(words)


def amount_in_words(amount: Decimal) -> str:
    amount = Decimal(amount).quantize(Decimal("0.01"))
    dollars = int(amount)
    cents = int((amount - dollars) * 100)
    text = whole_number_in_words(dollars) + f" and {cents:02d}/100"
    return text[0].upper() + text[1:]
