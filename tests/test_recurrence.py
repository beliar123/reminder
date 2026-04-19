from datetime import datetime, timezone

import pytest

from reminder.enums import Recurrence
from reminder.utils.recurrence import next_remind_date


def dt(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, 12, 0, 0, tzinfo=timezone.utc)


def test_one_time_returns_none():
    assert next_remind_date(dt(2026, 1, 1), Recurrence.one_time) is None


def test_daily():
    result = next_remind_date(dt(2026, 1, 31), Recurrence.daily)
    assert result == dt(2026, 2, 1)


def test_weekly():
    result = next_remind_date(dt(2026, 4, 19), Recurrence.weekly)
    assert result == dt(2026, 4, 26)


def test_monthly():
    result = next_remind_date(dt(2026, 1, 31), Recurrence.monthly)
    assert result == dt(2026, 2, 28)  # dateutil truncates to end of month


def test_monthly_preserves_day():
    result = next_remind_date(dt(2026, 3, 15), Recurrence.monthly)
    assert result == dt(2026, 4, 15)


def test_every_6_months():
    result = next_remind_date(dt(2026, 1, 15), Recurrence.every_6_months)
    assert result == dt(2026, 7, 15)


def test_every_6_months_year_boundary():
    result = next_remind_date(dt(2026, 9, 1), Recurrence.every_6_months)
    assert result == dt(2027, 3, 1)


def test_yearly():
    result = next_remind_date(dt(2026, 2, 28), Recurrence.yearly)
    assert result == dt(2027, 2, 28)


def test_yearly_leap_day():
    result = next_remind_date(dt(2024, 2, 29), Recurrence.yearly)
    assert result == dt(2025, 2, 28)  # dateutil truncates non-leap year


def test_every_18_months():
    result = next_remind_date(dt(2026, 1, 1), Recurrence.every_18_months)
    assert result == dt(2027, 7, 1)


def test_every_2_years():
    result = next_remind_date(dt(2026, 4, 19), Recurrence.every_2_years)
    assert result == dt(2028, 4, 19)
