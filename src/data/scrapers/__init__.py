"""Data scrapers for OpenVeris project.

This module provides scrapers for collecting declaration data from various sources:
- NAZK (National Agency on Corruption Prevention)
- YouControl (planned)

Example:
    from src.data.scrapers import NAZKScraper, NAZKConfig

    scraper = NAZKScraper()
    declarations = await scraper.scrape_by_year(2024)
"""

from src.data.scrapers.nazk import NAZKScraper
from src.data.scrapers.nazk.config import NAZKConfig
from src.data.scrapers.nazk.models import Declaration, SearchFilters

__all__ = [
    "NAZKScraper",
    "NAZKConfig",
    "Declaration",
    "SearchFilters",
]
