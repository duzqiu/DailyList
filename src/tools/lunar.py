"""农历 (Chinese lunisolar calendar) conversion for the 倒数日 cards.

The 1900-2099 table below is generated from the macOS/ICU Chinese calendar (the
same data iOS shows in Calendar.app), because a Flutter app has no ICU to ask at
runtime and the lunisolar calendar is table-based - it cannot be computed from a
simple formula. Each entry packs one lunar year:

    bit 16      leap month has 30 days (1) or 29 (0)
    bits 15..4  month 1..12 has 30 days (1) or 29 (0), bit 15 = month 1
    bits 3..0   which month is the leap one, 0 = none

Dates before 1900-01-31 or after 2099 fall back to the plain solar date.
"""

from datetime import date

# 1900..2099, one entry per lunar year.
_YEARS = (
    0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0,
    0x09ad0, 0x055d2, 0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d295, 0x0b550,
    0x056a0, 0x0ada2, 0x095b0, 0x14977, 0x049b0, 0x0a4b0, 0x0b4b5, 0x06a50,
    0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970, 0x06566, 0x0d4a0,
    0x0ea50, 0x16a95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950,
    0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2,
    0x0a950, 0x0b557, 0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5b0, 0x14573,
    0x052b0, 0x0a9a8, 0x0e950, 0x06aa0, 0x0aea6, 0x0ab50, 0x04b60, 0x0aae4,
    0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0, 0x096d0, 0x04dd5,
    0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b6a0, 0x195a6,
    0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46,
    0x0ab60, 0x09570, 0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58,
    0x05ac0, 0x0ab60, 0x096d5, 0x092e0, 0x0c960, 0x0d954, 0x0d4a0, 0x0da50,
    0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5, 0x0a950, 0x0b4a0,
    0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930,
    0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260,
    0x0ea65, 0x0d530, 0x05aa0, 0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0,
    0x1d0b6, 0x0d250, 0x0d520, 0x0dd45, 0x0b5a0, 0x056d0, 0x055b2, 0x049b0,
    0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0, 0x14b63, 0x09370,
    0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06b20, 0x1a6c4, 0x0aae0,
    0x092e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0,
    0x0a6d0, 0x055d4, 0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50,
    0x055a0, 0x0aba4, 0x0a5b0, 0x052b0, 0x0b273, 0x06930, 0x07337, 0x06aa0,
    0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160, 0x0e968, 0x0d520,
    0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a4d0, 0x0d150, 0x0f252,
)

_BASE = date(1900, 1, 31)  # 1900 正月初一
_FIRST_YEAR = 1900

_MONTH_NAMES = ("正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊")
_DAY_NAMES = (
    "初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
    "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
    "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十",
)


def _info(year: int) -> int:
    return _YEARS[year - _FIRST_YEAR]


def _leap_month(year: int) -> int:
    return _info(year) & 0xF


def _leap_days(year: int) -> int:
    if not _leap_month(year):
        return 0
    return 30 if _info(year) & 0x10000 else 29


def _month_days(year: int, month: int) -> int:
    return 30 if _info(year) & (0x10000 >> month) else 29


def _year_days(year: int) -> int:
    total = 348
    mask = 0x8000
    while mask > 0x8:
        if _info(year) & mask:
            total += 1
        mask >>= 1
    return total + _leap_days(year)


def lunar_parts(day: date) -> "tuple[int, int, bool] | None":
    """(month, day, is_leap) of `day` in the lunar calendar, or None if unknown."""
    offset = (day - _BASE).days
    if offset < 0 or offset >= sum(_year_days(y) for y in range(1900, 2100)):
        return None
    year = _FIRST_YEAR
    while True:
        days = _year_days(year)
        if offset < days:
            break
        offset -= days
        year += 1
    leap = _leap_month(year)
    month = 1
    is_leap = False
    while month <= 12:
        if leap and month == leap + 1 and not is_leap:
            days = _leap_days(year)
            is_leap = True
            # the same index is reused for the month that follows the leap one
            month -= 1
        else:
            days = _month_days(year, month)
            if is_leap and month == leap + 1:
                is_leap = False
        if offset < days:
            break
        offset -= days
        month += 1
    return month, offset + 1, is_leap


def lunar_label(day: date) -> str:
    """「八月十六」- the lunar date, or an empty string outside the table."""
    parts = lunar_parts(day)
    if parts is None:
        return ""
    month, day_number, is_leap = parts
    prefix = "闰" if is_leap else ""
    return f"{prefix}{_MONTH_NAMES[month - 1]}月{_DAY_NAMES[day_number - 1]}"
