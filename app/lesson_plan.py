"""Builds the day's lesson from prepared content.

Mon-Fri (2 sittings, about 75 min):
  sitting 1: review (10) · new words (10) · listening (10)
  sitting 2: speaking (15, coming soon) · writing OR reading (20, alternating days) · real-life task (5)
Saturday: review + mini-test of the week's words + one letter
Sunday:   rest day (review is optional)

The plan is built once per day and stored, so it stays the same all day.
"""
from datetime import date, timedelta

NEW_WORDS_PER_DAY = 5
SATURDAY, SUNDAY = 5, 6
WEEKLY_TEST_MAX_WORDS = 15


def _block(key, kind, sitting, minutes, **extra):
    return {"key": key, "type": kind, "sitting": sitting, "minutes": minutes, **extra}


def topic_order(content) -> list[str]:
    return [t["id"] for t in content.get("topics", [])]


def next_new_words(content, introduced: set, limit: int = NEW_WORDS_PER_DAY) -> list[str]:
    """Next words not yet learned, in topic order, never mixing two topics in one day."""
    order = {t: i for i, t in enumerate(topic_order(content))}
    words = [w for w in content.get("words", []) if w["id"] not in introduced]
    words.sort(key=lambda w: order.get(w["topic"], len(order)))  # stable: keeps file order
    if not words:
        return []
    topic = words[0]["topic"]
    return [w["id"] for w in words if w["topic"] == topic][:limit]


def pick_item(items, used: dict, topic: str | None = None) -> str | None:
    """Next unused item, preferring today's topic. When all are used, repeat the oldest one."""
    if not items:
        return None
    unused = [i for i in items if i["id"] not in used]
    if unused:
        same = [i for i in unused if i.get("topic") == topic]
        return (same or unused)[0]["id"]
    return min(items, key=lambda i: (used[i["id"]], i["id"]))["id"]


def writing_day(day: date) -> bool:
    """Writing and reading alternate. Fri->Mon is 3 days, so weekdays always alternate."""
    return day.toordinal() % 2 == 0


def build_day_plan(day: date, content, introduced: set, used: dict, due_count: int,
                   week_words=()) -> dict:
    """
    introduced: word ids Saba has already learned
    used:       {content_id: 'YYYY-MM-DD' last used}
    due_count:  number of flashcards due for review today
    week_words: word ids introduced in the last 7 days (for Saturday's test)
    """
    wd = day.weekday()
    review = _block("review", "review", 1, 10)

    if wd == SUNDAY:
        blocks = [dict(review, optional=True)] if due_count else []
        return {"day": day.isoformat(), "kind": "rest", "blocks": blocks}

    if wd == SATURDAY:
        blocks = []
        if due_count:
            blocks.append(review)
        if week_words:
            blocks.append(_block("weekly_test", "weekly_test", 1, 10,
                                 word_ids=list(week_words)[:WEEKLY_TEST_MAX_WORDS]))
        letter = pick_item(content.get("letters", []), used)
        if letter:
            blocks.append(_block("writing", "writing", 1, 10, item_id=letter))
        return {"day": day.isoformat(), "kind": "weekly_test", "blocks": blocks}

    blocks = []
    if due_count:
        blocks.append(review)
    new = next_new_words(content, introduced)
    topic = None
    if new:
        topic = next(w["topic"] for w in content["words"] if w["id"] == new[0])
        blocks.append(_block("new_words", "new_words", 1, 10, word_ids=new, topic=topic))
    listening = pick_item(content.get("listening", []), used, topic)
    if listening:
        blocks.append(_block("listening", "listening", 1, 10, item_id=listening))

    blocks.append(_block("speaking", "speaking", 2, 15, coming_soon=True))
    if writing_day(day):
        item = pick_item(content.get("letters", []), used, topic)
        if item:
            blocks.append(_block("writing", "writing", 2, 20, item_id=item))
    else:
        item = pick_item(content.get("reading", []), used, topic)
        if item:
            blocks.append(_block("reading", "reading", 2, 20, item_id=item))
    task = pick_item(content.get("tasks", []), used, topic)
    if task:
        blocks.append(_block("task", "task", 2, 5, item_id=task))
    return {"day": day.isoformat(), "kind": "lesson", "topic": topic, "blocks": blocks}


def words_of_last_week(cards_introduced: dict, day: date) -> list[str]:
    """cards_introduced: {word_id: date introduced}. Words from the 6 days before `day`."""
    start = day - timedelta(days=6)
    return [w for w, d in sorted(cards_introduced.items(), key=lambda x: (x[1], x[0]))
            if start <= d < day]
