-- D1 schema. Create once:
--   npx wrangler d1 create findwell
--   npx wrangler d1 execute findwell --remote --file=schema.sql
CREATE TABLE IF NOT EXISTS submissions (
  id          TEXT PRIMARY KEY,
  created_at  TEXT NOT NULL,
  decided_at  TEXT,
  status      TEXT NOT NULL DEFAULT 'pending',   -- pending | approved | declined
  payload     TEXT NOT NULL                      -- the full submission as JSON
);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions (status, created_at DESC);
