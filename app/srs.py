"""Spaced repetition — a simple Leitner box system.

Box 0..6. Each box has a waiting time in days. A right answer moves the card
up one box; a wrong answer sends it back to box 0 (due tomorrow) and marks it
'again', so it is first in tomorrow's review.

Only the FIRST answer of the day changes the schedule. If Saba gets a card
wrong, it comes back later in the same session to practise, but those extra
tries don't move it.
"""
from dataclasses import dataclass, replace
from datetime import date, timedelta

INTERVALS = [1, 2, 4, 7, 14, 30, 60]  # days to wait after leaving box i
MAX_BOX = len(INTERVALS) - 1
KNOWN_BOX = 3                          # box >= 3 counts as "a word I know"
DAILY_REVIEW_LIMIT = 25                # about 10 minutes


@dataclass(frozen=True)
class Card:
    word_id: str
    box: int
    due_date: date
    introduced_on: date
    reps: int = 0
    lapses: int = 0
    last_result: str | None = None     # 'good' | 'again'
    last_seen: date | None = None


def new_card(word_id: str, today: date) -> Card:
    """A word just learned in 'New words'. First review is tomorrow."""
    return Card(word_id=word_id, box=0, due_date=today + timedelta(days=1), introduced_on=today)


def review(card: Card, correct: bool, today: date) -> Card:
    """Apply one answer. Returns a new Card."""
    if card.last_seen == today:
        return card  # already scheduled today; practice tries don't count
    if correct:
        box = min(card.box + 1, MAX_BOX)
        return replace(card, box=box, due_date=today + timedelta(days=INTERVALS[box]),
                       reps=card.reps + 1, last_result="good", last_seen=today)
    return replace(card, box=0, due_date=today + timedelta(days=INTERVALS[0]),
                   reps=card.reps + 1, lapses=card.lapses + 1,
                   last_result="again", last_seen=today)


def review_queue(cards, today: date, limit: int = DAILY_REVIEW_LIMIT) -> list[Card]:
    """Cards to review today: mistakes first, then the most overdue, then lowest box."""
    due = [c for c in cards if c.due_date <= today and c.last_seen != today]
    due.sort(key=lambda c: (0 if c.last_result == "again" else 1, c.due_date, c.box, c.word_id))
    return due[:limit]


def words_known(cards) -> int:
    return sum(1 for c in cards if c.box >= KNOWN_BOX)
