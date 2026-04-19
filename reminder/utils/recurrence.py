from datetime import datetime

from dateutil.relativedelta import relativedelta

from reminder.enums import Recurrence

_RECURRENCE_DELTA: dict[Recurrence, relativedelta] = {
    Recurrence.daily: relativedelta(days=1),
    Recurrence.weekly: relativedelta(weeks=1),
    Recurrence.monthly: relativedelta(months=1),
    Recurrence.every_6_months: relativedelta(months=6),
    Recurrence.yearly: relativedelta(years=1),
    Recurrence.every_18_months: relativedelta(months=18),
    Recurrence.every_2_years: relativedelta(years=2),
}


def next_remind_date(current: datetime, recurrence: Recurrence) -> datetime | None:
    """Return the next reminder datetime after advancing by the recurrence interval.

    Returns None for one_time events (no next occurrence).
    """
    if recurrence == Recurrence.one_time:
        return None
    return current + _RECURRENCE_DELTA[recurrence]
