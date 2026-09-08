"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getRun, type Run } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { VerdictBadge } from "@/components/VerdictBadge";
import { Card, CardHeader, CardBody } from "@/components/Card";
import { PredicateList } from "@/components/PredicateList";

export default function RunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getRun(id)
      .then((r) => !cancelled && setRun(r))
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) return <div className="mx-auto max-w-3xl px-6 py-10 text-sm" style={{ color: "var(--contradicted)" }}>{error}</div>;
  if (!run) return <div className="mx-auto max-w-3xl px-6 py-10 text-sm" style={{ color: "var(--muted)" }}>Loading…</div>;

  const { task } = run;

  return (
    <div className="mx-auto max-w-3xl px-6 py-10 space-y-6">
      <div className="flex items-center justify-between">
        <Link href="/" className="text-sm" style={{ color: "var(--accent)" }}>
          ← All runs
        </Link>
        <div className="flex items-center gap-2">
          {task.scenario_mode !== "NORMAL" && (
            <span
              className="mono text-xs rounded px-2 py-1 border"
              style={{ borderColor: "var(--border)", color: "var(--muted)" }}
            >
              demo mode: {task.scenario_mode}
            </span>
          )}
          <VerdictBadge verdict={run.verdict} />
        </div>
      </div>

      <Card>
        <CardHeader>Task</CardHeader>
        <CardBody>
          <p className="text-base">{task.original_request}</p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>Expected outcome</CardHeader>
        <CardBody>
          <dl className="grid grid-cols-2 gap-y-2 text-sm mono">
            <dt style={{ color: "var(--muted)" }}>Order</dt>
            <dd>{task.order_id}</dd>
            <dt style={{ color: "var(--muted)" }}>Customer</dt>
            <dd>{task.customer_id}</dd>
            <dt style={{ color: "var(--muted)" }}>Amount</dt>
            <dd>{formatMoney(task.expected_amount_minor_units, task.currency)}</dd>
            <dt style={{ color: "var(--muted)" }}>Currency</dt>
            <dd>{task.currency}</dd>
            <dt style={{ color: "var(--muted)" }}>Notification</dt>
            <dd>{task.notification_required ? "Required" : "Not required"}</dd>
          </dl>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>Agent claim</CardHeader>
        <CardBody>
          <p className="text-sm italic">{run.raw_claim ? `"${run.raw_claim}"` : "No claim recorded."}</p>
          {run.normalization_error && (
            <p className="text-xs mt-2" style={{ color: "var(--not-verifiable)" }}>
              Normalization: {run.normalization_error}
            </p>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader>Independent proof</CardHeader>
        <CardBody>
          {run.predicate_results ? (
            <PredicateList results={run.predicate_results} />
          ) : (
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              No proof was evaluated — the claim could not be verified.
            </p>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader>Verdict</CardHeader>
        <CardBody className="space-y-2">
          <VerdictBadge verdict={run.verdict} />
          <p className="text-sm">{run.verdict_explanation}</p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>Evidence</CardHeader>
        <CardBody>
          <ul className="text-sm space-y-1">
            {(run.systems_queried || []).map((s) => (
              <li key={s} className="flex justify-between">
                <span>{s.replace(/_/g, " ")}</span>
                <span className="mono text-xs" style={{ color: "var(--muted)" }}>
                  {run.verified_at ? new Date(run.verified_at).toLocaleString() : "—"}
                </span>
              </li>
            ))}
          </ul>
          <p className="text-xs mt-3" style={{ color: "var(--muted)" }}>
            Credential role used: {run.credential_role_used || "—"} · Proof definition:{" "}
            {run.proof_definition_id || "—"}
          </p>
        </CardBody>
      </Card>
    </div>
  );
}
