"""Pagination models for Twilio API responses."""

from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    """Pagination metadata for API list responses."""

    key: str = Field(..., description="Key for the response")
    page_size: int = Field(..., alias="pageSize", description="Page size")
    previous_token: str | None = Field(
        default=None, alias="previousToken", description="Token for previous page"
    )
    next_token: str | None = Field(
        default=None, alias="nextToken", description="Token for next page"
    )

    model_config = {"populate_by_name": True}
