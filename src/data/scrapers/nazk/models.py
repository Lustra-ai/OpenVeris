"""Data models for NAZK declarations."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Declaration:
    """Represents a NAZK declaration."""

    document_id: str
    declarant_name: str | None = None
    user_declarant_id: int | None = None
    document_type: int | None = None
    declaration_type: int | None = None
    declaration_year: int | None = None
    submission_date: datetime | None = None
    data: dict[str, Any] | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Declaration":
        """Create Declaration from API response."""
        submission_date = None
        if "submission_date" in data and data["submission_date"]:
            try:
                # Handle Unix timestamp or ISO format
                if isinstance(data["submission_date"], (int, float)):
                    submission_date = datetime.fromtimestamp(data["submission_date"])
                else:
                    submission_date = datetime.fromisoformat(data["submission_date"])
            except (ValueError, OSError):
                pass

        return cls(
            document_id=data.get("id", ""),
            declarant_name=data.get("declarant_name"),
            user_declarant_id=data.get("user_declarant_id"),
            document_type=data.get("document_type"),
            declaration_type=data.get("declaration_type"),
            declaration_year=data.get("declaration_year"),
            submission_date=submission_date,
            data=data,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "document_id": self.document_id,
            "declarant_name": self.declarant_name,
            "user_declarant_id": self.user_declarant_id,
            "document_type": self.document_type,
            "declaration_type": self.declaration_type,
            "declaration_year": self.declaration_year,
            "submission_date": self.submission_date.isoformat() if self.submission_date else None,
            "data": self.data,
        }


@dataclass
class SearchFilters:
    """Filters for searching declarations."""

    query: str | None = None
    user_declarant_id: int | None = None
    document_type: int | None = None
    declaration_type: int | None = None
    declaration_year: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None

    def to_query_params(self, page: int = 1) -> dict[str, Any]:
        """Convert filters to API query parameters."""
        params: dict[str, Any] = {"page": page}

        if self.query and len(self.query) >= 3:
            params["q"] = self.query

        if self.user_declarant_id:
            params["user_declarant_id"] = self.user_declarant_id

        if self.document_type:
            params["document_type"] = self.document_type

        if self.declaration_type:
            params["declaration_type"] = self.declaration_type

        if self.declaration_year:
            params["declaration_year"] = self.declaration_year

        if self.start_date:
            params["start_date"] = int(self.start_date.timestamp())

        if self.end_date:
            params["end_date"] = int(self.end_date.timestamp())

        return params
