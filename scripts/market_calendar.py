"""Conservative regular NYSE closures for chart gaps, not a model calendar.

Unknown/special closures remain gaps unless explicitly reviewed. An observed
benchmark session always takes precedence over this regular-holiday classifier.
Reference: https://www.nyse.com/trade/hours-calendars
"""
from datetime import date, timedelta


def easter(year):
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def regular_closure(day):
    if day.weekday() >= 5:
        return True
    year = day.year
    def observed(month, number):
        value = date(year, month, number)
        return value + timedelta(days=-1 if value.weekday() == 5 else 1 if value.weekday() == 6 else 0)
    def nth(month, weekday, n):
        first = date(year, month, 1)
        return first + timedelta(days=(weekday-first.weekday()) % 7 + 7*(n-1))
    may_end = date(year, 5, 31)
    holidays = {nth(2,0,3), easter(year)-timedelta(days=2), may_end-timedelta(days=may_end.weekday()),
                observed(7,4), nth(9,0,1), nth(11,3,4), observed(12,25)}
    # NYSE does not close on the preceding Friday for a Saturday New Year's Day.
    new_year = date(year,1,1)
    if new_year.weekday() != 5:
        holidays.add(new_year + timedelta(days=1 if new_year.weekday() == 6 else 0))
    if year >= 1998:
        holidays.add(nth(1,0,3))
    if year >= 2022:
        holidays.add(observed(6,19))
    return day in holidays
