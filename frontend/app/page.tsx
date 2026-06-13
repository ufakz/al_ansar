import Link from "next/link";
import { fetchApi } from "@/lib/api";
import { PageHeader, SeverityBadge, CountryBadge } from "@/components/PageHeader";
import { LiveDot, SeverityStrip } from "@/components/VisualIndicators";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/States";
import { AlertTriangle, Users, Scale, FileText } from "lucide-react";

export default async function HomePage() {
  try {
    const [health, crises, reports, ansar, legal] = await Promise.all([
      fetchApi<{ status: string }>("/health"),
      fetchApi<{ crises: { id: string; title: string; country_iso: string | null; severity: number | null }[] }>("/dashboard/crises"),
      fetchApi<unknown[]>("/reports"),
      fetchApi<{ ansar: unknown[] }>("/dashboard/ansar"),
      fetchApi<{ sources: { chunk_count: number }[] }>("/legal/sources"),
    ]);

    const reportCount = reports.length;
    const chunkCount = legal.sources.reduce((n, s) => n + (s.chunk_count || 0), 0);

    const stats = [
      { label: "Crises", value: crises.crises.length, icon: AlertTriangle, href: "/crises" },
      { label: "Reports", value: reportCount, icon: FileText, href: "/reports" },
      { label: "Legal chunks", value: chunkCount, icon: Scale, href: "/legal" },
      { label: "Ansar helpers", value: ansar.ansar.length, icon: Users, href: "/ansar" },
    ];

    return (
      <div>
        <PageHeader
          title="Operations Overview"
          description="Crisis detection → legal grounding → task decomposition → helper matching"
        />

        <div className="mb-6 page-enter">
          <LiveDot ok={health.status === "ok"} />
        </div>

        <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map(({ label, value, icon: Icon, href }, i) => (
            <Link key={label} href={href} className={`page-enter stagger-${i + 1}`}>
              <Card className="stat-card h-full">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    {label}
                  </CardTitle>
                  <Icon className="h-4 w-4 text-primary/70" />
                </CardHeader>
                <CardContent>
                  <p className="font-display text-4xl font-semibold tabular-nums">{value}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        <Card className="page-enter stagger-5">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Crises</CardTitle>
            <Button asChild variant="outline" size="sm">
              <Link href="/crises">View all</Link>
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {crises.crises.slice(0, 6).map((c) => (
                <Link
                  key={c.id}
                  href={`/crisis/${c.id}`}
                  className="flex items-center gap-3 rounded-lg border border-border/80 bg-secondary/30 p-3 transition-all duration-200 hover:border-primary/40 hover:bg-primary/5"
                >
                  <SeverityStrip severity={c.severity} className="h-10" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{c.title}</p>
                    <div className="mt-1 flex items-center gap-2">
                      <CountryBadge iso={c.country_iso} />
                    </div>
                  </div>
                  <SeverityBadge severity={c.severity} />
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  } catch (e) {
    return (
      <div>
        <PageHeader title="Operations Overview" />
        <ErrorState message={`Backend unreachable: ${String(e)}. Start with docker compose up.`} />
      </div>
    );
  }
}
