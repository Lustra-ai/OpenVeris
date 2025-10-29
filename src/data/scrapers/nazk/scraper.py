"""NAZK Declarations Scraper using Crawlee framework."""

import asyncio
import random
from typing import Any

import httpx

from src.data.scrapers.nazk.config import NAZKConfig
from src.data.scrapers.nazk.postgres_storage import PostgreSQLStorage
from src.utils.logger import init_logger


class NAZKScraper:
    """Scraper for NAZK public declarations API."""

    def __init__(self, config: NAZKConfig | None = None):
        """Initialize NAZK scraper.

        Args:
            config: Configuration object. If None, uses default config.
        """
        self.config = config or NAZKConfig()
        self.logger = init_logger(__name__)
        self._user_agent_index = 0
        self._request_count = 0

        # Shared HTTP client for connection pooling
        self._client: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(5)  # Limit concurrent requests (avoid 429)

        # Initialize storage if enabled
        if self.config.use_storage:
            if self.config.storage_type == "postgresql":
                self.storage: PostgreSQLStorage | None = PostgreSQLStorage(
                    host=self.config.pg_host,
                    port=self.config.pg_port,
                    database=self.config.pg_database,
                    user=self.config.pg_user,
                    password=self.config.pg_password,
                )
            else:
                raise ValueError(
                    f"Unsupported storage type: {self.config.storage_type}. Only 'postgresql' is supported."
                )
        else:
            self.storage = None

    async def __aenter__(self) -> "NAZKScraper":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - ensures client is closed even on exception."""
        await self.close()

    def _get_next_user_agent(self) -> str:
        """Get next user agent for rotation."""
        assert self.config.user_agents is not None, "user_agents must be initialized"
        user_agent = self.config.user_agents[self._user_agent_index]
        self._user_agent_index = (self._user_agent_index + 1) % len(self.config.user_agents)
        return user_agent

    def _ensure_client_initialized(self) -> None:
        """Initialize the HTTP client if not already created."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=30),
            )

    async def close(self) -> None:
        """Close the shared HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _make_request(
        self, url: str, params: dict[str, Any] | None = None, retry_count: int = 0
    ) -> dict[str, Any] | None:
        """Make HTTP request with retry logic and rate limiting.

        Args:
            url: URL to request
            params: Query parameters
            retry_count: Current retry attempt number

        Returns:
            JSON response or None if failed
        """
        # Use semaphore to limit concurrent requests
        async with self._semaphore:
            # Rate limiting with randomization to prevent IP blocking
            # Randomly vary delay by ±30% to appear more natural
            min_delay = self.config.request_delay_seconds * 0.7
            max_delay = self.config.request_delay_seconds * 1.3
            delay = random.uniform(min_delay, max_delay)
            await asyncio.sleep(delay)

            headers = {
                "User-Agent": self._get_next_user_agent(),
                "Accept": "application/json",
                "Accept-Language": "uk-UA,uk;q=0.9,en;q=0.8",
            }

            try:
                self._ensure_client_initialized()
                assert self._client is not None, "Client should be initialized"
                self.logger.debug(f"Requesting (attempt {retry_count + 1}): {url}")

                import time

                start_time = time.time()
                response = await self._client.get(url, params=params, headers=headers)
                elapsed = time.time() - start_time

                response.raise_for_status()

                self._request_count += 1
                self.logger.debug(f"Success in {elapsed:.2f}s: {url}")
                return response.json()  # type: ignore[no-any-return]

            except httpx.HTTPStatusError as e:
                self.logger.warning(
                    f"HTTP {e.response.status_code} on attempt {retry_count + 1}/{self.config.max_retries + 1}: {url}"
                )
                if retry_count < self.config.max_retries:
                    retry_delay = self.config.retry_delay_seconds * (retry_count + 1)
                    self.logger.info(f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    return await self._make_request(url, params, retry_count + 1)
                self.logger.error(f"Failed after {self.config.max_retries + 1} attempts: {url}")
                return None

            except httpx.RequestError as e:
                error_type = type(e).__name__
                error_msg = str(e)
                self.logger.error(
                    f"{error_type} on attempt {retry_count + 1}/{self.config.max_retries + 1}: {error_msg} | URL: {url}"
                )
                if retry_count < self.config.max_retries:
                    retry_delay = self.config.retry_delay_seconds * (retry_count + 1)
                    self.logger.info(f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    return await self._make_request(url, params, retry_count + 1)
                self.logger.error(
                    f"Failed after {self.config.max_retries + 1} attempts ({error_type}): {url}"
                )
                return None

            except Exception as e:
                error_type = type(e).__name__
                self.logger.error(f"Unexpected {error_type}: {e} | URL: {url}", exc_info=True)
                return None
