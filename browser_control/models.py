from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """SearchQuery: Pydantic model for the search query."""

    query: str = Field(strict=True, default="India")
