"""Options for configuring adapter behavior."""

from pydantic import BaseModel, Field


class AdapterOptions(BaseModel):
    """Options for configuring how adapters inject memory and profile data.

    Example:
        # Default behavior (no options) - inject ALL profile traits
        client = with_tac_memory(openai_client, memory_response, context)

        # Default behavior (options but no profile_traits specified) - inject ALL profile traits
        options = AdapterOptions()
        client = with_tac_memory(openai_client, memory_response, context, options=options)

        # Explicitly exclude all profile traits
        options = AdapterOptions(profile_traits=None)
        client = with_tac_memory(openai_client, memory_response, context, options=options)
        # or
        options = AdapterOptions(profile_traits=[])
        client = with_tac_memory(openai_client, memory_response, context, options=options)

        # Specific traits only
        options = AdapterOptions(profile_traits=["Contact", "Preferences"])
        client = with_tac_memory(openai_client, memory_response, context, options=options)
    """

    profile_traits: list[str] | None = Field(
        default=None,
        description=(
            "List of trait groups to include in profile injection. "
            "If not provided (field not set), ALL traits are included. "
            "If None or empty list [], no profile traits are included. "
            "If list of trait names, only those specific traits are included."
        ),
    )

    def get_profile_traits(self) -> list[str] | None:
        """Get the profile traits to include.

        Returns:
            None to include all traits (when field not set),
            empty list to exclude all (when explicitly set to None or []),
            or list of specific trait group names to include.
        """
        # Check if the field was explicitly set
        if "profile_traits" not in self.model_fields_set:
            # Field not provided - use all traits
            return None

        # Field was explicitly set
        if self.profile_traits is None or self.profile_traits == []:
            # Explicitly set to None or empty list - exclude all traits
            return []

        # Specific traits provided
        return self.profile_traits
