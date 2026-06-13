import Link from "next/link";
import { fetchApi, type Report } from "@/lib/api";
import { PageHeader, CountryBadge } from "@/components/PageHeader";
import { StatusDot } from "@/components/VisualIndicators";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/States";

export default async function ReportsPage({
  searchParams,
}: {
  searchParams: { status?: string };
}) {
  const status = searchParams.status;
  const query = status ? `?status=${status}` : "";

  try {
    const reports = await fetchApi<Report[]>(`/reports${query}`);

    return (
      <div>
        <PageHeader
          title="Community Reports"
          description={`${reports.length} incident reports from affected communities`}
        >
          <Button asChild variant="outline" size="sm">
            <Link href="/report">New report</Link>
          </Button>
        </PageHeader>

        <div className="mb-6 flex flex-wrap gap-2">
          {["all", "pending", "under_review", "promoted"].map((s) => {
            const active = (!status && s === "all") || status === s;
            return (
              <Button
                key={s}
                asChild
                variant={active ? "default" : "outline"}
                size="sm"
                className="gap-2"
              >
                <Link href={s === "all" ? "/reports" : `/reports?status=${s}`}>
                  {s !== "all" && <StatusDot status={s} />}
                  {s.replace(/_/g, " ")}
                </Link>
              </Button>
            );
          })}
        </div>

        <div className="space-y-4">
          {reports.map((report) => (
            <Card key={report.id}>
              <CardContent className="p-5">
                <div className="mb-2 flex flex-wrap items-center gap-3">
                  <StatusDot status={report.status} showLabel />
                  <CountryBadge iso={report.country_iso} />
                  {report.location_text && (
                    <span className="text-xs text-muted-foreground">{report.location_text}</span>
                  )}
                </div>
                <p className="text-sm leading-relaxed">{report.narrative}</p>
                {report.promoted_crisis_id && (
                  <Button asChild variant="ghost" className="mt-3 h-auto p-0 text-primary">
                    <Link href={`/crisis/${report.promoted_crisis_id}`}>
                      View promoted crisis →
                    </Link>
                  </Button>
                )}
                {report.triage_notes && (
                  <p className="mt-2 text-xs text-muted-foreground">{report.triage_notes}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  } catch (e) {
    return (
      <div>
        <PageHeader title="Community Reports" />
        <ErrorState message={String(e)} />
      </div>
    );
  }
}
