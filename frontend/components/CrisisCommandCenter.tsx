"use client";

import { useState } from "react";
import Link from "next/link";
import {
  fetchApi,
  postApi,
  type Crisis,
  type Grounding,
  type Task,
  type MatchedUser,
  type TaskMatchGroup,
  type TaskMatchResult,
  type NotifyResult,
} from "@/lib/api";
import { PageHeader, SeverityBadge, CountryBadge, TypeChip, LegalReviewFlag } from "@/components/PageHeader";
import { RelevanceMeter, SkillDots, StatusDot } from "@/components/VisualIndicators";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Loader2, CheckCircle2, Scale, Users, ListTodo, Bell, UserCheck } from "lucide-react";

type ActionState = {
  loading: boolean;
  done: boolean;
  cached?: boolean;
  elapsed?: number;
  error?: string;
};

const initialAction: ActionState = { loading: false, done: false };

export function CrisisCommandCenter({
  crisis,
  initialGrounding,
  initialTasks = [],
  initialTaskMatches = [],
}: {
  crisis: Crisis;
  initialGrounding: Grounding | null;
  initialTasks?: Task[];
  initialTaskMatches?: TaskMatchGroup[];
}) {
  const [grounding, setGrounding] = useState<Grounding | null>(initialGrounding);
  const [tasks, setTasks] = useState<Task[]>(initialTasks);
  const [taskMatches, setTaskMatches] = useState<TaskMatchGroup[]>(initialTaskMatches);
  const [groundState, setGroundState] = useState<ActionState>(
    initialGrounding ? { loading: false, done: true } : initialAction
  );
  const [matchState, setMatchState] = useState<ActionState>(
    initialGrounding?.matched_users?.length
      ? { loading: false, done: true }
      : initialAction
  );
  const [decomposeState, setDecomposeState] = useState<ActionState>(
    initialTasks.length > 0 ? { loading: false, done: true } : initialAction
  );
  const [taskMatchState, setTaskMatchState] = useState<ActionState>(
    initialTaskMatches.length > 0 ? { loading: false, done: true } : initialAction
  );
  const [notifyState, setNotifyState] = useState<ActionState>(initialAction);

  const crisisId = crisis.id;
  const hasGrounding = !!grounding;
  const hasMatches = (grounding?.matched_users?.length ?? 0) > 0;
  const hasTasks = tasks.length > 0;
  const hasTaskMatches = taskMatches.length > 0;

  const matchesByTaskId = Object.fromEntries(
    taskMatches.map((g) => [g.task_id, g.matches])
  );

  async function refreshGrounding() {
    const g = await fetchApi<Grounding>(`/dashboard/grounding/${crisisId}`);
    setGrounding(g);
    return g;
  }

  async function handleGround(force = false) {
    setGroundState({ loading: true, done: false });
    try {
      const res = await postApi<{ cached?: boolean; elapsed_seconds?: number }>(
        `/ground/${crisisId}${force ? "?force=true" : ""}`
      );
      await refreshGrounding();
      setGroundState({ loading: false, done: true, cached: res.cached, elapsed: res.elapsed_seconds });
    } catch (e) {
      setGroundState({ loading: false, done: false, error: String(e) });
    }
  }

  async function handleMatch(force = false) {
    setMatchState({ loading: true, done: false });
    try {
      const res = await postApi<{ cached?: boolean; elapsed_seconds?: number }>(
        `/match/${crisisId}${force ? "?force=true" : ""}`
      );
      await refreshGrounding();
      setMatchState({ loading: false, done: true, cached: res.cached, elapsed: res.elapsed_seconds });
    } catch (e) {
      setMatchState({ loading: false, done: false, error: String(e) });
    }
  }

  async function handleDecompose(force = false) {
    setDecomposeState({ loading: true, done: false });
    try {
      const res = await postApi<{ tasks: Task[]; cached?: boolean; elapsed_seconds?: number }>(
        `/decompose/${crisisId}${force ? "?force=true" : ""}`
      );
      setTasks(res.tasks);
      setTaskMatches([]);
      setTaskMatchState(initialAction);
      setNotifyState(initialAction);
      setDecomposeState({ loading: false, done: true, cached: res.cached, elapsed: res.elapsed_seconds });
    } catch (e) {
      setDecomposeState({ loading: false, done: false, error: String(e) });
    }
  }

  async function handleTaskMatch(force = false) {
    setTaskMatchState({ loading: true, done: false });
    try {
      const res = await postApi<TaskMatchResult>(
        `/match/tasks/${crisisId}${force ? "?force=true" : ""}`
      );
      setTaskMatches(res.tasks);
      const tasksRes = await fetchApi<{ tasks: Task[] }>(`/dashboard/tasks?crisis_id=${crisisId}`);
      setTasks(tasksRes.tasks);
      setTaskMatchState({
        loading: false,
        done: true,
        cached: res.cached,
        elapsed: res.elapsed_seconds,
      });
    } catch (e) {
      setTaskMatchState({ loading: false, done: false, error: String(e) });
    }
  }

  async function handleNotify(force = false) {
    setNotifyState({ loading: true, done: false });
    try {
      const res = await postApi<NotifyResult>(
        `/notify/${crisisId}${force ? "?force=true" : ""}`
      );
      setNotifyState({
        loading: false,
        done: true,
        cached: res.cached,
        elapsed: res.elapsed_seconds,
      });
    } catch (e) {
      setNotifyState({ loading: false, done: false, error: String(e) });
    }
  }

  return (
    <div>
      <PageHeader title={crisis.title} description={crisis.summary ?? undefined}>
        <CountryBadge iso={crisis.country_iso} />
        <SeverityBadge severity={crisis.severity} />
        {crisis.type && <TypeChip type={crisis.type} />}
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Action pipeline */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Action Pipeline</CardTitle>
            <CardDescription>Run each step in order</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <ActionButton
              step={1}
              icon={Scale}
              label="Ground in law"
              state={groundState}
              onClick={() => handleGround()}
              onForce={() => handleGround(true)}
            />
            <ActionButton
              step={2}
              icon={Users}
              label="Match helpers"
              state={matchState}
              disabled={!hasGrounding}
              onClick={() => handleMatch()}
              onForce={() => handleMatch(true)}
            />
            <ActionButton
              step={3}
              icon={ListTodo}
              label="Decompose tasks"
              state={decomposeState}
              disabled={!hasGrounding}
              onClick={() => handleDecompose()}
              onForce={() => handleDecompose(true)}
            />
            <ActionButton
              step={4}
              icon={UserCheck}
              label="Match per task"
              state={taskMatchState}
              disabled={!hasTasks}
              onClick={() => handleTaskMatch()}
              onForce={() => handleTaskMatch(true)}
            />
            <ActionButton
              step={5}
              icon={Bell}
              label="Send notifications"
              state={notifyState}
              disabled={!hasTaskMatches}
              onClick={() => handleNotify()}
              onForce={() => handleNotify(true)}
            />
          </CardContent>
        </Card>

        {/* Legal grounding */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">Legal Backing</CardTitle>
            <CardDescription>
              {grounding
                ? grounding.summary ?? `${grounding.matched_chunks.length} provisions`
                : "Not grounded yet"}
            </CardDescription>
          </CardHeader>
          <CardContent className="max-h-[480px] space-y-3 overflow-y-auto">
            {!grounding && (
              <p className="text-sm text-muted-foreground">Click &quot;Ground in law&quot; to find relevant legal provisions.</p>
            )}
            {grounding?.matched_chunks.map((chunk) => (
              <div key={chunk.chunk_id} className="rounded-lg border border-border/80 p-3">
                <div className="mb-1 flex items-start justify-between gap-2">
                  <p className="text-sm font-medium leading-snug">{chunk.title}</p>
                  <RelevanceMeter score={chunk.relevance_score} />
                </div>
                {chunk.article_ref && (
                  <p className="text-xs text-primary">{chunk.article_ref}</p>
                )}
                <p className="mt-1 text-xs italic text-muted-foreground line-clamp-2">&ldquo;{chunk.excerpt}&rdquo;</p>
                {chunk.url && (
                  <a href={chunk.url} target="_blank" rel="noreferrer" className="mt-1 block text-xs text-primary hover:underline">
                    View source
                  </a>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Matched users */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Matched Helpers</CardTitle>
            <CardDescription>
              {hasMatches
                ? `${grounding!.matched_users.length} relevant Ansar helpers`
                : "No matches yet"}
            </CardDescription>
          </CardHeader>
          <CardContent className="max-h-[480px] space-y-3 overflow-y-auto">
            {!hasMatches && (
              <p className="text-sm text-muted-foreground">Click &quot;Match helpers&quot; after grounding.</p>
            )}
            {grounding?.matched_users.map((user: MatchedUser) => (
              <div key={user.ansar_id} className="rounded-lg border border-border/80 p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">{user.name}</p>
                  <RelevanceMeter score={user.relevance_score} />
                </div>
                <SkillDots skills={user.matched_skills} />
                <p className="mt-2 text-xs text-muted-foreground line-clamp-2">{user.reason}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Decomposed tasks */}
      {(tasks.length > 0 || decomposeState.done) && (
        <>
          <Separator className="my-8" />
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Decomposed Tasks</h2>
            <Button asChild variant="outline" size="sm">
              <Link href={`/tasks?crisis_id=${crisisId}`}>View on board →</Link>
            </Button>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {tasks.map((task) => (
              <Card key={task.id}>
                <CardContent className="p-4">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="font-medium leading-snug">{task.title}</p>
                    <StatusDot status={task.status} />
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-2">{task.description}</p>
                  <div className="mt-3">
                    <SkillDots skills={task.required_skills} />
                  </div>
                  {task.legal_review_needed && (
                    <div className="mt-2 flex items-center gap-1.5">
                      <LegalReviewFlag />
                      <span className="text-[10px] text-amber-600 dark:text-amber-400">Review</span>
                    </div>
                  )}
                  {(matchesByTaskId[task.id] ?? []).length > 0 && (
                    <div className="mt-3 space-y-1.5 border-t border-border/80 pt-3">
                      {matchesByTaskId[task.id].map((m) => (
                        <div key={m.id} className="flex items-center justify-between gap-2 text-xs">
                          <span className="truncate font-medium">{m.name}</span>
                          <RelevanceMeter score={Math.round(m.score * 10)} />
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function ActionButton({
  step,
  icon: Icon,
  label,
  state,
  disabled,
  onClick,
  onForce,
}: {
  step: number;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  state: ActionState;
  disabled?: boolean;
  onClick: () => void;
  onForce: () => void;
}) {
  const stepColor = state.error
    ? "border-l-destructive"
    : state.loading
      ? "border-l-blue-500"
      : state.done
        ? "border-l-emerald-500"
        : "border-l-muted-foreground/30";

  return (
    <div className="space-y-1">
      <Button
        className={`w-full justify-start border-l-4 ${stepColor}`}
        variant={state.done ? "secondary" : "default"}
        disabled={disabled || state.loading}
        onClick={onClick}
      >
        {state.loading ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin text-blue-500" />
        ) : state.done ? (
          <CheckCircle2 className="mr-2 h-4 w-4 text-emerald-500" />
        ) : (
          <Icon className="mr-2 h-4 w-4" />
        )}
        {step}. {label}
        {state.cached && (
          <span className="ml-auto h-2 w-2 rounded-full bg-primary/60" title="Cached result" />
        )}
        {state.elapsed !== undefined && !state.cached && (
          <span className="ml-auto text-xs tabular-nums text-muted-foreground">{state.elapsed}s</span>
        )}
      </Button>
      {state.done && (
        <button
          onClick={onForce}
          className="text-xs text-muted-foreground transition-colors hover:text-primary"
          disabled={state.loading}
        >
          Run again
        </button>
      )}
      {state.error && <p className="text-xs text-destructive">{state.error}</p>}
    </div>
  );
}
