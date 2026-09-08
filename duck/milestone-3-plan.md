# Duck — milestone-3-plan

## Intent

Extract only the generic primitives that Milestones 1–2's working refund implementation already
proved out — claim model, proof definition, evidence adapter interface, verdict engine — as
named, reusable shapes. No new capability, no second scenario, no abstraction invented ahead of
what the refund flow already does. This is the last milestone of V0.

## Scope

For each of the four primitives named in `docs/MVP_SCOPE.md` § Milestone 3, extract exactly what
the current code already implicitly does, made explicit and reusable — nothing more:

1. **Claim model.** `app/claim_normalizer.py`'s `normalize_claim()` currently hardcodes
   `RefundAndNotifyClaim` as the one Pydantic model it validates against. Extract a
   `claim_type -> Pydantic model class` registry (`app/claims.py`) so the normalizer looks up the
   schema generically. Still exactly one entry (`refund_and_notify`) — the registry exists so a
   second claim type could be added without touching `normalize_claim()`'s logic, not because a
   second type is coming in V0.
2. **Proof definition.** `app/proof.py`'s `REFUND_COMPLETED_V1` is currently a raw dict literal.
   Extract typed `ProofCheck` and `ProofDefinition` structures so the shape is an importable type
   instead of an implicit JSON convention — matching `docs/PROOF_MODEL.md`'s existing statement
   that proof definitions should be "architected so a visual builder could be added later."
   `app/verdict_engine.py`'s `evaluate()` takes the typed `ProofDefinition` instead of a raw dict.
3. **Evidence adapter interface.** `EvidenceAdapter` (Protocol) already exists in `app/adapter.py`
   from Milestone 1 and needs no change. What's missing is that `app/main.py`'s `verify_run()`
   hardcodes `PaymentCustomerEvidenceAdapter()` directly, coupling the API layer to one concrete
   adapter class. Extract a `claim_type -> adapter instance` registry so `verify_run()` resolves
   the adapter generically, the same shape as the claim-schema and proof-definition registries.
4. **Verdict engine.** `app/verdict_engine.py`'s `evaluate()` is already fully generic — it
   contains no refund-specific logic, only proof-definition-driven equality checks against an
   `ExpectedOutcome`. No functional change beyond taking the newly-typed `ProofDefinition`.

Explicitly not in scope: a second scenario/claim type/adapter to prove the registries "really"
generalize (that's Milestone 4+'s job, not authorized here), a config-driven or file-based proof
definition loader, dynamic adapter discovery/plugin loading, any change to verdict semantics or
the API surface. This milestone must produce zero observable behavior change — the refund
scenario's four verdicts (VERIFIED/CONTRADICTED/INDETERMINATE/NOT_VERIFIABLE) work exactly as
before; only the internal shape of the code changes.

V0 is Milestones 1–3. This is the last milestone V0's approval covers — completing it closes out
V0 pending human review, and any post-V0 roadmap item requires separate approval.

## Assumptions

- "Extraction" means introducing types/registries around existing logic, not rewriting the
  refund flow's behavior. Every existing test should pass unmodified in *assertions* — only
  import paths / helper construction may need to change where they touch the refactored modules
  directly (e.g. a test that imports `REFUND_COMPLETED_V1` as a dict).
- No migration is needed — this milestone touches no database schema.
- A single live Claude API smoke test (not all four scenarios again) is sufficient regression
  evidence for this milestone, since the four scenarios' live behavior was already proven in
  Milestone 2 and this milestone changes no runtime behavior, only internal structure.

## Planned Tests

1. Full existing automated suite (15 tests) passes unmodified in substance after the refactor.
2. Frontend build stays clean (untouched by this milestone, but confirmed regardless since the
   API response shapes must not change).
3. One live end-to-end run against the real Claude API, confirming the refactored
   claim-schema/proof-definition/adapter registries produce the same VERIFIED result as before.

## Known Unknowns

- Whether to make the registries plain `dict`s or introduce a tiny "registry" helper class —
  leaning toward plain dicts (`CLAIM_SCHEMAS: dict[str, type[BaseModel]]`,
  `ADAPTER_REGISTRY: dict[str, EvidenceAdapter]`), since a wrapper class around a single-entry
  dict would itself be exactly the kind of invented-ahead-of-need abstraction this milestone is
  supposed to avoid.
