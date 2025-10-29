# Database Migrations

This directory contains SQL migration files for the OpenVeris database schema.

## Applying Migrations

Migrations should be applied in order:

```bash
# Connect to PostgreSQL
psql -h localhost -U openveris -d openveris

# Apply migrations in order
\i migrations/001_initial_schema.sql
\i migrations/002_fix_declarant_uniqueness.sql
\i migrations/003_add_submission_date_and_rename_fields.sql
\i migrations/004_link_family_members_to_declarants.sql
```

Or using environment variables from .env:

```bash
source .env
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -f migrations/001_initial_schema.sql
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -f migrations/002_fix_declarant_uniqueness.sql
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -f migrations/003_add_submission_date_and_rename_fields.sql
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -f migrations/004_link_family_members_to_declarants.sql
```

## Migration History

| # | File | Description | Date |
|---|------|-------------|------|
| 001 | `001_initial_schema.sql` | Initial database schema with all tables | 2025-10-28 |
| 002 | `002_fix_declarant_uniqueness.sql` | Fix declarant uniqueness constraints (tax_number and unzr should be individually unique) | 2025-10-29 |
| 003 | `003_add_submission_date_and_rename_fields.sql` | Add submitted_at field and rename declaration_year_from/to to reporting_period_from/to | 2025-10-29 |
| 004 | `004_link_family_members_to_declarants.sql` | Add declarant_id FK to family_members to prevent person duplication when family members are also declarants | 2025-10-29 |

## Notes

- **Always backup your database before applying migrations**
- Migrations are designed to be idempotent where possible (using `IF EXISTS`, `IF NOT EXISTS`)
- Migration 002 fixes the composite UNIQUE constraint bug that allowed duplicate tax_numbers
- Migration 003 adds submission tracking and clarifies field names (declarations can be submitted multiple times per year)
- Migration 004 prevents person duplication when family members are also public officials (declarants)
