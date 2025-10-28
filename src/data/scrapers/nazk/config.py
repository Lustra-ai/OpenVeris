"""Configuration for NAZK scraper."""

from dataclasses import dataclass


@dataclass
class NAZKConfig:
    """Configuration for NAZK scraper."""

    # API endpoints
    base_url: str = "https://public-api.nazk.gov.ua/v2"
    list_endpoint: str = "/documents/list"
    document_endpoint: str = "/documents/{document_id}"

    # Rate limiting and anti-blocking
    requests_per_minute: int = 30
    request_delay_seconds: float = 0.6
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    timeout_seconds: int = 30

    # Pagination
    max_pages_per_request: int = 100
    results_per_page: int = 100

    # Proxy settings (optional)
    proxy_urls: list[str] | None = None

    # User agents for rotation
    user_agents: list[str] | None = None

    # Storage settings
    storage_type: str = "sqlite"  # "sqlite" or "postgresql"
    db_path: str = "data/nazk.db"  # For SQLite
    use_storage: bool = True
    batch_size: int = 100  # Number of declarations to save in one batch

    # PostgreSQL settings
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "openveris"
    pg_user: str = "openveris"
    pg_password: str = "openveris_dev_password"

    # Worker/distributed scraping settings
    worker_id: str | None = None  # Unique identifier for this worker
    page_start: int | None = None  # Starting page for this worker
    page_end: int | None = None  # Ending page for this worker

    def __post_init__(self):
        """Initialize default user agents if not provided."""
        if self.user_agents is None:
            self.user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            ]
