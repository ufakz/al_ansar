import { fetchApi, type LegalSource, type LegalChunk } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ErrorState } from "@/components/States";

export default async function LegalPage() {
  try {
    const [{ sources }, { chunks }] = await Promise.all([
      fetchApi<{ sources: LegalSource[] }>("/legal/sources"),
      fetchApi<{ chunks: LegalChunk[] }>("/legal/chunks?include_text=true"),
    ]);

    const byJurisdiction = sources.reduce<Record<string, LegalSource[]>>((acc, s) => {
      const j = s.jurisdiction ?? "Other";
      (acc[j] ??= []).push(s);
      return acc;
    }, {});

    return (
      <div>
        <PageHeader
          title="Legal Corpus"
          description={`${sources.length} sources, ${chunks.length} chunks — EU, Finland, ECHR, evidence`}
        />

        <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(byJurisdiction).map(([jur, items]) => (
            <Card key={jur}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">{jur}</CardTitle>
                <CardDescription>{items.length} sources</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">
                  {items.reduce((n, s) => n + s.chunk_count, 0)}
                </p>
                <p className="text-xs text-muted-foreground">chunks</p>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="space-y-6">
          {sources.map((source) => {
            const sourceChunks = chunks.filter((c) => c.source_id === source.id);
            return (
              <Card key={source.id}>
                <CardHeader>
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <CardTitle className="text-base">{source.title}</CardTitle>
                      <CardDescription className="mt-1">
                        {source.jurisdiction} · {source.chunk_count} chunks
                        {source.url && (
                          <> · <a href={source.url} target="_blank" rel="noreferrer" className="text-primary hover:underline">source</a></>
                        )}
                      </CardDescription>
                    </div>
                    <Badge variant="secondary">{source.jurisdiction}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {sourceChunks.slice(0, 5).map((chunk) => (
                    <div key={chunk.id} className="rounded-md border border-border p-3">
                      {chunk.article_ref && (
                        <p className="mb-1 text-xs font-medium text-primary">{chunk.article_ref}</p>
                      )}
                      <p className="line-clamp-3 text-sm text-muted-foreground">
                        {chunk.chunk_text}
                      </p>
                    </div>
                  ))}
                  {sourceChunks.length > 5 && (
                    <p className="text-xs text-muted-foreground">+ {sourceChunks.length - 5} more chunks</p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    );
  } catch (e) {
    return (
      <div>
        <PageHeader title="Legal Corpus" />
        <ErrorState message={String(e)} />
      </div>
    );
  }
}
