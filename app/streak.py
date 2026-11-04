"""Daily streak.

- A day counts when Saba studied at least 10 minutes or finished one sitting.
- Sunday is a rest day: it never breaks the streak (it counts if she studies).
- One missed day Monday-Saturday per week is forgiven ("streak freeze").
- Today doesn't break the streak while it is still going on.
"""
from datetime import date, timedelta

MIN_SECONDS = 10 * 60
SUNDAY = 6


def is_active_day(seconds: int, sittings_done: int) -> bool:
    return seconds >= MIN_SECONDS or sittings_done >= 1


def current_streak(active_days, today: date) -> int:
    """Number of active days in the current unbroken run."""
    active = set(active_days)
    if not active:
        return 0
    first = min(active)
    streak = 0
    freeze_used_weeks = set()
    d = today
    if d not in active:
        d -= timedelta(days=1)  # today still in progress
    while d >= first:
        if d in active:
            streak += 1
        elif d.weekday() == SUNDAY:
            pass
        else:
            week = d.isocalendar()[:2]
            if week in freeze_used_weeks:
                break
            freeze_used_weeks.add(week)
        d -= timedelta(days=1)
    return streak
