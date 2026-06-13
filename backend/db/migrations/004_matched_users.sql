-- Ansar user matching results stored on grounding_results

ALTER TABLE grounding_results
    ADD COLUMN IF NOT EXISTS matched_users JSONB DEFAULT '[]'::jsonb;
