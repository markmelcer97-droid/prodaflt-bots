-- ============================================================
-- PRODAFLT Migration 001: Core Tables
-- Creates: links, content_analysis, tz_specs, patterns,
--          campaign_metrics, alerts_log, users
-- ============================================================

-- ============================================================
-- 1. ENUM TYPES (idempotent via DO blocks)
-- ============================================================

DO $$ BEGIN
    CREATE TYPE link_status AS ENUM (
        'pending', 'processing', 'analyzed', 'failed', 'archived'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE compliance_status AS ENUM (
        'pending', 'compliant', 'non_compliant', 'flagged'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE tz_spec_status AS ENUM (
        'draft', 'in_review', 'approved', 'rejected', 'archived'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE campaign_status AS ENUM (
        'active', 'paused', 'completed', 'archived'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE alert_type AS ENUM (
        'roi_drop', 'cpi_spike', 'install_drop', 'deposit_drop', 'anomaly'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE alert_status AS ENUM (
        'new', 'acknowledged', 'resolved', 'dismissed'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM (
        'admin', 'user', 'viewer'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- 2. USERS TABLE (created first -- referenced by other tables)
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    telegram_id BIGINT UNIQUE,
    username VARCHAR(100) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    role user_role NOT NULL DEFAULT 'user',
    team_role VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 3. LINKS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS links (
    link_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    url VARCHAR(2048) NOT NULL,
    platform VARCHAR(100),
    title VARCHAR(500),
    description TEXT,
    duration INT,
    status link_status NOT NULL DEFAULT 'pending',
    added_by INT,
    added_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    preview_url VARCHAR(2048),
    metadata JSONB,
    CONSTRAINT fk_links_added_by
        FOREIGN KEY (added_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================================
-- 4. CONTENT ANALYSIS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS content_analysis (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    link_id INT NOT NULL,
    pattern VARCHAR(255),
    researcher_comment TEXT,
    compliance_status compliance_status NOT NULL DEFAULT 'pending',
    compliance_comment TEXT,
    creative_potential INT CHECK (creative_potential BETWEEN 1 AND 10),
    assigned_code VARCHAR(100),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_content_analysis_link_id
        FOREIGN KEY (link_id) REFERENCES links(link_id) ON DELETE CASCADE
);

-- ============================================================
-- 5. TZ SPECS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS tz_specs (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code_content VARCHAR(255) UNIQUE NOT NULL,
    title VARCHAR(500),
    description TEXT,
    script JSONB,
    visual_refs JSONB,
    target_audience VARCHAR(255),
    platform VARCHAR(100),
    status tz_spec_status NOT NULL DEFAULT 'draft',
    created_by INT,
    assigned_to INT,
    asana_task_id VARCHAR(100),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_tz_specs_created_by
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_tz_specs_assigned_to
        FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================================
-- 6. PATTERNS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS patterns (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    examples JSONB,
    frequency INT,
    week_of DATE,
    metrics JSONB,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 7. CAMPAIGN METRICS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS campaign_metrics (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    creative_code VARCHAR(100) NOT NULL,
    spend NUMERIC(12,2),
    clicks INT,
    installs INT,
    deposits INT,
    cpc NUMERIC(10,4),
    cpi NUMERIC(10,4),
    uepc NUMERIC(10,4),
    roi NUMERIC(10,4),
    revenue NUMERIC(12,2),
    status campaign_status NOT NULL DEFAULT 'active',
    recorded_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 8. ALERTS LOG TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS alerts_log (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id INT,
    alert_type alert_type NOT NULL,
    flag VARCHAR(100),
    triggered_metrics JSONB,
    confidence NUMERIC(5,2) CHECK (confidence BETWEEN 0 AND 100),
    decision VARCHAR(255),
    reason TEXT,
    sent_to VARCHAR(255),
    sent_at TIMESTAMP WITHOUT TIME ZONE,
    status alert_status NOT NULL DEFAULT 'new',
    CONSTRAINT fk_alerts_log_campaign_id
        FOREIGN KEY (campaign_id) REFERENCES campaign_metrics(id) ON DELETE CASCADE
);

-- ============================================================
-- 9. INDEXES
-- ============================================================

-- links indexes
CREATE INDEX IF NOT EXISTS idx_links_platform ON links(platform);
CREATE INDEX IF NOT EXISTS idx_links_status ON links(status);
CREATE INDEX IF NOT EXISTS idx_links_added_by ON links(added_by);
CREATE INDEX IF NOT EXISTS idx_links_added_at ON links(added_at DESC);

-- content_analysis indexes
CREATE INDEX IF NOT EXISTS idx_content_analysis_link_id ON content_analysis(link_id);
CREATE INDEX IF NOT EXISTS idx_content_analysis_compliance_status ON content_analysis(compliance_status);
CREATE INDEX IF NOT EXISTS idx_content_analysis_assigned_code ON content_analysis(assigned_code);

-- tz_specs indexes
CREATE INDEX IF NOT EXISTS idx_tz_specs_status ON tz_specs(status);
CREATE INDEX IF NOT EXISTS idx_tz_specs_assigned_to ON tz_specs(assigned_to);
CREATE INDEX IF NOT EXISTS idx_tz_specs_platform ON tz_specs(platform);

-- patterns indexes
CREATE INDEX IF NOT EXISTS idx_patterns_name ON patterns(name);
CREATE INDEX IF NOT EXISTS idx_patterns_week_of ON patterns(week_of);

-- campaign_metrics indexes
CREATE INDEX IF NOT EXISTS idx_campaign_metrics_creative_code ON campaign_metrics(creative_code);
CREATE INDEX IF NOT EXISTS idx_campaign_metrics_status ON campaign_metrics(status);
CREATE INDEX IF NOT EXISTS idx_campaign_metrics_recorded_at ON campaign_metrics(recorded_at DESC);

-- alerts_log indexes
CREATE INDEX IF NOT EXISTS idx_alerts_log_campaign_id ON alerts_log(campaign_id);
CREATE INDEX IF NOT EXISTS idx_alerts_log_alert_type ON alerts_log(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_log_status ON alerts_log(status);
CREATE INDEX IF NOT EXISTS idx_alerts_log_sent_at ON alerts_log(sent_at DESC);

-- users indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- ============================================================
-- 10. SEED DATA -- Users
-- ============================================================

INSERT INTO users (username, role, team_role, is_active) VALUES
    ('durovscales', 'admin', 'TeamLead', true),
    ('chernov_1', 'user', 'Bayer', true),
    ('only1showbizschool', 'user', 'Design', true),
    ('danilorrel', 'user', 'Bayer', true),
    ('gfftra', 'user', 'Bayer', true),
    ('mitrafq', 'user', 'Design', true),
    ('Nepenthese', 'user', 'Design', true)
ON CONFLICT (username) DO NOTHING;
