-- Migration: community crisis reports (apply to existing DB)

ALTER TABLE crisis_objects
    ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'gdelt',
    ADD COLUMN IF NOT EXISTS source_report_id UUID;

CREATE TABLE IF NOT EXISTS crisis_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    narrative TEXT NOT NULL,
    incident_at TIMESTAMPTZ,
    location_text TEXT,
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    country_iso VARCHAR(3) NOT NULL DEFAULT 'FIN',
    type TEXT,
    tags TEXT[] DEFAULT '{}',
    reporter_name TEXT,
    reporter_email TEXT,
    reporter_phone TEXT,
    is_anonymous BOOLEAN NOT NULL DEFAULT TRUE,
    preferred_language TEXT DEFAULT 'en',
    status TEXT NOT NULL DEFAULT 'pending',
    promoted_crisis_id UUID REFERENCES crisis_objects(id) ON DELETE SET NULL,
    triage_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS report_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES crisis_reports(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL,
    file_url TEXT,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_crisis_source_report'
    ) THEN
        ALTER TABLE crisis_objects
            ADD CONSTRAINT fk_crisis_source_report
            FOREIGN KEY (source_report_id) REFERENCES crisis_reports(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_crisis_objects_source ON crisis_objects(source);
CREATE INDEX IF NOT EXISTS idx_crisis_reports_status ON crisis_reports(status);
CREATE INDEX IF NOT EXISTS idx_crisis_reports_country ON crisis_reports(country_iso);
CREATE INDEX IF NOT EXISTS idx_report_evidence_report ON report_evidence(report_id);
