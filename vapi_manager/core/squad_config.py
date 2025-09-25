"""
Squad Configuration System

This module provides functionality to load squad configurations from
a structured directory containing YAML files and manage squad deployments.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ..core.models import SquadCreateRequest, SquadMember
from ..core.deployment_state import DeploymentStateManager


@dataclass
class SquadConfig:
    """Represents a complete squad configuration loaded from files."""

    name: str
    base_path: Path
    config: Dict[str, Any]
    members: List[Dict[str, Any]]
    overrides: Dict[str, Any] = None
    routing: Dict[str, Any] = None

    def __post_init__(self):
        if self.overrides is None:
            self.overrides = {}
        if self.routing is None:
            self.routing = {}


class SquadConfigLoader:
    """Loads squad configuration from file structure."""

    def __init__(self, base_dir: str = "squads"):
        self.base_dir = Path(base_dir)

    def load_squad(self, squad_name: str, environment: str = "default") -> SquadConfig:
        """
        Load a squad configuration from its directory.

        Args:
            squad_name: Name of the squad directory
            environment: Environment to use for overrides

        Returns:
            SquadConfig object with all loaded data
        """
        squad_path = self.base_dir / squad_name

        if not squad_path.exists():
            raise FileNotFoundError(f"Squad directory not found: {squad_path}")

        # Load main configuration
        config = self._load_config_file(squad_path / "squad.yaml", environment)

        # Load members configuration
        members = self._load_members_file(squad_path / "members.yaml")

        # Load optional overrides
        overrides = self._load_overrides(squad_path / "overrides")

        # Load optional routing
        routing = self._load_routing(squad_path / "routing")

        return SquadConfig(
            name=squad_name,
            base_path=squad_path,
            config=config,
            members=members,
            overrides=overrides,
            routing=routing
        )

    def _load_config_file(self, file_path: Path, environment: str) -> Dict[str, Any]:
        """Load and parse YAML configuration file with environment overrides."""
        if not file_path.exists():
            return {}

        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        # Apply environment-specific overrides
        if environment != "default" and "environments" in config:
            env_config = config.get("environments", {}).get(environment, {})
            config = self._merge_configs(config, env_config)

        # Remove environments section from final config
        config.pop("environments", None)

        return config

    def _load_members_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load members configuration from YAML file."""
        if not file_path.exists():
            return []

        with open(file_path, 'r', encoding='utf-8') as f:
            members_config = yaml.safe_load(f) or {}

        return members_config.get("members", [])

    def _load_overrides(self, overrides_dir: Path) -> Dict[str, Any]:
        """Load override configurations from the overrides directory."""
        overrides = {}

        if not overrides_dir.exists():
            return overrides

        for file_path in overrides_dir.glob("*.yaml"):
            override_name = file_path.stem
            with open(file_path, 'r', encoding='utf-8') as f:
                overrides[override_name] = yaml.safe_load(f)

        return overrides

    def _load_routing(self, routing_dir: Path) -> Dict[str, Any]:
        """Load routing configurations from the routing directory."""
        routing = {}

        if not routing_dir.exists():
            return routing

        for file_path in routing_dir.glob("*.yaml"):
            routing_name = file_path.stem
            with open(file_path, 'r', encoding='utf-8') as f:
                routing[routing_name] = yaml.safe_load(f)

        return routing

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def list_squads(self) -> List[str]:
        """List all available squad configurations."""
        if not self.base_dir.exists():
            return []

        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]

    def validate_config(self, config: SquadConfig) -> bool:
        """Validate that a squad configuration has required fields."""
        required_fields = ['name']

        for field in required_fields:
            if field not in config.config:
                return False

        # Validate that members are present
        if not config.members:
            return False

        return True


class SquadBuilder:
    """Builds VAPI Squad objects from configuration."""

    def __init__(self, assistants_dir: str = "assistants"):
        self.assistants_dir = Path(assistants_dir)
        self.deployment_state = DeploymentStateManager(assistants_dir)

    def build_from_config(self, config: SquadConfig, environment: str = "development") -> SquadCreateRequest:
        """
        Build a VAPI SquadCreateRequest from a SquadConfig.

        Args:
            config: SquadConfig object with loaded configuration
            environment: Environment to resolve assistant IDs for

        Returns:
            SquadCreateRequest ready to send to VAPI API
        """
        squad_config = config.config

        # Build squad members
        members = self._build_members(config.members, config.overrides, environment)

        # Create the squad request
        # Use the actual squad name (directory name) instead of template placeholder
        squad_name = config.name  # This is the directory name

        # Only use squad_config name if it's not a template placeholder
        config_name = squad_config.get('name', '')
        if not config_name.startswith('{{') and config_name:
            squad_name = config_name

        request = SquadCreateRequest(
            name=squad_name,
            members=members
        )

        return request

    def _build_members(self, members_config: List[Dict[str, Any]], overrides: Dict[str, Any], environment: str) -> List[SquadMember]:
        """Build squad members from configuration."""
        members = []

        for member_config in members_config:
            assistant_name = member_config.get('assistant_name')
            if not assistant_name:
                continue

            # Resolve assistant ID from deployment state
            assistant_id = self._resolve_assistant_id(assistant_name, environment)
            if not assistant_id:
                raise ValueError(f"Assistant '{assistant_name}' not deployed to {environment}")

            # Build assistant destinations
            destinations = self._build_destinations(member_config.get('destinations', []), environment)

            # Build assistant overrides
            assistant_overrides = self._build_assistant_overrides(member_config, overrides)

            # Create base member data
            member_data = {
                'assistantId': assistant_id,
            }

            # Add destinations if present
            if destinations:
                member_data['assistantDestinations'] = destinations

            # Add overrides if present
            if assistant_overrides:
                member_data['assistantOverrides'] = assistant_overrides

            # Create squad member
            member = SquadMember.model_validate(member_data)

            members.append(member)

        return members

    def _resolve_assistant_id(self, assistant_name: str, environment: str) -> Optional[str]:
        """Resolve assistant name to VAPI ID from deployment state."""
        try:
            deployment_info = self.deployment_state.get_deployment_info(assistant_name, environment)
            return deployment_info.id if deployment_info.is_deployed() else None
        except FileNotFoundError:
            return None

    def _build_destinations(self, destinations_config: List[Dict[str, Any]], environment: str) -> List[Dict[str, Any]]:
        """Build assistant destinations from configuration."""
        destinations = []

        for dest_config in destinations_config:
            dest_type = dest_config.get('type')

            if dest_type == 'assistant':
                # Resolve assistant destination
                assistant_name = dest_config.get('assistant_name')
                if assistant_name:
                    assistant_id = self._resolve_assistant_id(assistant_name, environment)
                    if assistant_id:
                        destination = {
                            'type': 'assistant',
                            'assistantName': assistant_name,
                            'transferMode': 'rolling-history'  # Required by VAPI
                        }

                        # Always set message to empty string to prevent VAPI default messages
                        destination['message'] = ''

                        # Include description if present (VAPI supports this)
                        if 'description' in dest_config:
                            destination['description'] = dest_config['description']

                        # Note: VAPI API does not support conditions, keywords, intent, priority
                        # These are used for routing logic in the YAML but not sent to VAPI

                        destinations.append(destination)

            # Note: VAPI API currently only supports 'assistant' type destinations
            # Phone number destinations are not supported in the current API schema

        return destinations

    def _build_assistant_overrides(self, member_config: Dict[str, Any], global_overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Build assistant overrides for the squad member."""
        overrides = {}

        # Start with global default overrides
        if 'default_overrides' in global_overrides:
            overrides.update(global_overrides['default_overrides'])

        # Apply member-specific overrides
        if 'overrides' in member_config:
            overrides.update(member_config['overrides'])

        return overrides

    def _replace_env_vars(self, value: str) -> str:
        """Replace environment variable placeholders in strings."""
        if not isinstance(value, str):
            return value

        import re
        pattern = r'\$\{([^}]+)\}'

        def replacer(match):
            env_var = match.group(1)
            return os.environ.get(env_var, match.group(0))

        return re.sub(pattern, replacer, value)