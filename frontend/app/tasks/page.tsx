import Link from "next/link";
import { fetchApi, type Task, type TaskMatch } from "@/lib/api";
import { PageHeader, LegalReviewFlag } from "@/components/PageHeader";
import { ColumnHeader, SkillDots, RelevanceMeter } from "@/components/VisualIndicators";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState, EmptyState } from "@/components/States";

const COLUMNS = [
  { key: "open", label: "Open" },
  { key: "matched", label: "Matched" },
  { key: "in_progress", label: "In Progress" },
  { key: "resolved", label: "Resolved" },
] as const;

export default async function TasksPage({
  searchParams,
}: {
  searchParams: { crisis_id?: string };
}) {
  const crisisId = searchParams.crisis_id;
  const query = crisisId ? `?crisis_id=${crisisId}` : "";

  try {
    const [{ tasks }, matchData] = await Promise.all([
      fetchApi<{ tasks: Task[] }>(`/dashboard/tasks${query}`),
      fetchApi<{ matches: TaskMatch[] }>(`/dashboard/matches${query}`).catch(() => ({
        matches: [] as TaskMatch[],
      })),
    ]);

    const matchesByTask = matchData.matches.reduce<Record<string, TaskMatch[]>>((acc, m) => {
      (acc[m.task_id] ??= []).push(m);
      return acc;
    }, {});

    const byStatus = COLUMNS.reduce<Record<string, Task[]>>((acc, col) => {
      acc[col.key] = tasks.filter((t) => t.status === col.key);
      return acc;
    }, {});

    return (
      <div>
        <PageHeader
          title="Task Board"
          description={
            crisisId
              ? `Tasks for crisis ${crisisId.slice(0, 8)}…`
              : `${tasks.length} tasks across all crises`
          }
        >
          {crisisId && (
            <span className="text-xs text-muted-foreground">Filtered</span>
          )}
        </PageHeader>

        {tasks.length === 0 ? (
          <EmptyState
            message="No tasks yet. Open a crisis and run Decompose tasks."
            actionHref="/crises"
            actionLabel="Browse crises"
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {COLUMNS.map(({ key, label }) => (
              <div key={key} className="flex flex-col">
                <ColumnHeader
                  label={label}
                  count={byStatus[key]?.length ?? 0}
                  statusKey={key}
                />
                <div className="flex flex-1 flex-col gap-3 rounded-lg border border-border bg-card/50 p-3 min-h-[200px]">
                  {(byStatus[key] ?? []).map((task) => (
                    <Card key={task.id} className="shadow-none">
                      <CardHeader className="p-3 pb-1">
                        <CardTitle className="text-sm leading-snug">{task.title}</CardTitle>
                      </CardHeader>
                      <CardContent className="p-3 pt-0">
                        <p className="mb-2 line-clamp-2 text-xs text-muted-foreground">
                          {task.description}
                        </p>
                        <SkillDots skills={task.required_skills} />
                        {task.legal_review_needed && (
                          <div className="mt-2 flex items-center gap-1.5">
                            <LegalReviewFlag />
                            <span className="text-[10px] text-amber-600 dark:text-amber-400">Review</span>
                          </div>
                        )}
                        <Link
                          href={`/crisis/${task.crisis_id}`}
                          className="mt-2 block text-xs text-primary hover:underline"
                        >
                          View crisis →
                        </Link>
                        {(matchesByTask[task.id] ?? []).length > 0 && (
                          <div className="mt-2 space-y-1.5 border-t border-border pt-2">
                            {(matchesByTask[task.id] ?? []).map((m) => (
                              <div key={m.id} className="flex items-center justify-between gap-2 text-xs">
                                <span className="truncate">{m.name}</span>
                                <RelevanceMeter score={Math.round(m.score * 10)} />
                              </div>
                            ))}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  } catch (e) {
    return (
      <div>
        <PageHeader title="Task Board" />
        <ErrorState message={String(e)} />
      </div>
    );
  }
}
