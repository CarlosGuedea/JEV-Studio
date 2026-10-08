"""Minimal, dependency-free cron matcher for five-field UTC schedules.

Supported field syntax: ``*``, ``*/n``, numbers, comma lists, ranges, and
ranged steps (for example ``1-10/2``). Expressions use:
minute hour day-of-month month day-of-week (Sunday is 0).
"""
from datetime import datetime

_RANGES = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 6))


def validate_cron_expression(expression: str) -> str:
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError("Cron must have five fields: minute hour day month weekday")
    for field, (minimum, maximum) in zip(fields, _RANGES):
        _expand_field(field, minimum, maximum)
    return " ".join(fields)


def matches_cron(expression: str, moment: datetime) -> bool:
    fields = validate_cron_expression(expression).split()
    minute, hour, day, month, weekday = (
        moment.minute,
        moment.hour,
        moment.day,
        moment.month,
        (moment.weekday() + 1) % 7,  # Python Monday=0; cron Sunday=0.
    )
    values = (minute, hour, day, month, weekday)
    allowed = [_expand_field(field, low, high) for field, (low, high) in zip(fields, _RANGES)]
    if not all(value in field_values for value, field_values in zip(values[:4], allowed[:4])):
        return False

    # Cron's historical convention: if day-of-month and day-of-week are both
    # restricted, either one may match; otherwise the restricted one must match.
    dom_any, dow_any = fields[2] == "*", fields[4] == "*"
    dom_match, dow_match = day in allowed[2], weekday in allowed[4]
    return (dom_match and dow_match) if dom_any and dow_any else (dow_match if dom_any else dom_match if dow_any else dom_match or dow_match)


def _expand_field(field: str, minimum: int, maximum: int) -> set[int]:
    if not field:
        raise ValueError("Cron fields cannot be empty")
    values: set[int] = set()
    for item in field.split(","):
        base, separator, step_text = item.partition("/")
        if separator:
            if not step_text.isdigit() or int(step_text) <= 0:
                raise ValueError(f"Invalid cron step '{item}'")
            step = int(step_text)
        else:
            step = 1
        if base == "*":
            start, end = minimum, maximum
        elif "-" in base:
            start_text, end_text = base.split("-", 1)
            if not start_text.isdigit() or not end_text.isdigit():
                raise ValueError(f"Invalid cron range '{item}'")
            start, end = int(start_text), int(end_text)
        elif base.isdigit() and not separator:
            start = end = int(base)
        else:
            raise ValueError(f"Invalid cron value '{item}'")
        if start < minimum or end > maximum or start > end:
            raise ValueError(f"Cron value '{item}' must be between {minimum} and {maximum}")
        values.update(range(start, end + 1, step))
    return values
