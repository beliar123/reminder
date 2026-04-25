from enum import StrEnum


class Category(StrEnum):
    birthday = "birthday"
    anniversary = "anniversary"
    meeting = "meeting"
    personal = "personal"


class Recurrence(StrEnum):
    one_time = "one_time"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    every_6_months = "every_6_months"
    yearly = "yearly"
    every_18_months = "every_18_months"
    every_2_years = "every_2_years"


CATEGORIES_WITH_HISTORY = {Category.birthday, Category.anniversary, Category.meeting, Category.personal}
CATEGORIES_YEARLY_ONLY = {Category.birthday, Category.anniversary}
