-- Al-Ansar shared schema (hackathon contract)

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS vector;

-- Person 1: crisis ingestion
CREATE TABLE crisis_objects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    summary TEXT,
    type TEXT,
    country_iso VARCHAR(3),
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    severity INTEGER CHECK (severity BETWEEN 1 AND 5),
    urgency TEXT,
    tags TEXT[] DEFAULT '{}',
    raw_gdelt_id TEXT,
    source TEXT NOT NULL DEFAULT 'gdelt',
    source_report_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Community-submitted incident reports (intake before promotion to crisis_objects)
CREATE TABLE crisis_reports (
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

CREATE TABLE report_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES crisis_reports(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL,
    file_url TEXT,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE crisis_objects
    ADD CONSTRAINT fk_crisis_source_report
    FOREIGN KEY (source_report_id) REFERENCES crisis_reports(id) ON DELETE SET NULL;

-- Person 2: legal corpus + grounding
CREATE TABLE legal_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    jurisdiction TEXT,
    source_type TEXT,
    url TEXT,
    celex_or_ref TEXT,
    slug TEXT UNIQUE,
    file_path TEXT,
    topic_tags TEXT[] DEFAULT '{}',
    leverage_routes JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE legal_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES legal_sources(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    article_ref TEXT,
    topic_tags TEXT[] DEFAULT '{}',
    chunk_index INTEGER,
    token_count INTEGER,
    embedding vector(1024),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE grounding_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crisis_id UUID NOT NULL REFERENCES crisis_objects(id) ON DELETE CASCADE,
    has_legal_support BOOLEAN NOT NULL DEFAULT FALSE,
    summary TEXT,
    citations JSONB DEFAULT '[]'::jsonb,
    leverage_routes JSONB DEFAULT '[]'::jsonb,
    matched_users JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Joint: tasks, Ansar helpers, matching, notifications
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crisis_id UUID NOT NULL REFERENCES crisis_objects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    required_skills TEXT[] DEFAULT '{}',
    task_type TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    legal_review_needed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ansar_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    skills TEXT[] DEFAULT '{}',
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    languages TEXT[] DEFAULT '{}',
    trust_tier TEXT NOT NULL DEFAULT 'unverified',
    capacity INTEGER NOT NULL DEFAULT 1,
    telegram_chat_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    ansar_id UUID NOT NULL REFERENCES ansar_users(id) ON DELETE CASCADE,
    score DOUBLE PRECISION,
    rank INTEGER,
    notified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    channel TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    payload JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_crisis_objects_country ON crisis_objects(country_iso);
CREATE INDEX idx_crisis_objects_source ON crisis_objects(source);
CREATE INDEX idx_crisis_reports_status ON crisis_reports(status);
CREATE INDEX idx_crisis_reports_country ON crisis_reports(country_iso);
CREATE INDEX idx_report_evidence_report ON report_evidence(report_id);
CREATE INDEX idx_legal_sources_jurisdiction ON legal_sources(jurisdiction);
CREATE INDEX idx_legal_chunks_source ON legal_chunks(source_id);
CREATE INDEX idx_legal_chunks_source_index ON legal_chunks(source_id, chunk_index);
CREATE INDEX idx_grounding_crisis ON grounding_results(crisis_id);
CREATE INDEX idx_tasks_crisis ON tasks(crisis_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_matches_task ON matches(task_id);
