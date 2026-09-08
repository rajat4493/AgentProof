"""Deterministic verdict engine — a generic primitive.

No probabilistic or semantic judgment. Every check is a literal equality
between independently observed evidence and either a fixed expected value or
the original structured ExpectedOutcome — never the agent's claim. This
function contains no refund-specific logic: it operates entirely on the
ProofDefinition it's given (app/proof.py) and would run identically over any
future claim type's proof definition.
"""

from app.proof import ProofDefinition
from app.schemas import ExpectedOutcome, PredicateResult
from app.models import Verdict


def _resolve_source(source: str, expected_outcome: ExpectedOutcome):
    return getattr(expected_outcome, source)


def evaluate(
    proof_definition: ProofDefinition,
    expected_outcome: ExpectedOutcome,
    normalized_evidence: dict,
    unreachable_fields: set[str],
) -> tuple[Verdict, list[PredicateResult]]:
    results: list[PredicateResult] = []

    for check in proof_definition.required_checks:
        expected = check.expected if check.expected is not None else _resolve_source(check.source, expected_outcome)
        observed = normalized_evidence.get(check.field)

        if check.field in unreachable_fields:
            results.append(
                PredicateResult(
                    field=check.field,
                    operator=check.operator,
                    expected=expected,
                    observed=None,
                    passed=None,
                    reason="Evidence source unreachable — could not independently verify.",
                )
            )
            continue

        if check.operator != "equals":
            raise ValueError(f"Unsupported operator: {check.operator!r}")

        passed = observed == expected
        results.append(
            PredicateResult(field=check.field, operator=check.operator, expected=expected, observed=observed, passed=passed)
        )

    if any(r.passed is False for r in results):
        verdict = Verdict.CONTRADICTED
    elif any(r.passed is None for r in results):
        verdict = Verdict.INDETERMINATE
    else:
        verdict = Verdict.VERIFIED

    return verdict, results
