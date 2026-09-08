import type { PredicateResult } from "@/lib/api";

function iconFor(passed: boolean | null) {
  if (passed === true) return { glyph: "✓", color: "var(--verified)" };
  if (passed === false) return { glyph: "✕", color: "var(--contradicted)" };
  return { glyph: "?", color: "var(--indeterminate)" };
}

function describe(p: PredicateResult): string {
  switch (p.field) {
    case "refund_exists":
      return "Refund exists";
    case "refund.order_id":
      return "Refund order matches task";
    case "refund.customer_id":
      return "Refund customer matches task";
    case "refund.amount_minor_units":
      return "Refund amount matches expected amount";
    case "refund.currency":
      return "Refund currency matches expected currency";
    case "refund.status":
      return "Refund status = succeeded";
    case "notification.customer_id":
      return "Notification customer matches task";
    case "notification.order_id":
      return "Notification order matches task";
    case "notification.exists":
      return "Customer notification exists";
    default:
      return p.field;
  }
}

export function PredicateList({ results }: { results: PredicateResult[] }) {
  return (
    <ul className="space-y-2">
      {results.map((p) => {
        const { glyph, color } = iconFor(p.passed);
        return (
          <li key={p.field} className="flex items-start gap-3 text-sm">
            <span className="mt-0.5 font-bold w-4 text-center" style={{ color }}>
              {glyph}
            </span>
            <div>
              <div>{describe(p)}</div>
              {p.passed === false && (
                <div className="mono text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                  expected {JSON.stringify(p.expected)}, observed {JSON.stringify(p.observed)}
                </div>
              )}
              {p.passed === null && p.reason && (
                <div className="text-xs mt-0.5" style={{ color: "var(--indeterminate)" }}>
                  {p.reason}
                </div>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
