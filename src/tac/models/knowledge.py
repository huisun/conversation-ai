"""Knowledge models for the Twilio Agent Connect."""

from typing import Literal

from pydantic import BaseModel, Field


class Knowledge(BaseModel):
    """Represents a Twilio Knowledge resource."""

    id: str
    name: str
    description: str
    type: Literal["Web", "File", "Text", "DB"]


class KnowledgeBase(BaseModel):
    """Represents a Twilio Knowledge Base resource."""

    id: str = Field(description="The unique identifier for the Knowledge Base")
    display_name: str = Field(
        alias="displayName", description="Human-readable name for the Knowledge Base"
    )
    description: str = Field(description="Description of the Knowledge Base")
    status: Literal["QUEUED", "PROVISIONING", "ACTIVE", "FAILED", "DELETING"] = Field(
        description="The provisioning status of the Knowledge Base"
    )
    created_at: str = Field(alias="createdAt", description="Creation timestamp in ISO 8601 format")
    updated_at: str = Field(
        alias="updatedAt", description="Last updated timestamp in ISO 8601 format"
    )
    version: int = Field(description="Version number of the Knowledge Base")

    model_config = {"populate_by_name": True}


class KnowledgeChunkResult(BaseModel):
    """Represents a search result chunk from knowledge base search."""

    content: str = Field(description="The chunk content")
    knowledge_id: str = Field(alias="knowledgeId", description="The knowledge source ID")
    created_at: str = Field(alias="createdAt", description="Creation timestamp in ISO 8601 format")
    score: float | None = Field(default=None, description="Relevance score for the search result")

    model_config = {"populate_by_name": True}
