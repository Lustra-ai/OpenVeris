-- Fix declarant uniqueness constraint
-- Version: 2.0
-- Created: 2025-10-29
--
-- Problem: The composite UNIQUE constraint on (tax_number, unzr) is incorrect.
-- Tax IDs should be unique independently, not as a composite key.
--
-- Solution: Drop the composite constraint and add individual UNIQUE constraints
-- on tax_number and unzr (when not null).

-- Drop the incorrect composite constraint
ALTER TABLE declarants DROP CONSTRAINT IF EXISTS declarants_tax_number_unzr_key;

-- Add individual UNIQUE constraints
-- tax_number should be unique when not null
CREATE UNIQUE INDEX idx_declarants_tax_number_unique
    ON declarants(tax_number)
    WHERE tax_number IS NOT NULL;

-- unzr should be unique when not null
CREATE UNIQUE INDEX idx_declarants_unzr_unique
    ON declarants(unzr)
    WHERE unzr IS NOT NULL;

-- Update the regular indexes (drop and recreate to avoid conflicts)
DROP INDEX IF EXISTS idx_declarants_tax_number;
DROP INDEX IF EXISTS idx_declarants_unzr;

-- These are now covered by the unique indexes above, so no need to recreate them

COMMENT ON INDEX idx_declarants_tax_number_unique IS 'Ensures tax_number is unique when present';
COMMENT ON INDEX idx_declarants_unzr_unique IS 'Ensures unzr is unique when present';
