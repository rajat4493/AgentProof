"""Unit tests for app.agent_stripe.run_agent_stripe using scripted (fake)
Claude + Stripe callers — same offline-testing discipline as
tests/test_agent_runner.py, extended with an injected StripeWriteCaller so
this suite never makes a real Stripe API call.
"""

from app.agent_stripe import run_agent_stripe
from app.schemas import ExpectedOutcome
from tests.fakes import FakeTextBlock, FakeToolUseBlock, scripted_agent_caller


def test_agent_calls_create_stripe_refund_with_run_id_stamped_by_harness():
    expected = ExpectedOutcome(
        task_id="TASK-stripe-1",
        order_id="ch_test_123",
        customer_id="cus_test_abc",
        expected_amount_minor_units=5000,
        currency="USD",
        notification_required=False,
    )

    turn1 = (
        [FakeToolUseBlock(name="create_stripe_refund", input={"charge_id": "ch_test_123", "amount_minor_units": 5000}, id="tu_1")],
        "tool_use",
    )
    turn2 = ([FakeTextBlock(text="Refunded $50.00 against charge ch_test_123.")], "end_turn")

    claude_caller = scripted_agent_caller([turn1, turn2])

    captured = {}

    def fake_stripe_write_caller(*, charge_id: str, amount_minor_units: int, run_id: str) -> dict:
        captured["charge_id"] = charge_id
        captured["amount_minor_units"] = amount_minor_units
        captured["run_id"] = run_id
        return {"id": "re_test_1", "charge": charge_id, "amount": amount_minor_units, "status": "succeeded"}

    result = run_agent_stripe(
        expected,
        "Refund $50 against charge ch_test_123.",
        run_id="RUN-stripe-test-1",
        claude_caller=claude_caller,
        stripe_write_caller=fake_stripe_write_caller,
    )

    assert "Refunded" in result["raw_claim"]
    # The model's tool call carried no run_id (not in its schema) — confirm
    # the harness stamped one anyway, matching what this test asked for.
    assert captured["run_id"] == "RUN-stripe-test-1"
    assert captured["charge_id"] == "ch_test_123"
    assert captured["amount_minor_units"] == 5000


def test_agent_receives_structured_task_with_order_id_as_charge_id():
    captured = {}

    expected = ExpectedOutcome(
        task_id="TASK-stripe-2",
        order_id="ch_test_999",
        customer_id="cus_test_z",
        expected_amount_minor_units=1234,
        currency="EUR",
        notification_required=False,
    )

    def claude_caller(*, messages, tools):
        captured["messages"] = messages
        return type("R", (), {"content": [FakeTextBlock(text="Done.")], "stop_reason": "end_turn"})()

    run_agent_stripe(expected, "some vague prose", run_id="RUN-stripe-test-2", claude_caller=claude_caller)

    user_content = captured["messages"][0]["content"]
    assert '"order_id": "ch_test_999"' in user_content
    assert '"expected_amount_minor_units": 1234' in user_content
