"""Monthly Claude API usage counter.

Every Claude API call (Phase 2+) must go through `record()` after the call and
`can_spend()` before it, so the monthly budget from .env is respected.
"""
from datetime import date

# Rough EUR per million tokens. Update when the model or prices change.
PRICE_EUR_PER_MTOK = {"input": 2.8, "output": 14.0}


def month_key(day: date | None = None) -> str:
    return (day or date.today()).strftime("%Y-%m")


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * PRICE_EUR_PER_MTOK["input"] + output_tokens * PRICE_EUR_PER_MTOK["output"]) / 1_000_000


def record(conn, input_tokens: int, output_tokens: int, day: date | None = None) -> None:
    cost = estimate_cost(input_tokens, output_tokens)
    conn.execute(
        "INSERT INTO api_usage (month, calls, input_tokens, output_tokens, est_cost_eur) VALUES (?, 1, ?, ?, ?) "
        "ON CONFLICT(month) DO UPDATE SET calls = calls + 1, input_tokens = input_tokens + excluded.input_tokens, "
        "output_tokens = output_tokens + excluded.output_tokens, est_cost_eur = est_cost_eur + excluded.est_cost_eur",
        (month_key(day), input_tokens, output_tokens, cost),
    )
    conn.commit()


def this_month(conn, day: date | None = None) -> dict:
    row = conn.execute("SELECT * FROM api_usage WHERE month = ?", (month_key(day),)).fetchone()
    if not row:
        return {"month": month_key(day), "calls": 0, "input_tokens": 0, "output_tokens": 0, "est_cost_eur": 0.0}
    return dict(row)


def can_spend(conn, budget_eur: float, day: date | None = None) -> bool:
    return this_month(conn, day)["est_cost_eur"] < budget_eur
