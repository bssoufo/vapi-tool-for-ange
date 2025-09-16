from typing import List, Optional
from ..core.models import Agent, AgentCreateRequest, AgentUpdateRequest, Squad, SquadCreateRequest, SquadMember
from ..core.exceptions.vapi_exceptions import AgentNotFoundError, ValidationError
from .assistant_service import AssistantService
from .squad_service import SquadService


class AgentService:
    """
    Service for managing Agents (combination of Squad + Assistants).

    An Agent represents a complete conversational unit that contains:
    - One Squad that manages multiple assistants
    - The assistants that belong to that squad
    """

    def __init__(
        self,
        assistant_service: Optional[AssistantService] = None,
        squad_service: Optional[SquadService] = None
    ):
        self.assistant_service = assistant_service or AssistantService()
        self.squad_service = squad_service or SquadService()

    async def create_agent(self, request: AgentCreateRequest) -> Agent:
        """
        Create a new agent with a squad and assign assistants to it.
        """
        if not request.assistant_ids:
            raise ValidationError("Agent must have at least one assistant")

        # Validate that all assistants exist
        assistants = await self.assistant_service.get_assistants_by_ids(request.assistant_ids)
        if len(assistants) != len(request.assistant_ids):
            found_ids = {assistant.id for assistant in assistants}
            missing_ids = set(request.assistant_ids) - found_ids
            raise ValidationError(f"Assistants not found: {missing_ids}")

        # Create squad with the assistants
        squad_members = [
            SquadMember(assistant_id=assistant_id)
            for assistant_id in request.assistant_ids
        ]

        squad_request = SquadCreateRequest(
            name=request.squad_name,
            members=squad_members
        )

        squad = await self.squad_service.create_squad(squad_request)

        # Create the agent object
        agent = Agent(
            name=request.name,
            description=request.description,
            squad=squad,
            assistants=assistants
        )

        return agent

    async def get_agent_by_squad_id(self, squad_id: str) -> Agent:
        """Get an agent by its squad ID."""
        try:
            # Get the squad
            squad = await self.squad_service.get_squad(squad_id)

            # Get all assistants in the squad
            assistant_ids = [member.assistant_id for member in squad.members]
            assistants = await self.assistant_service.get_assistants_by_ids(assistant_ids)

            # Create agent object
            agent = Agent(
                id=squad.id,
                name=squad.name,
                squad=squad,
                assistants=assistants,
                created_at=squad.created_at,
                updated_at=squad.updated_at
            )

            return agent

        except Exception as e:
            raise AgentNotFoundError(f"Agent with squad ID {squad_id} not found: {e}") from e

    async def list_agents(self, limit: Optional[int] = None) -> List[Agent]:
        """List all agents by listing squads and their assistants."""
        squads = await self.squad_service.list_squads(limit=limit)
        agents = []

        for squad in squads:
            try:
                assistant_ids = [member.assistant_id for member in squad.members]
                assistants = await self.assistant_service.get_assistants_by_ids(assistant_ids)

                agent = Agent(
                    id=squad.id,
                    name=squad.name,
                    squad=squad,
                    assistants=assistants,
                    created_at=squad.created_at,
                    updated_at=squad.updated_at
                )
                agents.append(agent)
            except Exception:
                # Skip squads with issues (e.g., deleted assistants)
                continue

        return agents

    async def update_agent(self, squad_id: str, request: AgentUpdateRequest) -> Agent:
        """Update an agent (squad and/or assistants)."""
        # Get current agent
        agent = await self.get_agent_by_squad_id(squad_id)

        # Prepare squad update
        squad_update_data = {}

        if request.name:
            squad_update_data["name"] = request.name
        elif request.squad_name:
            squad_update_data["name"] = request.squad_name

        if request.assistant_ids is not None:
            # Validate new assistants exist
            if request.assistant_ids:  # If not empty list
                assistants = await self.assistant_service.get_assistants_by_ids(request.assistant_ids)
                if len(assistants) != len(request.assistant_ids):
                    found_ids = {assistant.id for assistant in assistants}
                    missing_ids = set(request.assistant_ids) - found_ids
                    raise ValidationError(f"Assistants not found: {missing_ids}")

            # Update squad members
            squad_members = [
                SquadMember(assistant_id=assistant_id)
                for assistant_id in request.assistant_ids
            ]
            squad_update_data["members"] = squad_members

        if squad_update_data:
            from ..core.models import SquadUpdateRequest
            squad_update_request = SquadUpdateRequest(**squad_update_data)
            updated_squad = await self.squad_service.update_squad(squad_id, squad_update_request)

            # Get updated assistants
            assistant_ids = [member.assistant_id for member in updated_squad.members]
            assistants = await self.assistant_service.get_assistants_by_ids(assistant_ids)

            # Return updated agent
            return Agent(
                id=updated_squad.id,
                name=updated_squad.name,
                description=request.description or agent.description,
                squad=updated_squad,
                assistants=assistants,
                created_at=updated_squad.created_at,
                updated_at=updated_squad.updated_at
            )

        return agent

    async def delete_agent(self, squad_id: str) -> bool:
        """Delete an agent (deletes the squad, assistants remain)."""
        return await self.squad_service.delete_squad(squad_id)

    async def add_assistant_to_agent(self, squad_id: str, assistant_id: str) -> Agent:
        """Add an assistant to an agent's squad."""
        updated_squad = await self.squad_service.add_assistant_to_squad(squad_id, assistant_id)
        return await self.get_agent_by_squad_id(updated_squad.id)

    async def remove_assistant_from_agent(self, squad_id: str, assistant_id: str) -> Agent:
        """Remove an assistant from an agent's squad."""
        updated_squad = await self.squad_service.remove_assistant_from_squad(squad_id, assistant_id)
        return await self.get_agent_by_squad_id(updated_squad.id)