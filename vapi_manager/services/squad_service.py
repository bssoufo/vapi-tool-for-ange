from typing import List, Optional
from ..core.models import Squad, SquadCreateRequest, SquadUpdateRequest, SquadMember
from ..core.exceptions.vapi_exceptions import SquadNotFoundError, VAPIAPIError
from .vapi_client import VAPIClient


class SquadService:
    """Service for managing VAPI squads."""

    def __init__(self, client: Optional[VAPIClient] = None, verbose: bool = False):
        self.client = client or VAPIClient(verbose=verbose)

    async def create_squad(self, request: SquadCreateRequest) -> Squad:
        """Create a new squad."""
        try:
            data = request.model_dump(by_alias=True, exclude_none=True)
            response = await self.client.post("squad", data)
            return Squad.model_validate(response)
        except VAPIAPIError as e:
            raise VAPIAPIError(f"Failed to create squad: {e}") from e

    async def get_squad(self, squad_id: str) -> Squad:
        """Get a squad by ID."""
        try:
            response = await self.client.get(f"squad/{squad_id}")
            return Squad.model_validate(response)
        except VAPIAPIError as e:
            if e.status_code == 404:
                raise SquadNotFoundError(f"Squad {squad_id} not found") from e
            raise VAPIAPIError(f"Failed to get squad {squad_id}: {e}") from e

    async def list_squads(self, limit: Optional[int] = None) -> List[Squad]:
        """List all squads."""
        try:
            params = {}
            if limit:
                params["limit"] = limit

            response = await self.client.get("squad", params=params)

            # Handle both paginated and direct list responses
            if isinstance(response, dict) and "data" in response:
                squads_data = response["data"]
            else:
                squads_data = response

            return [Squad.model_validate(squad) for squad in squads_data]
        except VAPIAPIError as e:
            raise VAPIAPIError(f"Failed to list squads: {e}") from e

    async def update_squad(self, squad_id: str, request: SquadUpdateRequest) -> Squad:
        """Update an existing squad."""
        try:
            data = request.model_dump(by_alias=True, exclude_none=True)
            response = await self.client.patch(f"squad/{squad_id}", data)
            return Squad.model_validate(response)
        except VAPIAPIError as e:
            if e.status_code == 404:
                raise SquadNotFoundError(f"Squad {squad_id} not found") from e
            raise VAPIAPIError(f"Failed to update squad {squad_id}: {e}") from e

    async def delete_squad(self, squad_id: str) -> bool:
        """Delete a squad."""
        try:
            await self.client.delete(f"squad/{squad_id}")
            return True
        except VAPIAPIError as e:
            if e.status_code == 404:
                raise SquadNotFoundError(f"Squad {squad_id} not found") from e
            raise VAPIAPIError(f"Failed to delete squad {squad_id}: {e}") from e

    async def add_assistant_to_squad(self, squad_id: str, assistant_id: str) -> Squad:
        """Add an assistant to a squad."""
        squad = await self.get_squad(squad_id)

        # Check if assistant is already in the squad
        for member in squad.members:
            if member.assistant_id == assistant_id:
                return squad  # Assistant already in squad

        # Add new member
        new_member = SquadMember(assistant_id=assistant_id)
        squad.members.append(new_member)

        # Update the squad
        update_request = SquadUpdateRequest(members=squad.members)
        return await self.update_squad(squad_id, update_request)

    async def remove_assistant_from_squad(self, squad_id: str, assistant_id: str) -> Squad:
        """Remove an assistant from a squad."""
        squad = await self.get_squad(squad_id)

        # Remove the assistant from members
        squad.members = [
            member for member in squad.members
            if member.assistant_id != assistant_id
        ]

        # Update the squad
        update_request = SquadUpdateRequest(members=squad.members)
        return await self.update_squad(squad_id, update_request)