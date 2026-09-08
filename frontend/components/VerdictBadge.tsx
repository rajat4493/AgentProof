import type { Verdict } from "@/lib/api";

const STYLES: Record<Verdict, { fg: string; bg: string; label: string }> = {
  VERIFIED: { fg: "var(--verified)", bg: "var(--verified-bg)", label: "VERIFIED" },
  CONTRADICTED: { fg: "var(--contradicted)", bg: "var(--contradicted-bg)", label: "CONTRADICTED" },
  INDETERMINATE: { fg: "var(--indeterminate)", bg: "var(--indeterminate-bg)", label: "INDETERMINATE" },
  NOT_VERIFIABLE: { fg: "var(--not-verifiable)", bg: "var(--not-verifiable-bg)", label: "NOT VERIFIABLE" },
};

export function VerdictBadge({ verdict }: { verdict: Verdict | null }) {
  if (!verdict) {
    return (
      <span className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold border" style={{ borderColor: "var(--border)", color: "var(--muted)" }}>
        PENDING
      </span>
    );
  }
  const s = STYLES[verdict];
  return (
    <span
      className="inline-flex items-center rounded-full px-3 py-1 text-xs font-bold tracking-wide"
      style={{ color: s.fg, background: s.bg }}
    >
      {s.label}
    </span>
  );
}
