from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HandoffPayload(BaseModel):
    """Structured payload generated during a handoff.

    Contains conversation context and developer-defined attributes
    for routing to the target system (e.g., Flex TaskRouter).
    """

    conversation_id: str = Field(..., alias="conversationId")
    memory_store_id: str = Field(..., alias="storeId")
    profile_id: str = Field(..., alias="profileId")
    attributes: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class PendingHandoffData(BaseModel):
    """ConversationRelay WebSocket ``end`` message carrying a handoff payload.

    ``handoff_data`` is a JSON *string* (not a nested object) — ConversationRelay
    forwards it verbatim in the POST body to the ``<Connect action>`` URL.
    """

    type: Literal["end"] = "end"
    handoff_data: str = Field(..., alias="handoffData")

    model_config = ConfigDict(populate_by_name=True)
