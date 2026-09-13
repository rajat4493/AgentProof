"""Alternative agent runner: drives the refund task via the real Claude Agent
SDK (claude_agent_sdk / the library that powers Claude Code) instead of
app.agent's raw Messages-API tool-use loop.

This exists to test one specific claim: that AgentProof's independent
verification (app/adapter.py, app/verdict_engine.py) works identically no
matter how the agent itself is implemented, because verification never
inspects the agent's tool calls or code — it only re-queries the real
simulator afterward. This module is NOT wired into the default
POST /api/runs flow (app.agent.run_agent remains the default) — it's an
alternate, swappable implementation proving the point, used from
scripts/test_agent_sdk_integration.py.

Same harness-stamping discipline as app/agent.py: run_id and scenario_mode
are added to the tool call's HTTP payload by this module, never exposed in
the tool's input_schema, so the model never sees or influences either.
"""

import json
from typing import Any

import claude_agent_sdk as sdk
import httpx

from app.config import settings
from app.schemas import ExpectedOutcome

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


def _build_tools(run_id: str, scenario_mode: str, http_client: httpx.AsyncClient) -> list:
    headers = {"X-AgentProof-Credential": settings.agent_write_credential}

    @sdk.tool(
        "create_refund",
        "Create a refund for an order in the payment system. Use the exact "
        "order_id, customer_id, amount_minor_units, and currency from the "
        "structured task.",
        {"order_id": str, "customer_id": str, "amount_minor_units": int, "currency": str},
    )
    async def create_refund(args: dict) -> dict:
        payload = {**args, "run_id": run_id, "scenario_mode": scenario_mode}
        resp = await http_client.post("/simulator/actions/refunds", json=payload, headers=headers)
        resp.raise_for_status()
        return {"content": [{"type": "text", "text": json.dumps(resp.json())}]}

    @sdk.tool(
        "send_notification",
        "Send a confirmation notification to the customer about their refund.",
        {"customer_id": str, "order_id": str, "body": str},
    )
    async def send_notification(args: dict) -> dict:
        payload = {**args, "run_id": run_id, "scenario_mode": scenario_mode}
        resp = await http_client.post("/simulator/actions/notifications", json=payload, headers=headers)
        resp.raise_for_status()
        return {"content": [{"type": "text", "text": json.dumps(resp.json())}]}

    return [create_refund, send_notification]


async def run_agent_via_claude_sdk(
    expected_outcome: ExpectedOutcome,
    original_request: str,
    run_id: str,
    scenario_mode: str = "NORMAL",
) -> dict[str, Any]:
    """Same external contract as app.agent.run_agent: returns
    {"raw_claim": str, "transcript": list}. Requires the Claude Agent SDK's
    `claude` CLI to be available on PATH and authorized."""

    structured_task = expected_outcome.model_dump()
    user_prompt = (
        "Structured task (authoritative — use these exact field values):\n"
        f"{json.dumps(structured_task, indent=2)}\n\n"
        "Original customer-facing request (context only, not authoritative "
        f"for field values):\n{original_request}"
    )

    transcript: list[dict] = []
    raw_claim = ""

    async with httpx.AsyncClient(base_url=settings.simulator_base_url, timeout=10.0) as http_client:
        tools = _build_tools(run_id, scenario_mode, http_client)
        server = sdk.create_sdk_mcp_server(name="agentproof_simulator", tools=tools)

        options = sdk.ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={"agentproof_simulator": server},
            allowed_tools=[
                "mcp__agentproof_simulator__create_refund",
                "mcp__agentproof_simulator__send_notification",
            ],
            setting_sources=[],  # clean-room agent — no inherited skills/CLAUDE.md
            cwd="/tmp",
            max_turns=8,
            model=settings.claude_model,
        )

        async for message in sdk.query(prompt=user_prompt, options=options):
            type_name = type(message).__name__
            if type_name == "AssistantMessage":
                for block in message.content:
                    block_type = type(block).__name__
                    if block_type == "TextBlock":
                        transcript.append({"type": "text", "text": block.text})
                    elif block_type == "ToolUseBlock":
                        transcript.append({"type": "tool_use", "name": block.name, "input": block.input})
            elif type_name == "ResultMessage":
                if not message.is_error and message.result:
                    raw_claim = message.result
                transcript.append({"type": "result", "subtype": message.subtype, "result": message.result})

    return {"raw_claim": raw_claim, "transcript": transcript}
