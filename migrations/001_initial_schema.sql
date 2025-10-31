-- OpenVeris NAZK Declarations Database Schema
-- Version: 1.0 (Consolidated Initial Migration)
-- Created: 2025-10-28
--
-- This is the complete schema for storing Ukrainian NAZK (National Agency on Corruption Prevention)
-- declarations data, including declarants, their declarations, family members, and all associated assets.
--
-- Key features:
-- - Full normalization with declarants separate from declarations (one person, multiple declarations)
-- - Support for both declarant and family member asset ownership
-- - Comprehensive asset tracking (real estate, vehicles, securities, corporate rights, etc.)
-- - Financial information (income, expenses, liabilities)
-- - Work history and organizational memberships
-- - VARCHAR(255) for ownership_type and descriptive fields to accommodate Ukrainian legal terminology

-- =============================================================================
-- EXTENSIONS
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;
COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';

-- =============================================================================
-- CORE TABLES: Declarants and Declarations
-- =============================================================================

-- Declarants: Unique persons who file declarations (normalized by tax_number or unzr)
CREATE TABLE declarants (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tax_number          VARCHAR(50),
    unzr                VARCHAR(50),
    lastname            VARCHAR(255) NOT NULL,
    firstname           VARCHAR(255) NOT NULL,
    middlename          VARCHAR(255),
    changed_name        BOOLEAN DEFAULT FALSE,
    previous_names      JSONB,
    birth_year          INTEGER,
    full_name_key       VARCHAR(1000) GENERATED ALWAYS AS (
        UPPER(TRIM(lastname || ' ' || firstname || ' ' || COALESCE(middlename, '')))
    ) STORED,
    first_seen_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    last_updated_at     TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT declarants_tax_number_unzr_key UNIQUE (tax_number, unzr)
);

COMMENT ON TABLE declarants IS 'Unique persons who file declarations';

-- Indexes for declarant lookups
CREATE INDEX idx_declarants_tax_number ON declarants(tax_number);
CREATE INDEX idx_declarants_unzr ON declarants(unzr);
CREATE INDEX idx_declarants_lastname ON declarants(lastname);
CREATE INDEX idx_declarants_full_name ON declarants(full_name_key);

-- Declarations: Annual or termination declarations filed by declarants
CREATE TABLE declarations (
    id                              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    declarant_id                    UUID NOT NULL REFERENCES declarants(id) ON DELETE CASCADE,
    document_id                     VARCHAR(255) NOT NULL UNIQUE,
    declaration_type                INTEGER,
    declaration_year                INTEGER,
    declaration_year_from           DATE,
    declaration_year_to             DATE,

    -- Work information
    work_place                      TEXT,
    work_place_edrpou               VARCHAR(50),
    work_post                       TEXT,
    post_type                       VARCHAR(255),
    post_category                   VARCHAR(50),
    responsible_position            BOOLEAN DEFAULT FALSE,
    public_person                   BOOLEAN DEFAULT FALSE,
    corruption_affected             BOOLEAN DEFAULT FALSE,
    continue_perform_functions      INTEGER,

    -- Address information
    country_id                      INTEGER,
    region                          VARCHAR(255),
    region_path                     TEXT,
    district                        VARCHAR(255),
    district_path                   TEXT,
    community                       VARCHAR(255),
    community_path                  TEXT,
    city                            VARCHAR(255),
    city_path                       TEXT,
    city_type                       VARCHAR(100),
    street_type                     VARCHAR(100),
    street                          VARCHAR(255),
    house_num                       VARCHAR(50),
    house_part_num                  VARCHAR(50),
    apartments_num                  VARCHAR(50),
    post_code                       VARCHAR(20),
    same_reg_living_address         BOOLEAN,

    -- Metadata
    raw_data                        JSONB NOT NULL,
    submission_date                 TIMESTAMP,
    scraped_at                      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE declarations IS 'Annual or termination declarations filed by declarants';
COMMENT ON COLUMN declarations.document_id IS 'Unique declaration document ID (primary unique identifier - a declarant may have multiple declarations per year)';
COMMENT ON COLUMN declarations.declaration_type IS 'Type of declaration (nullable - may be missing in older or incomplete declarations)';
COMMENT ON COLUMN declarations.declaration_year IS 'Year of declaration (nullable - may be missing in older or incomplete declarations)';
COMMENT ON COLUMN declarations.post_category IS 'Post category (A, B, V, etc.) - increased to VARCHAR(50) for longer values';

-- Indexes for declaration lookups
CREATE INDEX idx_declarations_declarant ON declarations(declarant_id);
CREATE INDEX idx_declarations_document_id ON declarations(document_id);
CREATE INDEX idx_declarations_year ON declarations(declaration_year);
CREATE INDEX idx_declarations_type ON declarations(declaration_type);
CREATE INDEX idx_declarations_scraped_at ON declarations(scraped_at);

-- Family Members: Spouse, children, and other family members listed in declarations
CREATE TABLE family_members (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    declaration_id      UUID NOT NULL REFERENCES declarations(id) ON DELETE CASCADE,
    declarant_id        UUID REFERENCES declarants(id),
    lastname            VARCHAR(255),
    firstname           VARCHAR(255),
    middlename          VARCHAR(255),
    tax_number          VARCHAR(50),
    unzr                VARCHAR(50),
    passport            VARCHAR(100),
    birth_year          INTEGER,
    subject_relation    VARCHAR(255),

    -- Address information
    country_id          INTEGER,
    region              VARCHAR(255),
    district            VARCHAR(255),
    community           VARCHAR(255),
    city                VARCHAR(255),
    city_type           VARCHAR(100),
    street              VARCHAR(255),
    house_num           VARCHAR(50),
    apartments_num      VARCHAR(50),
    post_code           VARCHAR(20),
    citizenship         INTEGER,

    raw_data            JSONB,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE family_members IS 'Family members listed in declarations (spouse, children)';
COMMENT ON COLUMN family_members.lastname IS 'Last name (nullable - may be withheld by family member)';
COMMENT ON COLUMN family_members.firstname IS 'First name (nullable - may be withheld by family member)';
COMMENT ON COLUMN family_members.subject_relation IS 'Relationship to declarant (nullable - may be withheld)';

-- Indexes for family member lookups
CREATE INDEX idx_family_members_declaration ON family_members(declaration_id);
CREATE INDEX idx_family_members_declarant ON family_members(declarant_id);
CREATE INDEX idx_family_members_relation ON family_members(subject_relation);

-- =============================================================================
-- ASSET TABLES
-- =============================================================================

-- Real Estate: Land, apartments, houses, commercial property
CREATE TABLE real_estate (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    declaration_id          UUID NOT NULL REFERENCES declarations(id) ON DELETE CASCADE,
    owner_type              VARCHAR(50) NOT NULL,
    family_member_id        UUID REFERENCES family_members(id),

    -- Property details
    object_type             VARCHAR(255) NOT NULL,
    total_area              NUMERIC(12,2),
    ownership_type          VARCHAR(255),
    ownership_date          DATE,
    rights                  JSONB,

    -- Location
    country_id              INTEGER,
    region                  VARCHAR(255),
    district                VARCHAR(255),
    community               VARCHAR(255),
    city                    VARCHAR(255),
    city_type               VARCHAR(100),
    street                  VARCHAR(255),
    house_num               VARCHAR(50),
    apartments_num          VARCHAR(50),
    post_code               VARCHAR(20),

    -- Valuation
    cost_at_acquisition     NUMERIC(15,2),
    cost_currency           VARCHAR(50) DEFAULT 'UAH',
    cost_type               VARCHAR(255),
    reg_number              VARCHAR(255),

    raw_data                JSONB,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE real_estate IS 'Real estate properties owned';

-- Indexes for real estate lookups
CREATE INDEX idx_real_estate_declaration ON real_estate(declaration_id);
CREATE INDEX idx_real_estate_family_member ON real_estate(family_member_id);
CREATE INDEX idx_real_estate_owner_type ON real_estate(owner_type);
CREATE INDEX idx_real_estate_object_type ON real_estate(object_type);

-- Vehicles: Cars, motorcycles, boats, aircraft
CREATE TABLE vehicles (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    declaration_id          UUID NOT NULL REFERENCES declarations(id) ON DELETE CASCADE,
    owner_type              VARCHAR(50) NOT NULL,
    family_member_id        UUID REFERENCES family_members(id),

    -- Vehicle details
    object_type             VARCHAR(255) NOT NULL,
    brand                   VARCHAR(255),
    model                   VARCHAR(255),
    year                    INTEGER,
    ownership_type          VARCHAR(255),
    ownership_date          DATE,
    rights                  JSONB,

    -- Valuation
    cost_at_acquisition     NUMERIC(15,2),
    cost_currency           VARCHAR(50) DEFAULT 'UAH',
    reg_number              VARCHAR(100),

    raw_data                JSONB,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE vehicles IS 'Vehicles owned (cars, motorcycles, etc.)';

-- Indexes for vehicle lookups
CREATE INDEX idx_vehicles_declaration ON vehicles(declaration_id);
CREATE INDEX idx_vehicles_family_member ON vehicles(family_member_id);
CREATE INDEX idx_vehicles_owner_type ON vehicles(owner_type);

-- Bank Accounts: Savings, deposits, checking accounts
CREATE TABLE bank_accounts (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    declaration_id          UUID NOT NULL REFERENCES declarations(id) ON DELETE CASCADE,
    owner_type              VARCHAR(50) NOT NULL,
    family_member_id        UUID REFERENCES family_members(id),

    -- Account details
    bank_name               VARCHAR(500),
    bank_code               VARCHAR(50),
    account_type            VARCHAR(255),
    currency                VARCHAR(50),
    balance_at_start        NUMERIC(15,2),
    balance_at_end          NUMERIC(15,2),
    interest_received       NUMERIC(15,2),
    ownership_type          VARCHAR(255),
    opening_date            DATE,
    rights                  JSONB,

    raw_data                JSONB,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE bank_accounts IS 'Bank accounts and deposits';

-- Indexes for bank account lookups
CREATE INDEX idx_bank_accounts_declaration ON bank_accounts(declaration_id);
CREATE INDEX idx_bank_accounts_family_member ON bank_accounts(family_member_id);
CREATE INDEX idx_bank_accounts_owner_type ON bank_accounts(owner_type);

-- Corporate Rights: Business ownership, shares in companies
CREATE TABLE corporate_rights (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    declaration_id          UUID NOT NULL REFERENCES declarations(id) ON DELETE CASCADE,
    owner_type              VARCHAR(50) NOT NULL,
    family_member_id        UUID REFERENCES family_members(id),

    -- Company details
    company_name            VARCHAR(500) NOT NULL,
    company_edrpou          VARCHAR(50),
    company_address         TEXT,
    ownership_percent       NUMERIC(5,2),
    nominal_value           NUMERIC(15,2),
    total_value             NUMERIC(15,2),
    cost_currency           VARCHAR(50) DEFAULT 'UAH',
    ownership_type          VARCHAR(255),
    ownership_date          DATE,
    rights                  JSONB,

    raw_data                JSONB,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE corporate_rights IS 'Corporate ownership and business rights';

-- Indexes for corporate rights lookups
CREATE INDEX idx_corporate_rights_declaration ON corporate_rights(declaration_id);
CREATE INDEX idx_corporate_rights_family_member ON corporate_rights(family_member_id);
CREATE INDEX idx_corporate_rights_owner_type ON corporate_rights(owner_type);
CREATE INDEX idx_corporate_rights_company ON corporate_rights(company_edrpou);

-- Securities: Stocks, bonds, investment certificates
CREATE TABLE securities (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    declaration_id          UUID NOT NULL REFERENCES declarations(id) ON DELETE CASCADE,
    owner_type              VARCHAR(50) NOT NULL,
    family_member_id        UUID REFERENCES family_members(id),

    -- Security details
    security_type           VARCHAR(255) NOT NULL,
    issuer_name             VARCHAR(500),
    issuer_edrpou           VARCHAR(50),
    quantity                NUMERIC(15,4),
    nominal_value           NUMERIC(15,2),
    total_value             NUMERIC(15,2),
    cost_currency           VARCHAR(50) DEFAULT 'UAH',
    ownership_type          VARCHAR(255),
    ownership_date          DATE,
    rights                  JSONB,

    raw_data                JSONB,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE securities IS 'Securities owned (stocks, bonds, etc.)';

-- Indexes for securities lookups
CREATE INDEX idx_securities_declaration ON securities(declaration_id);
CREATE INDEX idx_securities_family_member ON securities(family_member_id);
CREATE INDEX idx_securities_owner_type ON securities(owner_type);

-- Valuables: Jewelry, art, precious metals
CREATE TABLE valuables (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    declaration_id          UUID NOT NULL REFERENCES declarations(id) ON DELETE CASCADE,
    owner_type              VARCHAR(50) NOT NULL,
    family_member_id        UUID REFERENCES family_members(id),

    -- Valuable details
    valuable_type           VARCHAR(255) NOT NULL,
    description             TEXT,
    total_value             NUMERIC(15,2),
    cost_currency           VARCHAR(10) DEFAULT 'UAH',
    ownership_type          VARCHAR(255),
    ownership_date          DATE,
    rights                  JSONB,

    raw_data                JSONB,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for valuables lookups
CREATE INDEX idx_valuables_declaration ON valuables(declaration_id);
CREATE INDEX idx_valuables_family_member ON valuables(family_member_id);
CREATE INDEX idx_valuables_owner_type ON valuables(owner_type);

-- Intangible Assets: Patents, trademarks, copyrights
CREATE TABLE intangible_assets (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    declaration_id          UUID NOT NULL REFERENCES declarations(id) ON DELETE CASCADE,
    owner_type              VARCHAR(50) NOT NULL,
    family_member_id        UUID REFERENCES family_members(id),

    -- Asset details
    asset_type              VARCHAR(255) NOT NULL,
    description             TEXT,
    total_value             NUMERIC(15,2),
    cost_currency           VARCHAR(50) DEFAULT 'UAH',
    ownership_type          VARCHAR(255),
    ownership_date          DATE,
    rights                  JSONB,
    reg_number              VARCHAR(255),

    raw_data                JSONB,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for intangible assets lookups
CREATE INDEX idx_intangible_assets_declaration ON intangible_assets(declaration_id);
CREATE INDEX idx_intangible_assets_family_member ON intangible_assets(family_member_id);
CREATE INDEX idx_intangible_assets_owner_type ON intangible_assets(owner_type);

-- =============================================================================
-- FINANCIAL TABLES
-- =============================================================================

-- Income Sources: Salary, business income, investments, gifts
CREATE TABLE income_sources (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    declaration_id          UUID NOT NULL REFERENCES declarations(id) ON DELETE CASCADE,
    owner_type              VARCHAR(50) NOT NULL,
    family_member_id        UUID REFERENCES family_members(id),

    -- Income details
    income_type             VARCHAR(255) NOT NULL,
    income_source           VARCHAR(500),
    source_edrpou           VARCHAR(50),
    amount                  NUMERIC(15,2),
    currency                VARCHAR(50) DEFAULT 'UAH',
    period_from             DATE,
    period_to               DATE,

    raw_data                JSONB,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE income_sources IS 'All sources of income';
COMMENT ON COLUMN income_sources.amount IS 'Income amount (nullable - may be withheld or not reported)';

-- Indexes for income source lookups
CREATE INDEX idx_income_sources_declaration ON income_sources(declaration_id);
CREATE INDEX idx_income_sources_family_member ON income_sources(family_member_id);
CREATE INDEX idx_income_sources_owner_type ON income_sources(owner_type);
CREATE INDEX idx_income_sources_type ON income_sources(income_type);

-- Expenses: Major purchases and transactions
CREATE TABLE expenses (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    declaration_id          UUID NOT NULL REFERENCES declarations(id) ON DELETE CASCADE,

    -- Expense details
    expense_type            VARCHAR(255) NOT NULL,
    description             TEXT,
    amount                  NUMERIC(15,2) NOT NULL,
    currency                VARCHAR(10) DEFAULT 'UAH',
    expense_date            DATE,

    raw_data                JSONB,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for expense lookups
CREATE INDEX idx_expenses_declaration ON expenses(declaration_id);
CREATE INDEX idx_expenses_type ON expenses(expense_type);

-- Liabilities: Loans, mortgages, debts
CREATE TABLE liabilities (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    declaration_id          UUID NOT NULL REFERENCES declarations(id) ON DELETE CASCADE,
    owner_type              VARCHAR(50) NOT NULL,
    family_member_id        UUID REFERENCES family_members(id),

    -- Liability details
    liability_type          VARCHAR(255) NOT NULL,
    creditor_name           VARCHAR(500),
    creditor_edrpou         VARCHAR(50),
    original_amount         NUMERIC(15,2),
    outstanding_amount      NUMERIC(15,2),
    currency                VARCHAR(50) DEFAULT 'UAH',
    interest_rate           NUMERIC(5,2),
    issue_date              DATE,
    maturity_date           DATE,
    purpose                 TEXT,

    raw_data                JSONB,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE liabilities IS 'Financial obligations (loans, debts, mortgages)';

-- Indexes for liability lookups
CREATE INDEX idx_liabilities_declaration ON liabilities(declaration_id);
CREATE INDEX idx_liabilities_family_member ON liabilities(family_member_id);
CREATE INDEX idx_liabilities_owner_type ON liabilities(owner_type);

-- =============================================================================
-- WORK AND ORGANIZATION TABLES
-- =============================================================================

-- Part-time Work: Additional employment
CREATE TABLE part_time_work (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    declaration_id          UUID NOT NULL REFERENCES declarations(id) ON DELETE CASCADE,

    -- Employment details
    employer_name           VARCHAR(500),
    employer_edrpou         VARCHAR(50),
    employer_address        TEXT,
    position                VARCHAR(255),
    period_from             DATE,
    period_to               DATE,

    raw_data                JSONB,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Index for part-time work lookups
CREATE INDEX idx_part_time_work_declaration ON part_time_work(declaration_id);

-- Memberships: Boards, committees, organizations
CREATE TABLE memberships (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    declaration_id          UUID NOT NULL REFERENCES declarations(id) ON DELETE CASCADE,

    -- Organization details
    organization_name       VARCHAR(500),
    organization_edrpou     VARCHAR(50),
    organization_type       VARCHAR(255),
    role                    VARCHAR(255),
    period_from             DATE,
    period_to               DATE,

    raw_data                JSONB,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Index for membership lookups
CREATE INDEX idx_memberships_declaration ON memberships(declaration_id);

-- =============================================================================
-- SCRAPING METADATA
-- =============================================================================

-- Scraping Progress: Track distributed scraping workers
CREATE TABLE scraping_progress (
    worker_id               VARCHAR(255) PRIMARY KEY,
    page_start              INTEGER NOT NULL,
    page_end                INTEGER NOT NULL,
    last_completed_page     INTEGER NOT NULL,
    status                  VARCHAR(50) NOT NULL,
    started_at              TIMESTAMP NOT NULL,
    updated_at              TIMESTAMP NOT NULL,
    completed_at            TIMESTAMP
);

-- Index for progress tracking
CREATE INDEX idx_scraping_progress_status ON scraping_progress(status);

-- =============================================================================
-- VIEWS FOR ANALYTICS
-- =============================================================================

-- Declarant Assets Summary: Aggregate view of declarant's assets
CREATE VIEW declarant_assets_summary AS
SELECT
    d.id AS declarant_id,
    d.lastname,
    d.firstname,
    d.middlename,
    dec.declaration_year,
    COUNT(DISTINCT re.id) AS real_estate_count,
    COUNT(DISTINCT v.id) AS vehicles_count,
    COUNT(DISTINCT s.id) AS securities_count,
    COUNT(DISTINCT cr.id) AS corporate_rights_count,
    SUM(COALESCE(re.cost_at_acquisition, 0)) AS total_real_estate_value,
    SUM(COALESCE(v.cost_at_acquisition, 0)) AS total_vehicles_value,
    SUM(COALESCE(is2.amount, 0)) AS total_income
FROM declarants d
LEFT JOIN declarations dec ON d.id = dec.declarant_id
LEFT JOIN real_estate re ON dec.id = re.declaration_id AND re.owner_type = 'declarant'
LEFT JOIN vehicles v ON dec.id = v.declaration_id AND v.owner_type = 'declarant'
LEFT JOIN securities s ON dec.id = s.declaration_id AND s.owner_type = 'declarant'
LEFT JOIN corporate_rights cr ON dec.id = cr.declaration_id AND cr.owner_type = 'declarant'
LEFT JOIN income_sources is2 ON dec.id = is2.declaration_id AND is2.owner_type = 'declarant'
GROUP BY d.id, d.lastname, d.firstname, d.middlename, dec.declaration_year;

-- Family Assets Summary: Aggregate view of family member assets
CREATE VIEW family_assets_summary AS
SELECT
    fm.id AS family_member_id,
    fm.lastname,
    fm.firstname,
    fm.subject_relation,
    dec.declaration_year,
    d.id AS declarant_id,
    d.lastname AS declarant_lastname,
    COUNT(DISTINCT re.id) AS real_estate_count,
    COUNT(DISTINCT v.id) AS vehicles_count,
    SUM(COALESCE(re.cost_at_acquisition, 0)) AS total_real_estate_value
FROM family_members fm
JOIN declarations dec ON fm.declaration_id = dec.id
JOIN declarants d ON dec.declarant_id = d.id
LEFT JOIN real_estate re ON dec.id = re.declaration_id AND re.family_member_id = fm.id
LEFT JOIN vehicles v ON dec.id = v.declaration_id AND v.family_member_id = fm.id
GROUP BY fm.id, fm.lastname, fm.firstname, fm.subject_relation, dec.declaration_year, d.id, d.lastname;
