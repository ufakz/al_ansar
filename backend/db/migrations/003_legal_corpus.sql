-- Legal corpus metadata for LLM-grounded citation matching

ALTER TABLE legal_sources
  ADD COLUMN IF NOT EXISTS file_path TEXT,
  ADD COLUMN IF NOT EXISTS topic_tags TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS leverage_routes JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS slug TEXT;

ALTER TABLE legal_chunks
  ADD COLUMN IF NOT EXISTS article_ref TEXT,
  ADD COLUMN IF NOT EXISTS topic_tags TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS chunk_index INTEGER,
  ADD COLUMN IF NOT EXISTS token_count INTEGER;

CREATE UNIQUE INDEX IF NOT EXISTS idx_legal_sources_slug ON legal_sources(slug);
CREATE INDEX IF NOT EXISTS idx_legal_sources_jurisdiction ON legal_sources(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_legal_chunks_jurisdiction ON legal_chunks(source_id, chunk_index);
