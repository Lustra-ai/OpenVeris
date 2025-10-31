"""
NAZK Scraper - Year-based approach to get all historical declarations.
This script scrapes declarations year by year to avoid API pagination limits.
"""

import asyncio
from typing import Any

import redis

from src.data.scrapers.nazk.config import NAZKConfig
from src.data.scrapers.nazk.postgres_storage import PostgreSQLStorage
from src.data.scrapers.nazk.schemas import SearchFilters
from src.data.scrapers.nazk.scraper import NAZKScraper
from src.utils.logger import init_logger


class YearBasedScraper:
    """Scraper that processes declarations year by year."""

    def __init__(self) -> None:
        self.logger = init_logger(__name__)
        self.config = NAZKConfig.from_yaml()

        # Initialize PostgreSQL storage
        self.storage = PostgreSQLStorage(
            password=self.config.pg_password,
            host=self.config.pg_host,
            port=self.config.pg_port,
            database=self.config.pg_database,
            user=self.config.pg_user,
        )

        # Initialize Redis for fast existence checks
        self.redis_client = redis.Redis(host=self.config.redis_host, port=self.config.redis_port, decode_responses=True)
        self.redis_key = "nazk:existing_declaration_ids"

        # Load existing IDs from PostgresSQL into Redis on startup
        self._sync_redis_with_db()

        # Initialize scraper
        self.scraper = NAZKScraper(config=self.config)
        self.scraper.storage = self.storage

    async def __aenter__(self) -> "YearBasedScraper":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - ensures resources are cleaned up."""
        await self.cleanup()

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.scraper:
            await self.scraper.close()
        if self.redis_client:
            self.redis_client.close()

    def _sync_redis_with_db(self) -> None:
        """Load all existing declaration IDs from PostgreSQL into Redis SET."""
        self.logger.info("Syncing Redis cache with PostgreSQL...")
        existing_ids = self.storage.get_existing_ids([])  # Get all IDs

        if existing_ids:
            # Clear existing Redis set
            self.redis_client.delete(self.redis_key)
            # Add all IDs to Redis SET
            self.redis_client.sadd(self.redis_key, *existing_ids)
            self.logger.info(f"Loaded {len(existing_ids)} existing declaration IDs into Redis")
        else:
            self.logger.info("No existing declarations found, starting fresh")

    async def scrape_year(self, year: int) -> dict[str, Any]:
        """Scrape all declarations for a specific year.

        Args:
            year: Declaration year to scrape

        Returns:
            Dictionary with statistics
        """
        self.logger.info("=" * 80)
        self.logger.info(f"Starting scrape for year {year}")
        self.logger.info("=" * 80)

        filters = SearchFilters(declaration_year=year)
        page = 1
        total_declarations = 0
        new_declarations = 0
        skipped_existing = 0

        while True:
            self.logger.info(f"Year {year}: Fetching page {page}")

            # Fetch page
            params = filters.to_query_params(page=page)
            url = f"{self.config.base_url}{self.config.list_endpoint}"

            data = await self.scraper._make_request(url, params=params)

            if not data:
                self.logger.warning(f"Year {year}: No data returned for page {page}")
                break

            # Extract declarations data
            declarations_data: list[dict] = []
            if isinstance(data, dict):
                extracted = data.get("items", data.get("results", data.get("data", [])))
                if isinstance(extracted, list):
                    declarations_data = extracted
            elif isinstance(data, list):
                declarations_data = data

            if not declarations_data or len(declarations_data) == 0:
                self.logger.info(f"Year {year}: No more declarations at page {page}")
                break

            # Get IDs from this page
            page_ids = [item.get("id") for item in declarations_data if isinstance(item, dict) and item.get("id")]

            # Check which ones already exist in Redis (FAST O(1) lookup)
            existing_ids = set()
            for page_id in page_ids:
                if page_id and self.redis_client.sismember(self.redis_key, str(page_id)):
                    existing_ids.add(page_id)

            new_ids = set(page_ids) - existing_ids

            self.logger.info(
                f"Year {year}, Page {page}: {len(page_ids)} total, {len(existing_ids)} existing, {len(new_ids)} new"
            )

            total_declarations += len(page_ids)
            skipped_existing += len(existing_ids)

            # Process only new declarations - PARALLEL FETCHING
            async def fetch_and_save_declaration(document_id: str) -> bool:
                """Fetch and save a single declaration."""
                try:
                    full_data = await self.scraper._make_request(f"{self.config.base_url}/documents/{document_id}")
                    if full_data:
                        success = self.storage.save_declaration(document_id, full_data)
                        if success:
                            # Add to Redis cache for future lookups
                            self.redis_client.sadd(self.redis_key, document_id)
                            return True
                        else:
                            self.logger.warning(f"Failed to save declaration {document_id}")
                    else:
                        self.logger.warning(f"Failed to fetch declaration {document_id} (API returned None)")
                except Exception as e:
                    self.logger.error(f"Exception processing {document_id}: {type(e).__name__}: {e}")
                return False

            # Fetch all new declarations in parallel
            tasks = [
                fetch_and_save_declaration(str(item.get("id")))
                for item in declarations_data
                if isinstance(item, dict) and item.get("id") and item.get("id") in new_ids
            ]

            # Add timeout to prevent infinite blocking on mass API failures
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=300.0,  # 5 minutes max for entire page
                )
            except TimeoutError:
                self.logger.error(f"Year {year}, Page {page}: Timeout after 300s, marking all as failed")
                results = [False] * len(tasks)

            saved_count = sum(1 for r in results if r is True)
            failed_count = sum(1 for r in results if r is False)
            exception_count = sum(1 for r in results if not isinstance(r, bool))

            new_declarations += saved_count

            if failed_count > 0 or exception_count > 0:
                self.logger.warning(
                    f"Year {year}, Page {page}: {saved_count} saved, "
                    f"{failed_count} failed, {exception_count} exceptions"
                )

            if new_declarations % 100 == 0:
                self.logger.info(f"Year {year}: Progress - {new_declarations} new declarations saved")

            page += 1

        stats = {
            "year": year,
            "total_found": total_declarations,
            "new_saved": new_declarations,
            "skipped_existing": skipped_existing,
            "pages_processed": page - 1,
        }

        self.logger.info(f"Year {year} complete: {stats}")
        return stats

    async def scrape_all_years(self, start_year: int = 2016, end_year: int = 2025) -> None:
        """Scrape all years from start_year to end_year.

        Args:
            start_year: First year to scrape (default: 2016)
            end_year: Last year to scrape (default: 2025)
        """
        self.logger.info(f"Starting year-based scrape from {start_year} to {end_year}")

        all_stats = []
        total_new = 0
        total_existing = 0

        # Process years in reverse order (newest first) to get recent data quickly
        for year in range(end_year, start_year - 1, -1):
            try:
                stats = await self.scrape_year(year)
                all_stats.append(stats)
                total_new += stats["new_saved"]
                total_existing += stats["skipped_existing"]

                self.logger.info(f"Overall progress: {total_new} new, {total_existing} skipped")
            except Exception as e:
                self.logger.error(f"Error scraping year {year}: {e}", exc_info=True)
                continue

        # Final summary
        self.logger.info("=" * 80)
        self.logger.info("SCRAPING COMPLETE!")
        self.logger.info("=" * 80)
        self.logger.info(f"Total new declarations saved: {total_new}")
        self.logger.info(f"Total existing declarations skipped: {total_existing}")
        self.logger.info("\nPer-year breakdown:")
        for stats in all_stats:
            self.logger.info(
                f"  {stats['year']}: {stats['new_saved']} new, "
                f"{stats['skipped_existing']} existing, "
                f"{stats['pages_processed']} pages"
            )


async def main() -> None:
    """Main entry point."""
    async with YearBasedScraper() as scraper:
        # Scrape all years from 2016 to 2025
        await scraper.scrape_all_years(start_year=2016, end_year=2025)


if __name__ == "__main__":
    asyncio.run(main())
