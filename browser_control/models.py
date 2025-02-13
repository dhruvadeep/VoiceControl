from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    query: str = Field(strict=True, default="https://www.bing.com/search")