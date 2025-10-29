-- Link family members to declarants table to avoid person duplication
-- Version: 4.0
-- Created: 2025-10-29
--
-- Problem:
-- Family members can also be declarants themselves (e.g., both spouses are public officials).
-- Currently, the same person could exist in both declarants and family_members tables,
-- leading to data duplication and inconsistency.
--
-- Solution:
-- Add optional foreign key from family_members to declarants table.
-- When a family member is also a declarant, we link them instead of duplicating data.

-- Add optional reference to declarants table
ALTER TABLE family_members
    ADD COLUMN IF NOT EXISTS declarant_id UUID REFERENCES declarants(id) ON DELETE SET NULL;

-- Create index for the new foreign key
CREATE INDEX IF NOT EXISTS idx_family_members_declarant_id
    ON family_members(declarant_id);

-- Add comment explaining the relationship
COMMENT ON COLUMN family_members.declarant_id IS
    'Optional link to declarants table if this family member is also a declarant.
    Prevents person duplication when family members are public officials themselves.';

-- Migration note: Existing data needs to be updated to link family members to declarants
-- This requires a data migration script that:
-- 1. For each family_member, check if their tax_number exists in declarants
-- 2. If yes, set declarant_id to that declarant's id
-- 3. This can be done with:
--
-- UPDATE family_members fm
-- SET declarant_id = d.id
-- FROM declarants d
-- WHERE fm.tax_number IS NOT NULL
--   AND fm.tax_number != ''
--   AND fm.tax_number != '[Конфіденційна інформація]'
--   AND d.tax_number = fm.tax_number;
