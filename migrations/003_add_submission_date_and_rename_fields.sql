-- Add submission date and rename misleading date fields
-- Version: 3.0
-- Created: 2025-10-29
--
-- Problems:
-- 1. declaration_year_from and declaration_year_to are DATE types but names suggest they only store years
-- 2. Missing submitted_at field to track when declaration was actually submitted
-- 3. Declarations can be submitted multiple times per year - submission date is critical
--
-- Solutions:
-- 1. Rename declaration_year_from -> reporting_period_from
-- 2. Rename declaration_year_to -> reporting_period_to
-- 3. Add submitted_at TIMESTAMP field for actual submission date

-- Add the submitted_at column
ALTER TABLE declarations
    ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP;

COMMENT ON COLUMN declarations.submitted_at IS 'Date and time when the declaration was actually submitted (introDate from API)';

-- Rename the misleading columns
ALTER TABLE declarations
    RENAME COLUMN declaration_year_from TO reporting_period_from;

ALTER TABLE declarations
    RENAME COLUMN declaration_year_to TO reporting_period_to;

COMMENT ON COLUMN declarations.reporting_period_from IS 'Start date of the reporting period covered by this declaration';
COMMENT ON COLUMN declarations.reporting_period_to IS 'End date of the reporting period covered by this declaration';
COMMENT ON COLUMN declarations.declaration_year IS 'Year of the declaration (for filtering/grouping)';
