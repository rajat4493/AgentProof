"""Claim normalizer — translation only, never judgment.

The LLM selects a claim_type from a fixed known list and populates only the
fields that claim type's schema declares (docs/ARCHITECTURE.md § LLM
boundary). Its raw tool-call output is then re-validated against the strict
Pydantic model in app.schemas — that Pydantic model, not the LLM's own
schema adherence, is the authoritative boundary. If no known claim_type can
be confidently selected, or a required field is missing, or Pydantic
validation fails, normalization fails and the caller must terminate the run
as NOT_VERIFIABLE. The normalizer never guesses, defaults, or fabricates.
"""

import json
from typing import Protocol

import anthropic
from pydantic import BaseModel, ValidationError

from app.claims import CLAIM_SCHEMAS, KNOWN_CLAIM_TYPES
from app.config import settings

NORMALIZER_MODEL = settings.claude_model

SYSTEM_PROMPT = """\
You translate a support agent's free-text completion claim into a \
structured record. You do not judge whether the claim is true — you only \
extract what the agent said.

Call record_normalized_claim exactly once.

If the claim clearly describes a refund being completed and (optionally) \
the customer being notified, set claim_type to "refund_and_notify" and fill \
in every refund_and_notify field from what the claim states. If the claim \
does not clearly describe this, or you cannot confidently determine a \
required field's value from the text, set claim_type to "not_mappable" and \
leave the other fields null. Never guess a value you cannot support from \
the claim text.
"""

# The tool schema's fields are specific to today's one claim type
# (refund_and_notify) — a second claim type would need its own field set
# here too. What's generic is *validation*: normalize_claim() below looks
# up the Pydantic model for whatever claim_type comes back from
# app.claims.CLAIM_SCHEMAS, rather than hardcoding one model class.
RECORD_CLAIM_TOOL = {
    "name": "record_normalized_claim",
    "description": "Record the structured interpretation of the agent's free-text claim.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "claim_type": {"type": "string", "enum": [*KNOWN_CLAIM_TYPES, "not_mappable"]},
            "order_id": {"type": ["string", "null"]},
            "customer_id": {"type": ["string", "null"]},
            "amount_claimed_minor_units": {"type": ["integer", "null"]},
            "currency_claimed": {"type": ["string", "null"]},
            "refund_claimed": {"type": ["boolean", "null"]},
            "notification_claimed": {"type": ["boolean", "null"]},
        },
        "required": [
            "claim_type",
            "order_id",
            "customer_id",
            "amount_claimed_minor_units",
            "currency_claimed",
            "refund_claimed",
            "notification_claimed",
        ],
        "additionalProperties": False,
    },
}


class NormalizerCaller(Protocol):
    def __call__(self, *, raw_claim: str) -> dict: ...


def real_normalizer_caller(client: anthropic.Anthropic) -> NormalizerCaller:
    def call(*, raw_claim: str) -> dict:
        response = client.messages.create(
            model=NORMALIZER_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[RECORD_CLAIM_TOOL],
            tool_choice={"type": "tool", "name": "record_normalized_claim"},
            messages=[{"role": "user", "content": f"Agent claim:\n{raw_claim}"}],
        )
        tool_use = next(b for b in response.content if b.type == "tool_use")
        return tool_use.input

    return call


class NormalizationResult:
    def __init__(self, claim: BaseModel | None, error: str | None):
        self.claim = claim
        self.error = error

    @property
    def ok(self) -> bool:
        return self.claim is not None


def normalize_claim(raw_claim: str, normalizer_caller: NormalizerCaller | None = None) -> NormalizationResult:
    if normalizer_caller is None:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        normalizer_caller = real_normalizer_caller(client)

    try:
        raw_output = normalizer_caller(raw_claim=raw_claim)
    except Exception as exc:  # noqa: BLE001 — any LLM-call failure is NOT_VERIFIABLE, not a guess
        return NormalizationResult(None, f"Normalizer call failed: {exc}")

    claim_type = raw_output.get("claim_type")
    schema = CLAIM_SCHEMAS.get(claim_type)
    if schema is None:
        return NormalizationResult(None, f"Claim could not be mapped to a known claim_type (got {claim_type!r}).")

    # Drop nulls so Pydantic reports a clean "missing field" rather than a type error.
    candidate = {k: v for k, v in raw_output.items() if v is not None}

    try:
        claim = schema(**candidate)
    except ValidationError as exc:
        return NormalizationResult(None, f"Normalized claim failed schema validation: {exc}")

    return NormalizationResult(claim, None)


def serialize_raw_output_for_audit(raw_output: dict) -> str:
    return json.dumps(raw_output, sort_keys=True)
