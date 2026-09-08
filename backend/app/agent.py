"""Claude agent runner.

The agent receives the complete structured task object directly (not asked
to infer order/customer/amount from prose) and acts against the simulator's
action endpoints using its own write credential — a real HTTP boundary
distinct from AgentProof's read-only verification path. AgentProof never
sees or trusts these tool-call results as evidence; it independently
re-queries the simulator afterward (see app/adapter.py).
"""

import json
from typing import Any, Protocol

import anthropic
import httpx

from app.config import settings
from app.schemas import ExpectedOutcome

AGENT_MODEL = settings.claude_model

SYSTEM_PROMPT = """\
You are a customer support agent responsible for processing refunds.

You will be given a structured task object with the exact fields describing \
the refund to perform (order_id, customer_id, expected_amount_minor_units, \
currency, notification_required) plus the original customer-facing request \
for context. Always use the values from the structured task object for tool \
calls — never infer order id, customer id, amount, or currency from the \
prose request.

Steps:
1. Call create_refund with order_id, customer_id, amount_minor_units (use \
   expected_amount_minor_units from the task), and currency, all taken \
   directly from the structured task object.
2. If notification_required is true, call send_notification to confirm the \
   refund with the customer, using the same order_id and customer_id.
3. Once both actions are complete, reply with one short sentence describing \
   what you did. Do not call any tool more than once.
"""

TOOLS = [
    {
        "name": "create_refund",
        "description": (
            "Create a refund for an order in the payment system. Use the exact "
            "order_id, customer_id, amount_minor_units, and currency from the "
            "structured task."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "customer_id": {"type": "string"},
                "amount_minor_units": {"type": "integer"},
                "currency": {"type": "string"},
            },
            "required": ["order_id", "customer_id", "amount_minor_units", "currency"],
            "additionalProperties": False,
        },
    },
    {
        "name": "send_notification",
        "description": "Send a confirmation notification to the customer about their refund.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "order_id": {"type": "string"},
                "channel": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["customer_id", "order_id", "body"],
            "additionalProperties": False,
        },
    },
]

MAX_ITERATIONS = 6


class ClaudeCaller(Protocol):
    """Abstraction over a single Messages API call, for test injection."""

    def __call__(self, *, messages: list[dict], tools: list[dict]) -> Any: ...


def real_claude_caller(client: anthropic.Anthropic) -> ClaudeCaller:
    def call(*, messages: list[dict], tools: list[dict]):
        return client.messages.create(
            model=AGENT_MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

    return call


def _execute_tool(
    name: str, tool_input: dict, http_client: httpx.Client, run_id: str, scenario_mode: str
) -> dict:
    # run_id and scenario_mode are stamped here by the harness — never
    # exposed to the LLM's tool schema, never something the model supplies
    # or could get wrong. The agent has no idea either of these exists.
    payload = {**tool_input, "run_id": run_id, "scenario_mode": scenario_mode}
    headers = {"X-AgentProof-Credential": settings.agent_write_credential}
    if name == "create_refund":
        resp = http_client.post("/simulator/actions/refunds", json=payload, headers=headers)
    elif name == "send_notification":
        resp = http_client.post("/simulator/actions/notifications", json=payload, headers=headers)
    else:
        raise ValueError(f"Unknown tool: {name}")
    resp.raise_for_status()
    return resp.json()


def run_agent(
    expected_outcome: ExpectedOutcome,
    original_request: str,
    run_id: str,
    scenario_mode: str = "NORMAL",
    claude_caller: ClaudeCaller | None = None,
) -> dict:
    """Drive the agent to completion. Returns {"raw_claim": str, "transcript": list}."""

    if claude_caller is None:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        claude_caller = real_claude_caller(client)

    structured_task = expected_outcome.model_dump()
    user_content = (
        "Structured task (authoritative — use these exact field values):\n"
        f"{json.dumps(structured_task, indent=2)}\n\n"
        "Original customer-facing request (context only, not authoritative "
        f"for field values):\n{original_request}"
    )

    messages: list[dict] = [{"role": "user", "content": user_content}]
    transcript: list[dict] = [{"role": "user", "content": user_content}]

    with httpx.Client(base_url=settings.simulator_base_url, timeout=10.0) as http_client:
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
                    result = _execute_tool(block.name, block.input, http_client, run_id, scenario_mode)
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
    out = []
    for block in content:
        if block.type == "text":
            out.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            out.append({"type": "tool_use", "name": block.name, "input": block.input, "id": block.id})
        else:
            out.append({"type": block.type})
    return out
