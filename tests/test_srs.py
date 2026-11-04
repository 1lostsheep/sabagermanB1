from datetime import date, timedelta

from app import srs

D = date(2026, 11, 9)  # a Monday


def test_new_card_due_tomorrow():
    c = srs.new_card("w-a", D)
    assert c.box == 0 and c.due_date == D + timedelta(days=1)


def test_correct_moves_up_one_box_with_growing_gaps():
    c = srs.new_card("w-a", D)
    day = D
    gaps = []
    for _ in range(4):
        day = c.due_date
        c = srs.review(c, True, day)
        gaps.append((c.due_date - day).days)
    assert c.box == 4
    assert gaps == [2, 4, 7, 14]


def test_box_is_capped():
    c = srs.Card("w-a", box=srs.MAX_BOX, due_date=D, introduced_on=D)
    c = srs.review(c, True, D)
    assert c.box == srs.MAX_BOX and c.due_date == D + timedelta(days=60)


def test_wrong_goes_back_to_box_0_due_tomorrow():
    c = srs.Card("w-a", box=4, due_date=D, introduced_on=D)
    c = srs.review(c, False, D)
    assert c.box == 0 and c.due_date == D + timedelta(days=1)
    assert c.last_result == "again" and c.lapses == 1


def test_only_first_answer_of_the_day_counts():
    c = srs.Card("w-a", box=2, due_date=D, introduced_on=D)
    c = srs.review(c, False, D)
    c2 = srs.review(c, True, D)  # practice retry in same session
    assert c2 == c


def test_mistakes_come_first_next_day():
    yesterday, today = D, D + timedelta(days=1)
    old = srs.Card("w-old", box=3, due_date=today - timedelta(days=5), introduced_on=D)
    miss = srs.review(srs.Card("w-miss", box=2, due_date=yesterday, introduced_on=D), False, yesterday)
    fresh = srs.Card("w-fresh", box=1, due_date=today, introduced_on=D)
    q = srs.review_queue([fresh, old, miss], today)
    assert [c.word_id for c in q] == ["w-miss", "w-old", "w-fresh"]


def test_queue_skips_future_cards_and_respects_limit():
    cards = [srs.Card(f"w-{i}", box=1, due_date=D, introduced_on=D) for i in range(40)]
    cards.append(srs.Card("w-future", box=1, due_date=D + timedelta(days=3), introduced_on=D))
    q = srs.review_queue(cards, D)
    assert len(q) == srs.DAILY_REVIEW_LIMIT
    assert all(c.word_id != "w-future" for c in q)


def test_words_known_counts_box_3_and_up():
    cards = [srs.Card(f"w-{b}", box=b, due_date=D, introduced_on=D) for b in range(7)]
    assert srs.words_known(cards) == 4
