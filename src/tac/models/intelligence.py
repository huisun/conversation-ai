"""Models for Conversation Intelligence webhook events."""

from typing import Any

from pydantic import BaseModel, Field


class IntelligenceConfiguration(BaseModel):
    """Intelligence configuration details from the CI service."""

    id: str = Field(
        ...,
        description="Unique Identifier for IntelligenceConfiguration (TTID)",
        json_schema_extra={"example": "GA00000000000000000000000000000000"},
    )
    friendly_name: str | None = Field(
        default=None,
        alias="friendlyName",
        description="Unique name of the intelligence configuration",
        json_schema_extra={"example": "CONVERSATION_MEMORY_mem_store_00000000000000000000000000"},
    )
    version: int = Field(
        ...,
        description="Version of the IntelligenceConfiguration used",
        json_schema_extra={"example": 1},
    )
    rule_id: str | None = Field(
        default=None,
        alias="ruleId",
        description="Id of the associated rule",
        json_schema_extra={"example": "rule_00000000000000000000000000"},
    )

    model_config = {"populate_by_name": True}


class Operator(BaseModel):
    """Operator details from the CI service."""

    id: str | None = Field(
        default=None,
        description="Operator Sid (Sid<LY>) or TTID",
        json_schema_extra={"example": "LY00000000000000000000000000000000"},
    )
    friendly_name: str | None = Field(
        default=None,
        alias="friendlyName",
        description="Operator Friendly Name",
        json_schema_extra={"example": "Summary Extractor"},
    )
    version: int | None = Field(
        default=None,
        description="Version of the Operator used",
        json_schema_extra={"example": 1},
    )
    parameters: dict[str, str] | None = Field(
        default=None,
        description="Snapshot of the parameters passed to the Operator as key/value pairs",
        json_schema_extra={"example": {"param1": "value1"}},
    )

    model_config = {"populate_by_name": True}


class TriggerDetails(BaseModel):
    """Trigger details for the operator execution."""

    on: str | None = Field(
        default=None,
        description="Trigger type (e.g., utterance, conversation_closed)",
        json_schema_extra={"example": "conversation_closed"},
    )
    timestamp: str | None = Field(
        default=None,
        description="Trigger timestamp (ISO-8601)",
        json_schema_extra={"example": "2025-01-15T10:30:45Z"},
    )

    model_config = {"populate_by_name": True}


class CommunicationsRange(BaseModel):
    """Range of communications used in the operator execution."""

    first: str | None = Field(
        default=None,
        description="Starting Communication ID TTID of Operator Execution",
        json_schema_extra={"example": "comms_communication_00000000000000000000000000"},
    )
    last: str | None = Field(
        default=None,
        description="Ending Communication ID TTID of Operator Execution",
        json_schema_extra={"example": "comms_communication_00000000000000000000000001"},
    )

    model_config = {"populate_by_name": True}


class Participant(BaseModel):
    """Participant in a conversation."""

    id: str = Field(
        ...,
        description="Participant ID TTID",
        json_schema_extra={"example": "comms_participant_00000000000000000000000000"},
    )
    profile_id: str | None = Field(
        default=None,
        alias="profileId",
        description="Conversation Memory profile id of the participant",
        json_schema_extra={"example": "mem_profile_00000000000000000000000000"},
    )
    type: str | None = Field(
        default=None,
        description="Type of participant (e.g., HUMAN_AGENT, CUSTOMER, AI_AGENT)",
        json_schema_extra={"example": "CUSTOMER"},
    )

    model_config = {"populate_by_name": True}


class ExecutionDetails(BaseModel):
    """Execution context details for the operator result."""

    trigger: TriggerDetails | None = Field(
        default=None,
        description="Trigger details",
    )
    communications: CommunicationsRange | None = Field(
        default=None,
        description="Range of communications used",
    )
    channels: list[str] | None = Field(
        default=None,
        description="List of unique channels in a conversation (e.g., Voice, SMS, Email)",
        json_schema_extra={"example": ["SMS", "Voice"]},
    )
    participants: list[Participant] | None = Field(
        default=None,
        description="Participants involved in the conversation",
    )
    context: dict[str, str] | None = Field(
        default=None,
        description="Additional execution context key/value pairs",
        json_schema_extra={"example": {"key1": "value1"}},
    )

    model_config = {"populate_by_name": True}


# Result types for different output formats


class ClassificationResult(BaseModel):
    """Result for Text-Classification output format."""

    label: str = Field(
        ...,
        description="Predicted classification label",
        json_schema_extra={"example": "positive"},
    )

    model_config = {"populate_by_name": True}


class ExtractionEntity(BaseModel):
    """An extracted entity from Text-Extraction."""

    communication_id: str | None = Field(
        default=None,
        alias="communicationId",
        description="Communication context identifier",
        json_schema_extra={"example": "comms_communication_00000000000000000000000000"},
    )
    begin_offset: int | None = Field(
        default=None,
        alias="beginOffset",
        description="Starting character offset",
        json_schema_extra={"example": 0},
    )
    end_offset: int | None = Field(
        default=None,
        alias="endOffset",
        description="Ending character offset",
        json_schema_extra={"example": 10},
    )
    label: str = Field(
        ...,
        description="Entity label/type",
        json_schema_extra={"example": "PERSON"},
    )
    text: str = Field(
        ...,
        description="Extracted text",
        json_schema_extra={"example": "John Doe"},
    )

    model_config = {"populate_by_name": True}


class ExtractionResult(BaseModel):
    """Result for Text-Extraction output format."""

    entities: list[ExtractionEntity] = Field(
        ...,
        description="List of extracted entities",
    )

    model_config = {"populate_by_name": True}


class TextGenerationResult(BaseModel):
    """Result for Text-Generation output format."""

    result: str = Field(
        ...,
        description="Generated text output",
        json_schema_extra={"example": "The customer expressed satisfaction with the product."},
    )
    format: str | None = Field(
        default=None,
        description="Format of generated result. Allowed: text",
        json_schema_extra={"example": "text"},
    )

    model_config = {"populate_by_name": True}


class JSONResult(BaseModel):
    """Result for JSON output format."""

    payload: str = Field(
        ...,
        description="Arbitrary JSON payload serialized as a string",
        json_schema_extra={
            "example": '{"observations": [{"content": "Customer prefers email contact"}]}'
        },
    )

    model_config = {"populate_by_name": True}


class OperatorProcessingResult(BaseModel):
    """Result of processing a Conversation Intelligence webhook event."""

    success: bool = Field(
        ...,
        description="Whether processing completed successfully",
    )
    event_type: str | None = Field(
        default=None,
        description="Type of event processed: 'observation', 'summary', or None if filtered/failed",
    )
    skipped: bool = Field(
        default=False,
        description="True if event was filtered out (not an error)",
    )
    skip_reason: str | None = Field(
        default=None,
        description="Reason for skipping (e.g., 'non-conversation-memory event')",
    )
    error: str | None = Field(
        default=None,
        description="Error message if processing failed",
    )
    created_count: int = Field(
        default=0,
        description="Number of observations/summaries created",
    )

    model_config = {"populate_by_name": True}


class OperatorResult(BaseModel):
    """Individual operator result from a CI webhook event.

    This model represents a single operator result within the operatorResults array.
    """

    id: str = Field(
        ...,
        description="Unique Identifier for Operator Results (TTID)",
        json_schema_extra={"example": "intelligence_operatorresult_00000000000000000000000000"},
    )
    operator: Operator = Field(
        ...,
        description="Operator details",
    )
    output_format: str = Field(
        ...,
        alias="outputFormat",
        description="Output format. Allowed values: CLASSIFICATION, EXTRACTION, GENERATION, JSON",
        json_schema_extra={"example": "JSON"},
    )
    result: Any = Field(
        ...,
        description="Polymorphic operator result based on outputFormat",
    )
    date_created: str = Field(
        ...,
        alias="dateCreated",
        description="Creation timestamp (ISO-8601)",
        json_schema_extra={"example": "2025-01-15T10:30:45Z"},
    )
    reference_ids: list[str] = Field(
        default_factory=list,
        alias="referenceIds",
        description="Reference Ids for easier integration with Segment, Insights etc.",
        json_schema_extra={"example": ["ref_001", "ref_002"]},
    )
    execution_details: ExecutionDetails = Field(
        ...,
        alias="executionDetails",
        description="Execution context details",
    )

    model_config = {"populate_by_name": True}


class OperatorResultEvent(BaseModel):
    """Operator result event from Conversation Intelligence webhook.

    This model represents the webhook payload received from the CI service.
    It contains metadata about the conversation and an array of operator results.
    """

    account_id: str = Field(
        ...,
        alias="accountId",
        description="Twilio Account SID (Sid<AC>)",
        json_schema_extra={"example": "AC00000000000000000000000000000000"},
    )
    conversation_id: str = Field(
        ...,
        alias="conversationId",
        description="Conversation ID (TTID) associated with the execution",
        json_schema_extra={"example": "conv_conversation_00000000000000000000000000"},
    )
    memory_store_id: str | None = Field(
        default=None,
        alias="memoryStoreId",
        description="Memory store id",
        json_schema_extra={"example": "mem_store_00000000000000000000000000"},
    )
    intelligence_configuration: IntelligenceConfiguration = Field(
        ...,
        alias="intelligenceConfiguration",
        description="Intelligence configuration details",
    )
    operator_results: list[OperatorResult] = Field(
        ...,
        alias="operatorResults",
        description="List of operator results from this event",
    )

    model_config = {"populate_by_name": True}
