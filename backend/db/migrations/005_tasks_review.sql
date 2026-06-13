-- Task decomposition metadata

ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS legal_review_needed BOOLEAN NOT NULL DEFAULT FALSE;
