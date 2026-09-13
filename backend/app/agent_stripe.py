"""Stripe agent write-path — AgentProof's first real (non-simulator) agent
write-path, per docs/PROOF_MODEL.md's credential-separation requirement.

Same shape as app.agent.run_agent(): the agent receives the complete
structured task directly, calls exactly one tool, and the harness (not the
model) stamps the correlation id onto the outgoing request. Uses a
write-only-scoped Stripe Restricted Key (STRIPE_WRITE_KEY) — a distinct
credential from the read-only key app.adapter_stripe.StripeEvidenceAdapter
uses, the same separation the simulator enforces between
AGENT_WRITE_CREDENTIAL and VERIFIER_READ_CREDENTIAL.

Scope: refund-only. Stripe has no notification concept in AgentProof's V0
scope, so unlike app.agent there is no second tool call.
"""

import json
from typing import Any, Protocol

import anthropic
import httpx

from app.agent import ClaudeCaller, real_claude_caller
from app.config import settings
from app.schemas import ExpectedOutcome

AGENT_MODEL = settings.claude_model

SYSTEM_PROMPT = """\
You are a payments agent responsible for issuing refunds through Stripe.

You will be given a structured task object with the exact fields describing \
the refund to perform (order_id — this is the Stripe charge_id to refund, \
expected_amount_minor_units, currency) plus the original customer-facing \
request for context. Always use the values from the structured task object \
for the tool call — never infer the charge id or amount from the prose \
request.

Steps:
1. Call create_stripe_refund with charge_id (use order_id from the task) and \
   amount_minor_units (use expected_amount_minor_units from the task).
2. Once the refund is complete, reply with one short sentence describing \
   what you did. Do not call the tool more than once.
"""

TOOLS = [
    {
        "name": "create_stripe_refund",
        "description": "Issue a refund against an existing Stripe charge.",
        "input_schema": {
            "type": "object",
            "properties": {
                "charge_id": {"type": "string"},
                "amount_minor_units": {"type": "integer"},
            },
            "required": ["charge_id", "amount_minor_units"],
            "additionalProperties": False,
        },
    },
]

MAX_ITERATIONS = 4


class StripeWriteCaller(Protocol):
    """Abstraction over 'issue a Stripe refund', for test injection — same
    pattern as app.agent.ClaudeCaller / app.adapter_stripe.StripeReadCaller."""

    def __call__(self, *, charge_id: str, amount_minor_units: int, run_id: str) -> dict: ...


def real_stripe_write_caller() -> StripeWriteCaller:
    def call(*, charge_id: str, amount_minor_units: int, run_id: str) -> dict:
        # run_id is stamped here by the harness, in Stripe's own metadata
        # field — never exposed to the LLM's tool schema. Mirrors
        # app.agent._execute_tool's discipline: the model has no idea this
        # correlation id exists.
        if not settings.stripe_write_key:
            raise RuntimeError("STRIPE_WRITE_KEY is not configured.")
        headers = {"Authorization": f"Bearer {settings.stripe_write_key}"}
        data = {
            "charge": charge_id,
            "amount": str(amount_minor_units),
            "metadata[run_id]": run_id,
        }
        with httpx.Client(base_url=settings.stripe_api_base, timeout=10.0) as client:
            resp = client.post("/v1/refunds", data=data, headers=headers)
            resp.raise_for_status()
            return resp.json()

    return call


def run_agent_stripe(
    expected_outcome: ExpectedOutcome,
    original_request: str,
    run_id: str,
    claude_caller: ClaudeCaller | None = None,
    stripe_write_caller: StripeWriteCaller | None = None,
) -> dict:
    """Drive the Stripe refund agent to completion. Returns
    {"raw_claim": str, "transcript": list} — same contract as
    app.agent.run_agent()."""

    if claude_caller is None:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        claude_caller = real_claude_caller(client)
    if stripe_write_caller is None:
        stripe_write_caller = real_stripe_write_caller()

    structured_task = expected_outcome.model_dump()
    user_content = (
        "Structured task (authoritative — use these exact field values; "
        "order_id is the Stripe charge_id to refund):\n"
        f"{json.dumps(structured_task, indent=2)}\n\n"
        "Original customer-facing request (context only, not authoritative "
        f"for field values):\n{original_request}"
    )

    messages: list[dict] = [{"role": "user", "content": user_content}]
    transcript: list[dict] = [{"role": "user", "content": user_content}]

    for _ in range(MAX_ITERATIONS):
        response = claude_caller(messages=messages, tools=TOOLS)
        transcript.append({"role": "assistant", "content": _serialize_content(response.content)})

        if response.stop_reason != "tool_use":
            raw_claim = next((b.text for b in response.content if b.type == "text"), "")
            return {"raw_claim": raw_claim, "transcript": transcript}

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                result = stripe_write_caller(
                    charge_id=block.input["charge_id"],
                    amount_minor_units=block.input["amount_minor_units"],
                    run_id=run_id,
                )
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)}
                )
            except httpx.HTTPStatusError as exc:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Error: {exc.response.status_code} {exc.response.text}",
                        "is_error": True,
                    }
                )
        messages.append({"role": "user", "content": tool_results})
        transcript.append({"role": "user", "content": tool_results})

    raise RuntimeError("Agent did not finish within MAX_ITERATIONS")


def _serialize_content(content) -> list[dict]:
    out: list[dict[str, Any]] = []
    for block in content:
        if block.type == "text":
            out.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            out.append({"type": "tool_use", "name": block.name, "input": block.input, "id": block.id})
        else:
            out.append({"type": block.type})
    return out
