from datetime import date, timedelta

from app.streak import current_streak, is_active_day

MON = date(2026, 11, 9)


def days(*offsets):
    return {MON + timedelta(days=o) for o in offsets}


def test_empty():
    assert current_streak(set(), MON) == 0


def test_active_rule():
    assert is_active_day(600, 0)
    assert is_active_day(0, 1)
    assert not is_active_day(599, 0)


def test_simple_run_and_today_in_progress():
    active = days(0, 1, 2)          # Mon-Wed
    assert current_streak(active, MON + timedelta(days=2)) == 3
    assert current_streak(active, MON + timedelta(days=3)) == 3  # Thu not done yet


def test_sunday_never_breaks():
    active = days(0, 1, 2, 3, 4, 5, 7)   # Mon-Sat, skip Sun, Mon
    assert current_streak(active, MON + timedelta(days=7)) == 7


def test_one_missed_weekday_per_week_is_forgiven():
    active = days(0, 1, 3, 4)            # missed Wed
    assert current_streak(active, MON + timedelta(days=4)) == 4


def test_two_missed_weekdays_in_a_week_break():
    active = days(0, 3, 4)               # missed Tue + Wed
    assert current_streak(active, MON + timedelta(days=4)) == 2


def test_missing_yesterday_and_today_uses_freeze_then_counts():
    active = days(0, 1)                  # Mon, Tue; today Thu, Wed missed
    assert current_streak(active, MON + timedelta(days=3)) == 2


def test_long_gap_breaks():
    active = days(0, 1, 2, 10, 11)
    assert current_streak(active, MON + timedelta(days=11)) == 2
