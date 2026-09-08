"""Fakes for driving app.agent.run_agent / app.claim_normalizer.normalize_claim
without a live Claude API call, so the automated suite runs offline and
deterministically. Production code paths (real_claude_caller /
real_normalizer_caller) are exercised only by the live smoke test."""

from dataclasses import dataclass, field


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeToolUseBlock:
    name: str
    input: dict
    id: str
    type: str = "tool_use"


@dataclass
class FakeResponse:
    content: list
    stop_reason: str


def scripted_agent_caller(turns: list[tuple[list, str]]):
    """turns: list of (content_blocks, stop_reason), returned in order,
    one per Claude call the agent loop makes."""
    calls = {"i": 0}

    def caller(*, messages, tools):
        content, stop_reason = turns[calls["i"]]
        calls["i"] += 1
        return FakeResponse(content=content, stop_reason=stop_reason)

    return caller


def fixed_normalizer_caller(output: dict):
    def caller(*, raw_claim: str) -> dict:
        return output

    return caller
