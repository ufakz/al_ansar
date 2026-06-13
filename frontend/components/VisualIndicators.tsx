import { cn } from "@/lib/utils";

const SEVERITY_COLORS: Record<number, string> = {
  1: "bg-slate-400",
  2: "bg-slate-500",
  3: "bg-amber-500",
  4: "bg-orange-500",
  5: "bg-red-500",
};

const SEVERITY_GLOW: Record<number, string> = {
  4: "shadow-[0_0_8px_rgba(249,115,22,0.5)]",
  5: "shadow-[0_0_10px_rgba(239,68,68,0.6)]",
};

export function severityClass(severity: number | null | undefined): string {
  if (!severity) return "bg-muted-foreground/30";
  return SEVERITY_COLORS[severity] ?? "bg-muted-foreground/30";
}

/** Vertical severity strip for list rows */
export function SeverityStrip({
  severity,
  className,
}: {
  severity: number | null | undefined;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "w-1 shrink-0 self-stretch rounded-full",
        severityClass(severity),
        severity && severity >= 4 ? SEVERITY_GLOW[severity] : "",
        className
      )}
      title={severity ? `Severity ${severity}` : "Unknown severity"}
    />
  );
}

/** Compact severity indicator: dot + number */
export function SeverityIndicator({ severity }: { severity: number | null | undefined }) {
  if (!severity) {
    return <span className="inline-block h-2 w-2 rounded-full bg-muted-foreground/30" title="No severity" />;
  }
  return (
    <span
      className="inline-flex items-center gap-1.5"
      title={`Severity ${severity}/5`}
    >
      <span
        className={cn(
          "h-2.5 w-2.5 rounded-full",
          severityClass(severity),
          severity >= 4 ? SEVERITY_GLOW[severity] : ""
        )}
      />
      <span className="text-xs font-semibold tabular-nums text-muted-foreground">{severity}</span>
    </span>
  );
}

const STATUS_COLORS: Record<string, string> = {
  open: "bg-amber-500",
  matched: "bg-primary",
  in_progress: "bg-blue-500",
  resolved: "bg-emerald-500",
  pending: "bg-amber-500",
  promoted: "bg-emerald-500",
  under_review: "bg-slate-400",
};

export function StatusDot({ status, showLabel = false }: { status: string; showLabel?: boolean }) {
  const color = STATUS_COLORS[status] ?? "bg-muted-foreground/40";
  return (
    <span className="inline-flex items-center gap-1.5" title={status.replace(/_/g, " ")}>
      <span className={cn("h-2 w-2 shrink-0 rounded-full", color)} />
      {showLabel && (
        <span className="text-xs capitalize text-muted-foreground">
          {status.replace(/_/g, " ")}
        </span>
      )}
    </span>
  );
}

const TRUST_COLORS: Record<string, string> = {
  trusted: "bg-emerald-500",
  org_verified: "bg-primary",
  unverified: "bg-muted-foreground/50",
};

export function TrustDot({ tier }: { tier: string }) {
  return (
    <span
      className={cn("inline-block h-2.5 w-2.5 rounded-full", TRUST_COLORS[tier] ?? "bg-muted-foreground/40")}
      title={tier.replace(/_/g, " ")}
    />
  );
}

/** Score 0–10 as a colored progress bar */
export function RelevanceMeter({ score, max = 10 }: { score: number; max?: number }) {
  const pct = Math.min(100, Math.round((score / max) * 100));
  const barColor =
    score >= 8 ? "bg-emerald-500" : score >= 5 ? "bg-primary" : "bg-muted-foreground/40";

  return (
    <span className="inline-flex items-center gap-1.5" title={`${score}/${max}`}>
      <span className="relative h-1.5 w-10 overflow-hidden rounded-full bg-secondary">
        <span
          className={cn("absolute inset-y-0 left-0 rounded-full transition-all", barColor)}
          style={{ width: `${pct}%` }}
        />
      </span>
    </span>
  );
}

const REGION_COLORS: Record<string, string> = {
  FIN: "bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-500/30",
  GBR: "bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 border-indigo-500/30",
  BGD: "bg-orange-500/15 text-orange-800 dark:text-orange-300 border-orange-500/30",
  LBN: "bg-red-500/15 text-red-800 dark:text-red-300 border-red-500/30",
  SDN: "bg-amber-500/15 text-amber-900 dark:text-amber-300 border-amber-500/30",
};

export function CountryChip({ iso }: { iso: string | null }) {
  if (!iso) return null;
  const style = REGION_COLORS[iso] ?? "bg-secondary text-secondary-foreground border-border";
  return (
    <span
      className={cn(
        "inline-flex h-6 min-w-[2rem] items-center justify-center rounded border px-1.5 text-[10px] font-bold tracking-wider",
        style
      )}
    >
      {iso}
    </span>
  );
}

const SKILL_COLORS: Record<string, string> = {
  legal_aid: "bg-teal-500",
  advocacy: "bg-amber-500",
  translation: "bg-violet-500",
  remote_research: "bg-blue-500",
  foi_request: "bg-indigo-500",
  psychological_support: "bg-pink-500",
  logistics: "bg-orange-500",
  fundraising: "bg-emerald-500",
  medical_triage: "bg-red-500",
  on_ground_aid: "bg-lime-600",
};

export function SkillDots({ skills, max = 4 }: { skills: string[]; max?: number }) {
  const shown = skills.slice(0, max);
  const rest = skills.length - shown.length;
  return (
    <span className="inline-flex items-center gap-1" title={skills.map((s) => s.replace(/_/g, " ")).join(", ")}>
      {shown.map((s) => (
        <span
          key={s}
          className={cn("h-2 w-2 rounded-full", SKILL_COLORS[s] ?? "bg-muted-foreground/50")}
        />
      ))}
      {rest > 0 && (
        <span className="text-[10px] text-muted-foreground">+{rest}</span>
      )}
    </span>
  );
}

export function LiveDot({ ok }: { ok: boolean }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className={cn(
          "h-2.5 w-2.5 rounded-full",
          ok ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-destructive"
        )}
      />
      <span className="text-xs text-muted-foreground">{ok ? "Online" : "Offline"}</span>
    </span>
  );
}

export function ColumnHeader({
  label,
  count,
  statusKey,
}: {
  label: string;
  count: number;
  statusKey: string;
}) {
  const color = STATUS_COLORS[statusKey] ?? "bg-muted-foreground";
  return (
    <div className="mb-3 flex items-center gap-2">
      <span className={cn("h-3 w-1 rounded-full", color)} />
      <h2 className="text-sm font-semibold">{label}</h2>
      <span className="ml-auto rounded-full bg-secondary px-2 py-0.5 text-xs tabular-nums text-muted-foreground">
        {count}
      </span>
    </div>
  );
}
