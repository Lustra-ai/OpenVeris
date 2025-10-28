"""
NAZK Multi-Worker Scraper - Process multiple years in parallel.
Each worker handles a subset of years for maximum throughput.
"""

import argparse
import asyncio

from scrape_nazk_by_year import YearBasedScraper


async def worker(worker_id: int, years: list[int]) -> None:
    """Worker process that scrapes specific years.

    Args:
        worker_id: Worker identifier
        years: List of years this worker should process
    """
    scraper = YearBasedScraper()
    scraper.logger.info(f"Worker {worker_id} starting with years: {years}")

    total_new = 0
    total_existing = 0

    for year in years:
        try:
            stats = await scraper.scrape_year(year)
            total_new += stats["new_saved"]
            total_existing += stats["skipped_existing"]

            scraper.logger.info(
                f"Worker {worker_id} - Year {year} complete: "
                f"{stats['new_saved']} new, {stats['skipped_existing']} existing"
            )
        except Exception as e:
            scraper.logger.error(f"Worker {worker_id} - Error on year {year}: {e}", exc_info=True)
            continue

    scraper.logger.info(f"Worker {worker_id} finished: {total_new} new, {total_existing} existing")


async def main(num_workers: int = 3, start_year: int = 2016, end_year: int = 2025) -> None:
    """Run multiple workers in parallel.

    Args:
        num_workers: Number of parallel workers (default: 3)
        start_year: First year to scrape (default: 2016)
        end_year: Last year to scrape (default: 2025)
    """
    # Generate list of all years
    all_years = list(range(end_year, start_year - 1, -1))  # Newest first

    # Distribute years among workers
    years_per_worker = []
    for i in range(num_workers):
        worker_years = all_years[i::num_workers]  # Every Nth year
        years_per_worker.append(worker_years)

    print(f"Starting {num_workers} workers for years {start_year}-{end_year}")
    print("Year distribution:")
    for i, years in enumerate(years_per_worker):
        print(f"  Worker {i}: {years}")

    # Start all workers in parallel
    tasks = [worker(i, years) for i, years in enumerate(years_per_worker)]

    await asyncio.gather(*tasks)
    print("\nAll workers completed!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run NAZK scraper with multiple workers")
    parser.add_argument("--workers", type=int, default=3, help="Number of workers (default: 3)")
    parser.add_argument("--start-year", type=int, default=2016, help="Start year (default: 2016)")
    parser.add_argument("--end-year", type=int, default=2025, help="End year (default: 2025)")

    args = parser.parse_args()

    asyncio.run(main(args.workers, args.start_year, args.end_year))
