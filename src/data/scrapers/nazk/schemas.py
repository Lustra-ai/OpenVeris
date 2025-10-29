"""Data schemas for NAZK declarations API.

This module defines data structures (schemas) for NAZK API requests and responses.
Not to be confused with ML models, which would be in a separate models/ directory.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


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
