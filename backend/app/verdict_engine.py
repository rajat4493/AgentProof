"""Deterministic verdict engine.

No probabilistic or semantic judgment. Every check is a literal equality
between independently observed evidence and either a fixed expected value or
the original structured ExpectedOutcome — never the agent's claim.
"""

from app.schemas import ExpectedOutcome, PredicateResult
from app.models import Verdict


def _resolve_source(source: str, expected_outcome: ExpectedOutcome):
    return getattr(expected_outcome, source)


def evaluate(
    proof_definition: dict,
    expected_outcome: ExpectedOutcome,
    normalized_evidence: dict,
    unreachable_fields: set[str],
) -> tuple[Verdict, list[PredicateResult]]:
    results: list[PredicateResult] = []

    for check in proof_definition["required_checks"]:
        field = check["field"]
        operator = check["operator"]
        expected = check["expected"] if "expected" in check else _resolve_source(check["source"], expected_outcome)
        observed = normalized_evidence.get(field)

        if field in unreachable_fields:
            results.append(
                PredicateResult(
                    field=field,
                    operator=operator,
                    expected=expected,
                    observed=None,
                    passed=None,
                    reason="Evidence source unreachable — could not independently verify.",
                )
            )
            continue

        if operator != "equals":
            raise ValueError(f"Unsupported operator: {operator!r}")

        passed = observed == expected
        results.append(
            PredicateResult(field=field, operator=operator, expected=expected, observed=observed, passed=passed)
        )

    if any(r.passed is False for r in results):
        verdict = Verdict.CONTRADICTED
    elif any(r.passed is None for r in results):
        verdict = Verdict.INDETERMINATE
    else:
        verdict = Verdict.VERIFIED

    return verdict, results
