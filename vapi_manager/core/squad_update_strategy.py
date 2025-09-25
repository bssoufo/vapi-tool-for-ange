"""
Squad Update Strategy

This module provides intelligent squad update capabilities with change detection,
preview functionality, and safe update operations.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from ..services import SquadService, AssistantService
from ..core.squad_config import SquadConfigLoader, SquadBuilder
from ..core.squad_validator import SquadValidator
from ..core.squad_deployment_state import SquadDeploymentStateManager
from ..core.models import SquadUpdateRequest
from ..core.update_strategy import UpdateStrategy, UpdateOptions, UpdateScope


class ChangeType(Enum):
    """Type of change detected."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class SquadChange:
    """Represents a detected change in squad configuration."""
    field: str
    change_type: ChangeType
    old_value: Any = None
    new_value: Any = None
    description: str = ""


@dataclass
class UpdateResult:
    """Result of a squad update operation."""
    status: str  # 'success', 'no_changes', 'preview', 'failed'
    message: str
    squad_id: Optional[str] = None
    changes: List[SquadChange] = None
    total_changes: int = 0
    version: int = 0

    def __post_init__(self):
        if self.changes is None:
            self.changes = []
        self.total_changes = len(self.changes)


class SquadUpdateStrategy:
    """Manages squad updates with validation and change detection."""

    def __init__(self, squads_dir: str = "squads", assistants_dir: str = "assistants"):
        self.squads_dir = squads_dir
        self.assistants_dir = assistants_dir
        self.squad_service = SquadService()
        self.assistant_service = AssistantService()
        self.config_loader = SquadConfigLoader(squads_dir)
        self.squad_builder = SquadBuilder(assistants_dir)
        self.validator = SquadValidator(squads_dir, assistants_dir)
        self.state_manager = SquadDeploymentStateManager(squads_dir)
        self.assistant_update_strategy = UpdateStrategy(assistants_dir)

    async def update_squad(
        self,
        squad_name: str,
        environment: str = "development",
        dry_run: bool = False,
        force: bool = False
    ) -> UpdateResult:
        """
        Update a squad with comprehensive validation and change detection.

        Args:
            squad_name: Name of the squad configuration directory
            environment: Environment to update in
            dry_run: If True, only preview changes without applying
            force: If True, skip change detection and force update

        Returns:
            UpdateResult with operation details
        """
        try:
            # 1. Comprehensive validation
            validation_summary = await self.validator.validate_squad_update_prerequisites(
                squad_name, environment
            )

            if not validation_summary.overall_valid:
                errors = []
                if validation_summary.local_config_valid.errors:
                    errors.extend(validation_summary.local_config_valid.errors)
                if validation_summary.squad_exists.errors:
                    errors.extend(validation_summary.squad_exists.errors)
                if validation_summary.assistants_exist.errors:
                    errors.extend(validation_summary.assistants_exist.errors)

                return UpdateResult(
                    status="failed",
                    message=f"Validation failed: {'; '.join(errors)}"
                )

            # 2. Load current and new configurations
            squad_id = await self.validator.get_squad_id_from_local_config(squad_name, environment)
            current_squad = await self.squad_service.get_squad(squad_id)

            # Load new configuration
            new_config = self.config_loader.load_squad(squad_name, environment)
            new_squad_request = self.squad_builder.build_from_config(new_config, environment)

            # 3. Detect changes
            changes = await self._detect_changes(current_squad, new_squad_request, new_config)

            # 4. Handle no changes scenario - but still update assistants
            if not changes and not force:
                # Even if squad hasn't changed, update the assistants
                assistant_updates = await self._update_squad_assistants(new_config, environment)

                success_msg = f"No changes detected for squad '{squad_name}' in {environment}"
                if assistant_updates:
                    success_msg += f"\nAssistant updates: {', '.join(assistant_updates)}"
                else:
                    success_msg += "\nNo assistant updates were needed"

                return UpdateResult(
                    status="no_changes",
                    message=success_msg,
                    squad_id=squad_id
                )

            # 5. Handle dry run
            if dry_run:
                return UpdateResult(
                    status="preview",
                    message=f"Preview: {len(changes)} changes would be applied to squad '{squad_name}'",
                    squad_id=squad_id,
                    changes=changes
                )

            # 6. Apply the update
            update_request = SquadUpdateRequest(
                name=new_squad_request.name,
                members=new_squad_request.members
            )

            updated_squad = await self.squad_service.update_squad(squad_id, update_request)

            # 7. Update all assistants in the squad
            assistant_updates = await self._update_squad_assistants(new_config, environment)

            # 8. Update deployment state
            self.state_manager.mark_updated(squad_name, environment)
            deployment_info = self.state_manager.get_deployment_info(squad_name, environment)

            # Prepare success message
            success_msg = f"Squad '{squad_name}' updated successfully in {environment}"
            if assistant_updates:
                success_msg += f"\nAssistant updates: {', '.join(assistant_updates)}"

            return UpdateResult(
                status="success",
                message=success_msg,
                squad_id=updated_squad.id,
                changes=changes,
                version=deployment_info.version
            )

        except Exception as e:
            return UpdateResult(
                status="failed",
                message=f"Update failed: {str(e)}"
            )

    async def _detect_changes(
        self,
        current_squad,
        new_squad_request,
        new_config
    ) -> List[SquadChange]:
        """Detect changes between current and new squad configurations."""
        changes = []

        # Compare name
        if current_squad.name != new_squad_request.name:
            changes.append(SquadChange(
                field="name",
                change_type=ChangeType.MODIFIED,
                old_value=current_squad.name,
                new_value=new_squad_request.name,
                description=f"Squad name changed from '{current_squad.name}' to '{new_squad_request.name}'"
            ))

        # Compare members
        member_changes = self._detect_member_changes(current_squad.members, new_squad_request.members)
        changes.extend(member_changes)

        return changes

    def _detect_member_changes(self, current_members, new_members) -> List[SquadChange]:
        """Detect changes in squad members."""
        changes = []

        # Create lookup maps
        current_assistants = {member.assistant_id: member for member in (current_members or [])}
        new_assistants = {member.assistant_id: member for member in (new_members or [])}

        # Find removed members
        for assistant_id in current_assistants:
            if assistant_id not in new_assistants:
                changes.append(SquadChange(
                    field="members",
                    change_type=ChangeType.REMOVED,
                    old_value=assistant_id,
                    description=f"Removed assistant {assistant_id}"
                ))

        # Find added members
        for assistant_id in new_assistants:
            if assistant_id not in current_assistants:
                changes.append(SquadChange(
                    field="members",
                    change_type=ChangeType.ADDED,
                    new_value=assistant_id,
                    description=f"Added assistant {assistant_id}"
                ))

        # Find modified members (destinations or other properties)
        for assistant_id in new_assistants:
            if assistant_id in current_assistants:
                current_member = current_assistants[assistant_id]
                new_member = new_assistants[assistant_id]

                # Compare destinations
                if self._compare_destinations(current_member.assistant_destinations, new_member.assistant_destinations):
                    changes.append(SquadChange(
                        field="members.destinations",
                        change_type=ChangeType.MODIFIED,
                        old_value=len(current_member.assistant_destinations or []),
                        new_value=len(new_member.assistant_destinations or []),
                        description=f"Modified destinations for assistant {assistant_id}"
                    ))

        return changes

    def _compare_destinations(self, current_destinations, new_destinations) -> bool:
        """Compare assistant destinations to detect changes."""
        if (current_destinations is None) != (new_destinations is None):
            return True

        if current_destinations is None and new_destinations is None:
            return False

        if len(current_destinations) != len(new_destinations):
            return True

        # For now, consider any change in destinations as a modification
        # In a more sophisticated implementation, we could compare individual destination properties
        return json.dumps(current_destinations, sort_keys=True) != json.dumps(new_destinations, sort_keys=True)

    async def _update_squad_assistants(self, squad_config, environment: str) -> List[str]:
        """Update all assistants that are part of the squad."""
        updated_assistants = []

        # Get list of assistants from squad members
        members = squad_config.members

        for member in members:
            assistant_name = member.get('assistant_name')
            if not assistant_name:
                continue

            try:
                # Create update options for the assistant
                update_options = UpdateOptions(
                    environment=environment,
                    scope=UpdateScope.FULL,
                    force=True,  # Force update to ensure latest configuration is applied
                    backup=False,
                    dry_run=False
                )

                # Update the assistant using the existing update strategy
                result = await self.assistant_update_strategy.update_assistant(
                    assistant_name,
                    update_options
                )

                if result.get('status') == 'success':
                    updated_assistants.append(assistant_name)
                else:
                    print(f"Warning: Failed to update assistant {assistant_name}: {result.get('message')}")

            except Exception as e:
                print(f"Warning: Error updating assistant {assistant_name}: {str(e)}")

        return updated_assistants

    async def preview_changes(
        self,
        squad_name: str,
        environment: str = "development"
    ) -> UpdateResult:
        """Preview changes without applying them."""
        return await self.update_squad(squad_name, environment, dry_run=True)

    async def get_squad_status(self, squad_name: str) -> Dict[str, Any]:
        """Get current deployment status for a squad."""
        try:
            environments = await self.validator.get_available_environments(squad_name)
            status = {}

            for env in ["development", "staging", "production"]:
                if env in environments:
                    squad_id = await self.validator.get_squad_id_from_local_config(squad_name, env)
                    deployment_info = self.state_manager.get_deployment_info(squad_name, env)
                    status[env] = {
                        "deployed": True,
                        "squad_id": squad_id,
                        "version": deployment_info.version,
                        "deployed_at": deployment_info.deployed_at
                    }
                else:
                    status[env] = {
                        "deployed": False,
                        "squad_id": None,
                        "version": 0,
                        "deployed_at": None
                    }

            return status
        except Exception as e:
            return {"error": str(e)}