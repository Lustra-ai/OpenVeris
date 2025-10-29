"""Configuration for NAZK scraper."""

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv


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
    max_retries: int = 3  # Maximum allowed: 10
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

    # PostgreSQL settings (loaded from environment variables)
    pg_host: str | None = None
    pg_port: int | None = None
    pg_database: str | None = None
    pg_user: str | None = None
    pg_password: str | None = None

    # Worker/distributed scraping settings
    worker_id: str | None = None  # Unique identifier for this worker
    page_start: int | None = None  # Starting page for this worker
    page_end: int | None = None  # Ending page for this worker

    def __post_init__(self):
        """Initialize defaults and validate configuration."""
        # Initialize default user agents if not provided
        if self.user_agents is None:
            self.user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            ]

        # Validate max_retries to prevent stack overflow in recursive retry logic
        if self.max_retries > 10:
            raise ValueError(
                f"max_retries must not exceed 10 (got {self.max_retries}). "
                "Higher values can cause stack overflow in recursive retry logic."
            )
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be non-negative (got {self.max_retries})")

    @classmethod
    def from_yaml(cls, config_path: str | Path | None = None) -> "NAZKConfig":
        """Load configuration from YAML file and environment variables.

        Environment variables take precedence over YAML values for sensitive data.
        Required environment variables:
        - POSTGRES_HOST
        - POSTGRES_PORT
        - POSTGRES_DB
        - POSTGRES_USER
        - POSTGRES_PASSWORD

        Args:
            config_path: Path to YAML config file. If None, uses default path.

        Returns:
            NAZKConfig instance with values from YAML and environment variables.
        """
        # Load environment variables from .env file
        load_dotenv()

        if config_path is None:
            # Default to config/nazk.yaml in project root
            config_path = Path(__file__).parent.parent.parent.parent.parent / "config" / "nazk.yaml"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        # Override with environment variables for sensitive data
        config_data["pg_host"] = os.getenv("POSTGRES_HOST", config_data.get("pg_host"))
        config_data["pg_port"] = int(os.getenv("POSTGRES_PORT", config_data.get("pg_port") or 5432))
        config_data["pg_database"] = os.getenv("POSTGRES_DB", config_data.get("pg_database"))
        config_data["pg_user"] = os.getenv("POSTGRES_USER", config_data.get("pg_user"))
        config_data["pg_password"] = os.getenv("POSTGRES_PASSWORD", config_data.get("pg_password"))

        # Validate that required credentials are present
        required_fields = ["pg_host", "pg_database", "pg_user", "pg_password"]
        missing_fields = [field for field in required_fields if not config_data.get(field)]
        if missing_fields:
            raise ValueError(
                f"Missing required PostgreSQL configuration: {', '.join(missing_fields)}. "
                "Please set them in .env file or YAML config."
            )

        return cls(**config_data)
