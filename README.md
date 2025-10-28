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

### 3. Start Database Services

```bash
docker compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- pgAdmin (port 5050, optional GUI)

### 4. Initialize Database Schema

```bash
PGPASSWORD=openveris_dev_password psql -h localhost -U openveris -d openveris -f migrations/001_initial_schema.sql
```

## Quick Start

### Scrape NAZK Declarations

```bash
# Scrape declarations by year
.venv/bin/python scrape_nazk_by_year.py --year 2024

# Scrape with multiple workers (faster)
.venv/bin/python scrape_nazk_workers.py --year 2024 --workers 4
```

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
│   │       └── nazk/              # NAZK API scraper
│   └── utils/
│       └── logger.py              # Rich logging
├── migrations/
│   └── 001_initial_schema.sql    # PostgreSQL schema
├── scrape_nazk_by_year.py         # Single-year scraper
├── scrape_nazk_workers.py         # Multi-worker scraper
├── docker-compose.yml             # PostgreSQL + Redis + pgAdmin
└── pyproject.toml                 # Dependencies
```

## Development

```bash
# Format code
./scripts/format.sh

# Lint code
./scripts/lint.sh

# Run with dev dependencies
uv sync --extra dev
```

## How It Works

1. **Scraping**: Fetch declarations from NAZK API with rate limiting
2. **Parsing**: Extract declarant info, family members, assets (real estate, vehicles, bank accounts, etc.)
3. **Storage**: Save to normalized PostgreSQL database
4. **Deduplication**: Use Redis to track processed declarations
5. **Analysis**: (Coming soon) ML anomaly detection on income vs assets

## Status

**In Active Development** - Data collection phase complete. ML pipeline coming soon.

## License

TBD
