import Link from "next/link";
import { fetchApi, type Crisis } from "@/lib/api";
import { PageHeader, SeverityBadge, CountryBadge, TypeChip } from "@/components/PageHeader";
import { SeverityStrip } from "@/components/VisualIndicators";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorState } from "@/components/States";

export default async function CrisesPage() {
  try {
    const { crises } = await fetchApi<{ crises: Crisis[] }>("/dashboard/crises");

    return (
      <div>
        <PageHeader
          title="Crises"
          description={`${crises.length} active crisis objects from GDELT and community reports`}
        />

        <div className="space-y-3">
          {crises.map((c) => (
            <Link key={c.id} href={`/crisis/${c.id}`}>
              <Card className="transition-colors hover:border-primary/40">
                <CardContent className="flex gap-4 p-5">
                  <SeverityStrip severity={c.severity} />
                  <div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0 space-y-1">
                      <p className="font-semibold">{c.title}</p>
                      {c.summary && (
                        <p className="line-clamp-2 text-sm text-muted-foreground">{c.summary}</p>
                      )}
                      <div className="flex items-center gap-2 pt-1">
                        <CountryBadge iso={c.country_iso} />
                        {c.type && <TypeChip type={c.type} />}
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-3">
                      <SeverityBadge severity={c.severity} />
                      <span className="text-xs text-muted-foreground">→</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    );
  } catch (e) {
    return (
      <div>
        <PageHeader title="Crises" />
        <ErrorState message={String(e)} />
      </div>
    );
  }
}
