"""Usage limits and the rule that user-supplied numbers can be repeated but not computed with."""

from agentkit.grounding import check
from agentkit.limits import UsageLimiter


def test_question_numbers_can_be_repeated_but_not_computed_with():
    question = "If 85 cans and 30 lids cost 100 EUR and a lid costs 0.50 EUR, what does a can cost?"
    found = {n.text: n.status for n in check("85 cans and 30 lids for 100 EUR: a can costs 1.00 EUR", {}, question)}
    assert found == {"85": "grounded", "30": "grounded", "100": "grounded", "1.00": "ungrounded"}


def test_limits_per_client_per_hour_and_per_day():
    now = [0.0]
    limiter = UsageLimiter(per_client_per_hour=2, per_day=3, clock=lambda: now[0])
    assert limiter.check("a") is None and limiter.check("a") is None
    assert "per hour" in limiter.check("a")
    assert limiter.check("b") is None
    assert "daily limit" in limiter.check("c")
    now[0] = 86_400  # a day later both windows have rolled over
    assert limiter.check("a") is None


def test_flagging_marks_only_the_unverified_number():
    from agentkit.guard import flag_unverified
    out = flag_unverified("Terms such as net 30 days; 300 lines are open", ["30"])
    assert "net 30 [unverified] days" in out and "300 lines" in out and out.endswith("treat them with caution.")
