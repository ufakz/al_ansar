"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { API_URL } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorState } from "@/components/States";

export default function ReportForm() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const form = new FormData(e.currentTarget);
    const tags = (form.get("tags") as string)
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    const payload = {
      narrative: form.get("narrative") as string,
      incident_at: form.get("incident_at")
        ? new Date(form.get("incident_at") as string).toISOString()
        : null,
      location_text: (form.get("location_text") as string) || null,
      country_iso: (form.get("country_iso") as string) || "FIN",
      type: (form.get("type") as string) || "persecution",
      tags,
      is_anonymous: form.get("is_anonymous") === "on",
      preferred_language: (form.get("preferred_language") as string) || "en",
      reporter_name: (form.get("reporter_name") as string) || null,
      reporter_email: (form.get("reporter_email") as string) || null,
      evidence: (form.get("evidence_url") as string)
        ? [{
            evidence_type: "url",
            file_url: form.get("evidence_url") as string,
            description: (form.get("evidence_desc") as string) || null,
          }]
        : [],
    };

    try {
      const res = await fetch(`${API_URL}/reports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail?.[0]?.msg ?? "Failed to submit report");
      }
      router.push("/reports");
      router.refresh();
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Report an incident"
        description="Community reports are grounded against EU and Finnish law before Ansar matching."
      />

      {error && <div className="mb-4"><ErrorState message={error} /></div>}

      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="mb-1.5 block text-sm font-medium">What happened? *</label>
              <Textarea name="narrative" required rows={5} placeholder="Describe the incident..." />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-sm font-medium">When</label>
                <Input name="incident_at" type="datetime-local" />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">Location</label>
                <Input name="location_text" placeholder="e.g. Kamppi, Helsinki" />
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label className="mb-1.5 block text-sm font-medium">Country</label>
                <Input name="country_iso" defaultValue="FIN" />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">Type</label>
                <Input name="type" defaultValue="persecution" />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">Language</label>
                <Input name="preferred_language" defaultValue="en" />
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">Tags (comma-separated)</label>
              <Input name="tags" placeholder="hijab, workplace, discrimination" />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-sm font-medium">Evidence URL</label>
                <Input name="evidence_url" type="url" placeholder="https://..." />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">Evidence description</label>
                <Input name="evidence_desc" />
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-sm font-medium">Your name</label>
                <Input name="reporter_name" />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">Email</label>
                <Input name="reporter_email" type="email" />
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" name="is_anonymous" defaultChecked className="rounded" />
              Submit anonymously
            </label>
            <Button type="submit" disabled={loading}>
              {loading ? "Submitting…" : "Submit report"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
