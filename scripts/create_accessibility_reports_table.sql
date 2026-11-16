-- Schema for Accessibility Feedback Reports (Iteration 3, Epic 6)
-- Tracks community-submitted accessibility barrier reports to Victorian councils.

CREATE TABLE IF NOT EXISTS accessibility_reports (
    id SERIAL PRIMARY KEY,
    reference_id VARCHAR(50) UNIQUE NOT NULL,
    space_type VARCHAR(20) DEFAULT 'public',
    council_name TEXT NOT NULL,
    council_email TEXT NOT NULL,
    sender_name TEXT NOT NULL,
    sender_email TEXT,
    location_name TEXT NOT NULL,
    barrier_summary JSONB NOT NULL,
    email_subject TEXT NOT NULL,
    email_body TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'SENT',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_accessibility_reports_council 
ON accessibility_reports (council_name);

CREATE INDEX IF NOT EXISTS idx_accessibility_reports_created 
ON accessibility_reports (created_at DESC);
