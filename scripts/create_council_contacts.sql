-- Schema for Victorian Council Contacts (Iteration 3)
-- Source: data/victorian_council_contacts_2026_cleaned (1).csv

CREATE TABLE IF NOT EXISTS council_contacts (
    council_name TEXT PRIMARY KEY,
    ceo_name TEXT NOT NULL,
    mayor_name TEXT,
    deputy_mayor_name TEXT,
    telephone TEXT NOT NULL,
    email TEXT,
    website TEXT NOT NULL,
    postal_address TEXT NOT NULL,
    postal_suburb TEXT NOT NULL,
    postcode VARCHAR(10) NOT NULL
);

-- Index for case-insensitive lookup
CREATE INDEX IF NOT EXISTS idx_council_contacts_name_lower 
ON council_contacts (LOWER(council_name));

-- Views for backwards / alternative table naming compatibility
CREATE OR REPLACE VIEW victorian_council_contacts_2026_cleaned AS 
SELECT * FROM council_contacts;

CREATE OR REPLACE VIEW victorian_council_contacts AS 
SELECT * FROM council_contacts;
