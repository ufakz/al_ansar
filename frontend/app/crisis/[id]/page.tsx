import { fetchApi, type Crisis, type Grounding, type Task, type TaskMatchGroup } from "@/lib/api";
import { CrisisCommandCenter } from "@/components/CrisisCommandCenter";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState } from "@/components/States";

export default async function CrisisPage({ params }: { params: { id: string } }) {
  try {
    const crisis = await fetchApi<Crisis>(`/dashboard/crises/${params.id}`);

    let grounding: Grounding | null = null;
    try {
      grounding = await fetchApi<Grounding>(`/dashboard/grounding/${params.id}`);
    } catch {
      grounding = null;
    }

    let tasks: Task[] = [];
    try {
      const res = await fetchApi<{ tasks: Task[] }>(`/dashboard/tasks?crisis_id=${params.id}`);
      tasks = res.tasks;
    } catch {
      tasks = [];
    }

    let taskMatches: TaskMatchGroup[] = [];
    try {
      const res = await fetchApi<{ tasks: TaskMatchGroup[] }>(
        `/dashboard/matches?crisis_id=${params.id}`
      );
      taskMatches = res.tasks;
    } catch {
      taskMatches = [];
    }

    return (
      <CrisisCommandCenter
        crisis={crisis}
        initialGrounding={grounding}
        initialTasks={tasks}
        initialTaskMatches={taskMatches}
      />
    );
  } catch (e) {
    return (
      <div>
        <PageHeader title="Crisis not found" />
        <ErrorState message={String(e)} />
      </div>
    );
  }
}
