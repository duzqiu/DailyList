"""倒数日的循环周期：有哪几档、以及「下一次是哪天」怎么算。

这些原先长在本地数据层里（那会儿倒数日还存在本地 SQLite，周期是表里的一列）。倒数日搬到
后端之后它们就跟表没关系了 —— 纯粹是算术，所以单独挪出来（那一层后来整个删掉了）。

后端只认其中 5 档，收发两端的映射见 api/member_countdowns.py；`next_occurrence` 用
`REPEAT_CYCLES` 判断一条倒数日是不是循环的。
"""

import calendar
from datetime import date, timedelta

DEFAULT_CYCLE = "不循环"
# 两个「跳着来」的周期：工作日只落在周一..周五，非工作日只落在周六 / 周日。
# 它们不是「隔几天一次」，所以由 `_keeps_weekday` 处理。
WORKDAY_CYCLE = "工作日"
WEEKEND_CYCLE = "非工作日"
SKIP_CYCLES = (WORKDAY_CYCLE, WEEKEND_CYCLE)
REPEAT_CYCLES = (
    DEFAULT_CYCLE,
    "每天",
    "三天",
    "一周",
    WORKDAY_CYCLE,
    WEEKEND_CYCLE,
    "一月",
    "三月",
    "六月",
    "一年",
)

_MONTH_STEPS = {"一月": 1, "三月": 3, "六月": 6, "一年": 12}
_DAY_STEPS = {"每天": 1, "三天": 3, "一周": 7}


def next_occurrence(start: date, cycle: str, on_or_after: date) -> date:
    """First date of `start`'s cycle series that is not before `on_or_after`.

    不循环 keeps its single date (even a past one), while 每天/一周/每年… walk
    forward from the anchor so a birthday stays a birthday every year. The step
    count is estimated first, then nudged, so an anchor decades old still
    resolves in a couple of iterations.
    """
    if cycle not in REPEAT_CYCLES or cycle == DEFAULT_CYCLE:
        return start
    if cycle in SKIP_CYCLES:
        # 工作日 / 非工作日：从这天起往后找第一个属于该周期的日子。
        day = max(start, on_or_after)
        while not _keeps_weekday(cycle, day):
            day += timedelta(days=1)
        return day
    if start >= on_or_after:
        return start
    day_step = _DAY_STEPS.get(cycle)
    if day_step:
        steps = (on_or_after - start).days // day_step
    else:
        months = _MONTH_STEPS.get(cycle, 1)
        steps = (
            (on_or_after.year - start.year) * 12
            + on_or_after.month
            - start.month
        ) // months
    steps = max(0, steps - 1)
    while _shift(start, cycle, steps) < on_or_after:
        steps += 1
    return _shift(start, cycle, steps)


def _keeps_weekday(cycle: str, day: date) -> bool:
    """工作日 keeps 周一..周五, 非工作日 keeps 周六 / 周日."""
    return day.weekday() < 5 if cycle == WORKDAY_CYCLE else day.weekday() >= 5


def _shift(start: date, repeat_cycle: str, steps: int) -> date:
    """The day `steps` cycles after `start`.

    Month steps count from `start` rather than from the previous occurrence, so
    a countdown on the 31st stays on the 31st (clamping only in short months)
    instead of drifting to the 28th for good.
    """
    day_step = _DAY_STEPS.get(repeat_cycle)
    if day_step:
        return start + timedelta(days=day_step * steps)
    months = _MONTH_STEPS.get(repeat_cycle, 0)
    if months == 0:
        return start
    month_index = start.month - 1 + months * steps
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(start.day, last_day))
