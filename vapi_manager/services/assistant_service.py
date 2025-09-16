from typing import List, Optional
from ..core.models import Assistant, AssistantCreateRequest, AssistantUpdateRequest
from ..core.exceptions.vapi_exceptions import AssistantNotFoundError, VAPIAPIError
from .vapi_client import VAPIClient


class AssistantService:
    """Service for managing VAPI assistants."""

    def __init__(self, client: Optional[VAPIClient] = None):
        self.client = client or VAPIClient()

    async def create_assistant(self, request: AssistantCreateRequest) -> Assistant:
        """Create a new assistant."""
        try:
            data = request.model_dump(by_alias=True, exclude_none=True)
            response = await self.client.post("assistant", data)
            return Assistant.model_validate(response)
        except VAPIAPIError as e:
            raise VAPIAPIError(f"Failed to create assistant: {e}") from e

    async def get_assistant(self, assistant_id: str) -> Assistant:
        """Get an assistant by ID."""
        try:
            response = await self.client.get(f"assistant/{assistant_id}")
            return Assistant.model_validate(response)
        except VAPIAPIError as e:
            if e.status_code == 404:
                raise AssistantNotFoundError(f"Assistant {assistant_id} not found") from e
            raise VAPIAPIError(f"Failed to get assistant {assistant_id}: {e}") from e

    async def list_assistants(self, limit: Optional[int] = None) -> List[Assistant]:
        """List all assistants."""
        try:
            params = {}
            if limit:
                params["limit"] = limit

            response = await self.client.get("assistant", params=params)

            # Handle both paginated and direct list responses
            if isinstance(response, dict) and "data" in response:
                assistants_data = response["data"]
            else:
                assistants_data = response

            return [Assistant.model_validate(assistant) for assistant in assistants_data]
        except VAPIAPIError as e:
            raise VAPIAPIError(f"Failed to list assistants: {e}") from e

    async def update_assistant(self, assistant_id: str, request: AssistantUpdateRequest) -> Assistant:
        """Update an existing assistant."""
        try:
            data = request.model_dump(by_alias=True, exclude_none=True)
            response = await self.client.patch(f"assistant/{assistant_id}", data)
            return Assistant.model_validate(response)
        except VAPIAPIError as e:
            if e.status_code == 404:
                raise AssistantNotFoundError(f"Assistant {assistant_id} not found") from e
            raise VAPIAPIError(f"Failed to update assistant {assistant_id}: {e}") from e

    async def delete_assistant(self, assistant_id: str) -> bool:
        """Delete an assistant."""
        try:
            await self.client.delete(f"assistant/{assistant_id}")
            return True
        except VAPIAPIError as e:
            if e.status_code == 404:
                raise AssistantNotFoundError(f"Assistant {assistant_id} not found") from e
            raise VAPIAPIError(f"Failed to delete assistant {assistant_id}: {e}") from e

    async def get_assistants_by_ids(self, assistant_ids: List[str]) -> List[Assistant]:
        """Get multiple assistants by their IDs."""
        assistants = []
        for assistant_id in assistant_ids:
            try:
                assistant = await self.get_assistant(assistant_id)
                assistants.append(assistant)
            except AssistantNotFoundError:
                # Log warning but continue with other assistants
                continue
        return assistants