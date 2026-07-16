-- ============================================================
-- PRODAFLT Migration 002: Agents Table (Soul Prompt Versioning)
-- Creates: agents table for soul prompt tracking
-- Depends: Migration 001 (core tables)
-- ============================================================

CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    agent_key VARCHAR(50) UNIQUE NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    role VARCHAR(100),
    soul_version VARCHAR(20),
    soul_content TEXT,
    heartbeat VARCHAR(100),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_agents_key ON agents(agent_key);
CREATE INDEX IF NOT EXISTS idx_agents_version ON agents(soul_version);

-- Seed: insert placeholder rows for all 7 agents
-- These will be populated by the soul-prompts-text component sync
INSERT INTO agents (agent_key, agent_name, role, heartbeat, soul_version)
VALUES
    ('router', 'Router', 'Dispatcher', 'daily 09:17', '1.0.0'),
    ('researcher', 'Researcher', 'Content Researcher', 'daily 10:00', '1.0.0'),
    ('compliance', 'Compliance', 'Compliance Officer', 'Tue,Thu 12:00', '1.0.0'),
    ('creative', 'Creative', 'Creative Producer', 'Mon 09:00', '1.0.0'),
    ('meta_master', 'Meta Master', 'Meta Ads Expert', 'Mon 10:00', '1.0.0'),
    ('data_analyst', 'Data Analyst', 'Data Analyst', 'daily 07:00,18:00', '1.0.0'),
    ('tech_lead', 'Tech Lead', 'Tech Lead', 'Fri 18:00', '1.0.0')
ON CONFLICT (agent_key) DO NOTHING;
