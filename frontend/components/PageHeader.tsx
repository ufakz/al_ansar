import { Badge } from "@/components/ui/badge";
import {
  SeverityIndicator,
  StatusDot,
  TrustDot,
  CountryChip,
  SkillDots,
} from "@/components/VisualIndicators";

export function PageHeader({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">{title}</h1>
        {description && (
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {children && <div className="flex shrink-0 flex-wrap items-center gap-2">{children}</div>}
    </div>
  );
}

export function SeverityBadge({ severity }: { severity: number | null }) {
  return <SeverityIndicator severity={severity} />;
}

export function SkillBadge({ skill }: { skill: string }) {
  return <SkillDots skills={[skill]} max={1} />;
}

export function StatusBadge({ status }: { status: string }) {
  return <StatusDot status={status} showLabel />;
}

export function TrustBadge({ tier }: { tier: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <TrustDot tier={tier} />
      <span className="text-xs text-muted-foreground capitalize">{tier.replace(/_/g, " ")}</span>
    </span>
  );
}

export function CountryBadge({ iso }: { iso: string | null }) {
  return <CountryChip iso={iso} />;
}

/** Crisis type pill — compact, muted */
export function TypeChip({ type }: { type: string }) {
  return (
    <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
      {type}
    </span>
  );
}

export function LegalReviewFlag() {
  return (
    <span
      className="inline-block h-2 w-2 rounded-full bg-amber-500"
      title="Legal review needed"
    />
  );
}
