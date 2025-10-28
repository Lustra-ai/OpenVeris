"""NAZK Public Declarations Scraper.

This module provides scraping functionality for the National Agency
on Corruption Prevention (NAZK) public declarations database.
"""

from src.data.scrapers.nazk.config import NAZKConfig
from src.data.scrapers.nazk.scraper import NAZKScraper

__all__ = ["NAZKScraper", "NAZKConfig"]
