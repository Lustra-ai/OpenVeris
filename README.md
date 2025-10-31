# OpenVeris

Automated anomaly detection for Ukrainian public officials' asset declarations. Scrapes data from NAZK, stores in PostgreSQL, and identifies suspicious patterns using ML.

## Features

- **Data Collection**: Async scraper for [NAZK](https://public.nazk.gov.ua/) (National Agency on Corruption Prevention)
- **PostgreSQL Storage**: Normalized database with 14+ tables (declarants, declarations, assets, income, liabilities)
- **Redis Caching**: Deduplication and request caching
- **Anti-Blocking**: Rate limiting, user agent rotation, proxy support
- **ML Pipeline**: (Coming soon) Anomaly detection for suspicious declarations

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Docker & Docker Compose (for PostgreSQL/Redis)

## Installation

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone & Install Dependencies

```bash
git clone https://github.com/yourusername/OpenVeris.git
cd OpenVeris
uv sync
```

### 3. Configure Environment Variables

Create a `.env` file with database credentials:

```bash
cp .env.example .env
```

The default configuration works with the provided `docker-compose.yml`. Edit `.env` if you need custom settings.

### 4. Start Database Services

```bash
docker compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- pgAdmin (port 5050, optional GUI)

### 5. Initialize Database Schema

Apply all migrations in order:

```bash
# Set password from .env
source .env

# Apply migrations
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -f migrations/001_initial_schema.sql
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -f migrations/002_fix_declarant_uniqueness.sql
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -f migrations/003_add_submission_date_and_rename_fields.sql
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -f migrations/004_link_family_members_to_declarants.sql
```

See `migrations/README.md` for details on each migration.

## Quick Start

### Scrape NAZK Declarations

```bash
# Scrape declarations from a specific year
python -m src.data.scrapers.nazk.scrape_nazk_by_year --year 2024

# Scrape with multiple workers for faster processing
python -m src.data.scrapers.nazk.scrape_nazk_workers --workers 3 --start-year 2020 --end-year 2025
```

The scraper will:
- Load configuration from `config/nazk.yaml` and `.env`
- Use Redis cache to skip already-scraped declarations
- Save all data to PostgreSQL with proper normalization
- Handle rate limiting and retries automatically

### Check Database Stats

```bash
PGPASSWORD=openveris_dev_password psql -h localhost -U openveris -d openveris -c "
SELECT
    (SELECT COUNT(*) FROM declarants) as declarants,
    (SELECT COUNT(*) FROM declarations) as declarations,
    (SELECT COUNT(*) FROM real_estate) as real_estate,
    (SELECT COUNT(*) FROM vehicles) as vehicles,
    (SELECT COUNT(*) FROM income_sources) as income;
"
```

### Access pgAdmin (Database GUI)

1. Open http://localhost:5050
2. Login: `admin@admin.com` / `admin`
3. Add server:
   - Host: `postgres` (or `host.docker.internal` on Mac)
   - Port: `5432`
   - Database: `openveris`
   - Username: `openveris`
   - Password: `openveris_dev_password`

## Project Structure

```
OpenVeris/
├── src/
│   ├── data/
│   │   └── scrapers/
│   │       └── nazk/                      # NAZK API scraper
│   │           ├── config.py              # Configuration with YAML/env support
│   │           ├── scraper.py             # API client with rate limiting
│   │           ├── postgres_storage.py    # Database persistence layer
│   │           ├── schemas.py             # Data models
│   │           ├── scrape_nazk_by_year.py # Single-year scraper
│   │           └── scrape_nazk_workers.py # Multi-worker scraper
│   └── utils/
│       └── logger.py                      # Rich logging
├── config/
│   └── nazk.yaml                          # Scraper configuration
├── migrations/
│   ├── 001_initial_schema.sql             # Initial database schema
│   ├── 002_fix_declarant_uniqueness.sql   # Fix tax_number constraints
│   ├── 003_add_submission_date_and_rename_fields.sql
│   ├── 004_link_family_members_to_declarants.sql
│   └── README.md                          # Migration documentation
├── .github/
│   └── workflows/
│       └── code-quality.yml               # CI/CD pipeline
├── .env.example                           # Environment variables template
├── docker-compose.yml                     # PostgreSQL + Redis + pgAdmin
└── pyproject.toml                         # Dependencies
```

## Development

### Code Quality

```bash
# Install dev dependencies
uv sync --extra dev

# Format code
ruff format src/
ruff check --fix src/

# Lint and type check
ruff check src/
mypy src/
```

### CI/CD

GitHub Actions automatically runs code quality checks on every push and pull request:
- Ruff linting and formatting
- Import sorting validation
- Type checking with mypy

See `.github/workflows/code-quality.yml` for configuration.

## Configuration

The scraper uses a two-layer configuration system:

1. **YAML Configuration** (`config/nazk.yaml`): API settings, rate limits, retry logic
2. **Environment Variables** (`.env`): Sensitive data like database credentials

Key configuration options:
- `requests_per_minute`: API rate limiting (default: 30)
- `max_retries`: Number of retry attempts (max: 10 to prevent stack overflow)
- `request_delay_seconds`: Delay between requests (default: 0.6s)

See `src/data/scrapers/nazk/config.py` for all available options.

## How It Works

1. **Scraping**: Fetch declarations from NAZK API with rate limiting and automatic retries
2. **Parsing**: Extract declarant info, family members, assets (real estate, vehicles, bank accounts, etc.)
3. **Storage**: Save to normalized PostgreSQL database with 15 tables
4. **Deduplication**: Use Redis cache to skip already-processed declarations (99,000+ IDs loaded instantly)
5. **Parallel Processing**: Multi-worker support for faster scraping (tested with 2-4 workers)
6. **Analysis**: (Coming soon) ML anomaly detection on income vs assets

## Database Schema

The system uses a fully normalized PostgreSQL schema with:
- **Declarants**: Unique public officials
- **Declarations**: Annual/termination declarations
- **Family Members**: Spouse, children (with person deduplication)
- **Assets**: Real estate, vehicles, bank accounts, corporate rights, securities, valuables
- **Financial**: Income sources, expenses, liabilities
- **Work**: Part-time work, memberships

See `migrations/README.md` for detailed schema documentation and `src/data/scrapers/nazk/README.md` for the ER diagram.

## Performance

Tested and validated with 100,000+ declarations:
- **Single worker**: ~5 declarations/second
- **Multi-worker (2-4)**: ~10-20 declarations/second
- **Redis cache**: Enables instant duplicate detection
- **Success rate**: 100% (611/611 in latest test)
- **Zero errors** in production validation

## Status

**Production Ready** ✅

- ✅ Data collection: Fully implemented and tested
- ✅ Database: Normalized schema with migrations
- ✅ Configuration: YAML + environment variables
- ✅ CI/CD: GitHub Actions for code quality
- ✅ Multi-worker: Parallel processing tested
- 🚧 ML Pipeline: Coming soon (anomaly detection)

## License

TBD
