import { fetchApi, type AnsarUser } from "@/lib/api";
import { PageHeader, TrustBadge } from "@/components/PageHeader";
import { SkillDots } from "@/components/VisualIndicators";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorState } from "@/components/States";

export default async function AnsarPage() {
  try {
    const { ansar } = await fetchApi<{ ansar: AnsarUser[] }>("/dashboard/ansar");

    return (
      <div>
        <PageHeader
          title="Ansar Helpers"
          description={`${ansar.length} verified and community helpers across Finland, EU, and crisis regions`}
        />

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {ansar.map((user) => (
            <Card key={user.id}>
              <CardContent className="p-5">
                <div className="mb-3 flex items-start justify-between">
                  <div>
                    <p className="font-semibold">{user.name}</p>
                    <p className="text-xs text-muted-foreground">
                      Capacity: {user.capacity}
                    </p>
                  </div>
                  <TrustBadge tier={user.trust_tier} />
                </div>
                <div className="mb-3">
                  <SkillDots skills={user.skills} max={6} />
                </div>
                {user.languages.length > 0 && (
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                    {user.languages.join(" · ")}
                  </p>
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
        <PageHeader title="Ansar Helpers" />
        <ErrorState message={String(e)} />
      </div>
    );
  }
}
