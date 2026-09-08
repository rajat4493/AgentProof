"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { claimRun, createRun, createTask, listRuns, verifyRun, type Run } from "@/lib/api";
import { formatMoney, formatRelativeTime } from "@/lib/format";
import { VerdictBadge } from "@/components/VerdictBadge";
import { Card, CardBody, CardHeader } from "@/components/Card";

const DEFAULT_FORM = {
  order_id: "ORD-1047",
  customer_id: "C-891",
  amount: "185.00",
  currency: "EUR",
  notification_required: true,
  original_request: "Refund €185 for Order 1047 and notify the customer.",
};

export default function HomePage() {
  const router = useRouter();
  const [runs, setRuns] = useState<Run[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function refreshRuns() {
    listRuns()
      .then(setRuns)
      .catch(() => {})
      .finally(() => setLoadingRuns(false));
  }

  useEffect(() => {
    refreshRuns();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setStatus("Creating task…");
      const task = await createTask({
        order_id: form.order_id,
        customer_id: form.customer_id,
        expected_amount_minor_units: Math.round(parseFloat(form.amount) * 100),
        currency: form.currency,
        notification_required: form.notification_required,
        original_request: form.original_request,
      });

      setStatus("Running Claude agent against the simulator…");
      const run = await createRun(task.id);

      setStatus("Normalizing agent claim…");
      await claimRun(run.id);

      setStatus("AgentProof independently verifying…");
      await verifyRun(run.id);

      router.push(`/runs/${run.id}`);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
      setStatus(null);
    }
  }

  const verified = runs.filter((r) => r.verdict === "VERIFIED").length;
  const contradicted = runs.filter((r) => r.verdict === "CONTRADICTED").length;
  const indeterminate = runs.filter((r) => r.verdict === "INDETERMINATE").length;

  return (
    <div className="mx-auto max-w-5xl px-6 py-10 space-y-10">
      <section>
        <h1 className="text-3xl font-semibold tracking-tight">AgentProof</h1>
        <p className="mt-1" style={{ color: "var(--muted)" }}>
          Independent verification for autonomous work.
        </p>

        <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Stat label="Agent tasks" value={String(runs.length)} />
          <Stat label="Verified" value={`${verified}`} color="var(--verified)" />
          <Stat label="Contradicted" value={`${contradicted}`} color="var(--contradicted)" />
          <Stat label="Indeterminate" value={`${indeterminate}`} color="var(--indeterminate)" />
        </div>
      </section>

      <section className="grid md:grid-cols-2 gap-8">
        <Card>
          <CardHeader>Run a refund verification task</CardHeader>
          <CardBody>
            <form className="space-y-3" onSubmit={handleSubmit}>
              <Field label="Order ID">
                <input
                  className="input"
                  value={form.order_id}
                  onChange={(e) => setForm({ ...form, order_id: e.target.value })}
                />
              </Field>
              <Field label="Customer ID">
                <input
                  className="input"
                  value={form.customer_id}
                  onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
                />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Amount">
                  <input
                    className="input"
                    value={form.amount}
                    onChange={(e) => setForm({ ...form, amount: e.target.value })}
                  />
                </Field>
                <Field label="Currency">
                  <input
                    className="input"
                    value={form.currency}
                    onChange={(e) => setForm({ ...form, currency: e.target.value.toUpperCase() })}
                  />
                </Field>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.notification_required}
                  onChange={(e) => setForm({ ...form, notification_required: e.target.checked })}
                />
                Notification required
              </label>
              <Field label="Request">
                <textarea
                  className="input"
                  rows={3}
                  value={form.original_request}
                  onChange={(e) => setForm({ ...form, original_request: e.target.value })}
                />
              </Field>

              <button
                type="submit"
                disabled={busy}
                className="w-full rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                style={{ background: "var(--accent)" }}
              >
                {busy ? status || "Running…" : "Run agent + verify"}
              </button>
              {error && (
                <p className="text-xs" style={{ color: "var(--contradicted)" }}>
                  {error}
                </p>
              )}
            </form>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>Live feed</CardHeader>
          <CardBody className="p-0">
            {loadingRuns ? (
              <p className="px-5 py-4 text-sm" style={{ color: "var(--muted)" }}>
                Loading…
              </p>
            ) : runs.length === 0 ? (
              <p className="px-5 py-4 text-sm" style={{ color: "var(--muted)" }}>
                No runs yet.
              </p>
            ) : (
              <ul>
                {runs.map((r) => (
                  <li key={r.id} className="border-t first:border-t-0" style={{ borderColor: "var(--border)" }}>
                    <Link href={`/runs/${r.id}`} className="flex items-center justify-between px-5 py-3 hover:opacity-80">
                      <div>
                        <div className="text-sm font-medium">
                          {r.task.order_id} · {formatMoney(r.task.expected_amount_minor_units, r.task.currency)}
                        </div>
                        <div className="text-xs" style={{ color: "var(--muted)" }}>
                          {r.agent_identity} · {formatRelativeTime(r.created_at)}
                        </div>
                      </div>
                      <VerdictBadge verdict={r.verdict} />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      </section>

      <style jsx global>{`
        .input {
          width: 100%;
          border-radius: 0.5rem;
          border: 1px solid var(--border);
          background: var(--surface);
          padding: 0.5rem 0.75rem;
          font-size: 0.875rem;
        }
      `}</style>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="block mb-1" style={{ color: "var(--muted)" }}>
        {label}
      </span>
      {children}
    </label>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <Card>
      <CardBody>
        <div className="text-2xl font-semibold" style={{ color: color || "inherit" }}>
          {value}
        </div>
        <div className="text-xs mt-1" style={{ color: "var(--muted)" }}>
          {label}
        </div>
      </CardBody>
    </Card>
  );
}
