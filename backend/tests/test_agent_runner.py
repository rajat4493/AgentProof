"""Unit tests for app.agent.run_agent using a scripted (fake) Claude caller.

Confirms the agent is driven with the complete structured task object
(ExpectedOutcome), not asked to infer fields from prose, that its tool calls
hit the simulator's real write-credentialed action endpoints, and that the
harness — not the model — stamps run_id onto every write so evidence can be
correlated back to this specific run.
"""

import httpx

from app.agent import run_agent
from app.config import settings
from app.schemas import ExpectedOutcome
from tests.fakes import FakeTextBlock, FakeToolUseBlock, scripted_agent_caller


def test_agent_calls_refund_and_notification_then_claims_completion():
    expected = ExpectedOutcome(
        task_id="TASK-x",
        order_id="ORD-1047",
        customer_id="C-891",
        expected_amount_minor_units=18500,
        currency="EUR",
        notification_required=True,
    )

    turn1 = (
        [
            FakeToolUseBlock(
                name="create_refund",
                input={"order_id": "ORD-1047", "customer_id": "C-891", "amount_minor_units": 18500, "currency": "EUR"},
                id="tu_1",
            )
        ],
        "tool_use",
    )
    turn2 = (
        [
            FakeToolUseBlock(
                name="send_notification",
                input={"customer_id": "C-891", "order_id": "ORD-1047", "body": "Your refund is complete."},
                id="tu_2",
            )
        ],
        "tool_use",
    )
    turn3 = (
        [FakeTextBlock(text="Refund completed successfully and the customer has been notified.")],
        "end_turn",
    )

    caller = scripted_agent_caller([turn1, turn2, turn3])
    result = run_agent(
        expected,
        "Refund €185 for Order 1047 and notify the customer.",
        run_id="RUN-agent-test-1",
        claude_caller=caller,
    )

    assert "notified" in result["raw_claim"]
    assert len(result["transcript"]) > 0

    # The tool call the model made carried no run_id (not in its schema) —
    # confirm the harness stamped one anyway, and it's the one this test
    # asked for, not something the model could influence.
    resp = httpx.get(
        f"{settings.simulator_base_url}/simulator/read/refunds",
        params={"order_id": "ORD-1047", "customer_id": "C-891", "run_id": "RUN-agent-test-1"},
        headers={"X-AgentProof-Credential": settings.verifier_read_credential},
    )
    resp.raise_for_status()
    refunds = resp.json()
    assert len(refunds) == 1
    assert refunds[0]["run_id"] == "RUN-agent-test-1"
    assert refunds[0]["amount_minor_units"] == 18500


def test_agent_receives_structured_task_not_asked_to_infer_from_prose():
    """The user message passed to the model must contain the exact
    structured field values — the agent is never told to parse them out of
    the natural-language request itself."""

    captured = {}

    expected = ExpectedOutcome(
        task_id="TASK-y",
        order_id="ORD-9999",
        customer_id="C-1",
        expected_amount_minor_units=4200,
        currency="USD",
        notification_required=False,
    )

    def caller(*, messages, tools):
        captured["messages"] = messages
        from tests.fakes import FakeResponse, FakeTextBlock

        return FakeResponse(content=[FakeTextBlock(text="Done.")], stop_reason="end_turn")

    run_agent(expected, "some vague prose about a refund", run_id="RUN-agent-test-2", claude_caller=caller)

    user_content = captured["messages"][0]["content"]
    assert '"order_id": "ORD-9999"' in user_content
    assert '"expected_amount_minor_units": 4200' in user_content
    assert '"currency": "USD"' in user_content
