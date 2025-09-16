"""
Squad Update Validation System

This module provides comprehensive validation for squad updates to ensure
all dependencies exist before attempting to update a squad in VAPI.
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from ..services import SquadService, AssistantService
from ..core.squad_deployment_state import SquadDeploymentStateManager
from ..core.deployment_state import DeploymentStateManager


@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class SquadValidationSummary:
    """Complete validation summary for squad update."""
    squad_exists: ValidationResult
    assistants_exist: ValidationResult
    local_config_valid: ValidationResult
    overall_valid: bool
    missing_assistants: List[str] = None

    def __post_init__(self):
        if self.missing_assistants is None:
            self.missing_assistants = []


class SquadValidator:
    """Validates squad update prerequisites."""

    def __init__(self, squads_dir: str = "squads", assistants_dir: str = "assistants"):
        self.squads_dir = squads_dir
        self.assistants_dir = assistants_dir
        self.squad_service = SquadService()
        self.assistant_service = AssistantService()
        self.squad_state_manager = SquadDeploymentStateManager(squads_dir)
        self.assistant_state_manager = DeploymentStateManager(assistants_dir)

    async def validate_squad_update_prerequisites(
        self,
        squad_name: str,
        environment: str = "development"
    ) -> SquadValidationSummary:
        """
        Comprehensive validation before squad update.

        Args:
            squad_name: Name of the squad configuration directory
            environment: Environment to validate against

        Returns:
            SquadValidationSummary with all validation results
        """
        # 1. Validate local squad configuration exists
        local_config_result = self._validate_local_squad_config(squad_name)

        # 2. Validate squad exists in VAPI
        squad_exists_result = await self._validate_squad_exists_in_vapi(squad_name, environment)

        # 3. Validate all required assistants exist in VAPI
        assistants_result = await self._validate_assistants_exist_in_vapi(squad_name, environment)

        # Determine overall validity
        overall_valid = (
            local_config_result.is_valid and
            squad_exists_result.is_valid and
            assistants_result.is_valid
        )

        return SquadValidationSummary(
            squad_exists=squad_exists_result,
            assistants_exist=assistants_result,
            local_config_valid=local_config_result,
            overall_valid=overall_valid,
            missing_assistants=assistants_result.errors or []
        )

    def _validate_local_squad_config(self, squad_name: str) -> ValidationResult:
        """Validate that local squad configuration exists and is valid."""
        try:
            # Check if squad directory exists
            if not self.squad_state_manager.validate_squad_exists(squad_name):
                return ValidationResult(
                    is_valid=False,
                    errors=[f"Squad '{squad_name}' configuration not found locally"]
                )

            # Try to load the configuration
            from ..core.squad_config import SquadConfigLoader
            loader = SquadConfigLoader(self.squads_dir)
            config = loader.load_squad(squad_name)

            # Validate configuration
            if not loader.validate_config(config):
                return ValidationResult(
                    is_valid=False,
                    errors=[f"Squad '{squad_name}' configuration is invalid"]
                )

            return ValidationResult(is_valid=True)

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Error validating local config: {str(e)}"]
            )

    async def _validate_squad_exists_in_vapi(self, squad_name: str, environment: str) -> ValidationResult:
        """Validate that the squad exists in VAPI."""
        try:
            # Check if squad is deployed to the environment
            if not self.squad_state_manager.is_deployed(squad_name, environment):
                return ValidationResult(
                    is_valid=False,
                    errors=[f"Squad '{squad_name}' is not deployed to {environment}"]
                )

            # Get the squad ID and verify it exists in VAPI
            deployment_info = self.squad_state_manager.get_deployment_info(squad_name, environment)
            squad_id = deployment_info.id

            # Try to fetch the squad from VAPI
            squad = await self.squad_service.get_squad(squad_id)

            return ValidationResult(is_valid=True)

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Squad not found in VAPI: {str(e)}"]
            )

    async def _validate_assistants_exist_in_vapi(self, squad_name: str, environment: str) -> ValidationResult:
        """Validate that all required assistants exist in VAPI."""
        try:
            # Load squad configuration to get required assistants
            from ..core.squad_config import SquadConfigLoader
            loader = SquadConfigLoader(self.squads_dir)
            config = loader.load_squad(squad_name, environment)

            # Extract required assistant names
            required_assistants = set()
            for member in config.members:
                assistant_name = member.get('assistant_name')
                if assistant_name:
                    required_assistants.add(assistant_name)

            # Validate each assistant exists in VAPI
            missing_assistants = []
            validation_errors = []

            for assistant_name in required_assistants:
                try:
                    # Check if assistant is deployed
                    if not self.assistant_state_manager.is_deployed(assistant_name, environment):
                        missing_assistants.append(assistant_name)
                        validation_errors.append(f"Assistant '{assistant_name}' not deployed to {environment}")
                        continue

                    # Verify assistant exists in VAPI
                    deployment_info = self.assistant_state_manager.get_deployment_info(assistant_name, environment)
                    assistant_id = deployment_info.id

                    # Try to fetch the assistant from VAPI
                    await self.assistant_service.get_assistant(assistant_id)

                except Exception as e:
                    missing_assistants.append(assistant_name)
                    validation_errors.append(f"Assistant '{assistant_name}' validation failed: {str(e)}")

            if validation_errors:
                return ValidationResult(
                    is_valid=False,
                    errors=validation_errors
                )

            return ValidationResult(is_valid=True)

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Error validating assistants: {str(e)}"]
            )

    async def get_squad_id_from_local_config(self, squad_name: str, environment: str) -> Optional[str]:
        """Get VAPI squad ID from local deployment state."""
        try:
            if not self.squad_state_manager.is_deployed(squad_name, environment):
                return None

            deployment_info = self.squad_state_manager.get_deployment_info(squad_name, environment)
            return deployment_info.id
        except:
            return None

    async def get_available_environments(self, squad_name: str) -> List[str]:
        """Get list of environments where squad is deployed."""
        try:
            return self.squad_state_manager.get_deployed_environments(squad_name)
        except:
            return []