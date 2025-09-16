"""
Deployment State Management for VAPI Assistants

This module manages the deployment state and lifecycle of assistants,
tracking their VAPI IDs and deployment history across environments.
"""

import os
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .assistant_config import AssistantConfig


@dataclass
class DeploymentInfo:
    """Information about a specific deployment."""
    id: Optional[str] = None
    deployed_at: Optional[str] = None
    deployed_by: Optional[str] = None
    version: int = 0

    def is_deployed(self) -> bool:
        """Check if this deployment has a valid VAPI ID."""
        return self.id is not None and self.id != ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeploymentInfo':
        """Create DeploymentInfo from dictionary."""
        if not data:
            return cls()

        return cls(
            id=data.get('id'),
            deployed_at=data.get('deployed_at'),
            deployed_by=data.get('deployed_by'),
            version=data.get('version', 0)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            'id': self.id,
            'deployed_at': self.deployed_at,
            'deployed_by': self.deployed_by,
            'version': self.version
        }


class DeploymentStateManager:
    """Manages deployment state for VAPI assistants."""

    def __init__(self, assistants_dir: str = "assistants"):
        self.assistants_dir = Path(assistants_dir)

    def get_config_path(self, assistant_name: str) -> Path:
        """Get the path to assistant's configuration file."""
        return self.assistants_dir / assistant_name / "assistant.yaml"

    def load_deployment_state(self, assistant_name: str) -> Dict[str, Any]:
        """Load the full _vapi state section from assistant config."""
        config_path = self.get_config_path(assistant_name)

        if not config_path.exists():
            raise FileNotFoundError(f"Assistant config not found: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        # Initialize _vapi section if it doesn't exist
        if '_vapi' not in config:
            config['_vapi'] = self._create_empty_vapi_section()

        return config.get('_vapi', {})

    def save_deployment_state(self, assistant_name: str, vapi_state: Dict[str, Any]):
        """Save the _vapi state section back to the assistant config."""
        config_path = self.get_config_path(assistant_name)

        if not config_path.exists():
            raise FileNotFoundError(f"Assistant config not found: {config_path}")

        # Load current config
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        # Update _vapi section
        config['_vapi'] = vapi_state

        # Save back to file
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    def get_deployment_info(self, assistant_name: str, environment: str) -> DeploymentInfo:
        """Get deployment info for a specific environment."""
        vapi_state = self.load_deployment_state(assistant_name)
        env_data = vapi_state.get('environments', {}).get(environment, {})
        return DeploymentInfo.from_dict(env_data)

    def is_deployed(self, assistant_name: str, environment: str) -> bool:
        """Check if assistant is deployed in the specified environment."""
        try:
            deployment_info = self.get_deployment_info(assistant_name, environment)
            return deployment_info.is_deployed()
        except FileNotFoundError:
            return False

    def mark_deployed(
        self,
        assistant_name: str,
        environment: str,
        vapi_id: str,
        deployed_by: Optional[str] = None
    ):
        """Mark an assistant as deployed in the specified environment."""
        vapi_state = self.load_deployment_state(assistant_name)

        # Ensure environments section exists
        if 'environments' not in vapi_state:
            vapi_state['environments'] = {}

        if environment not in vapi_state['environments']:
            vapi_state['environments'][environment] = {}

        # Get current version and increment
        current_version = vapi_state['environments'][environment].get('version', 0)

        # Update deployment info
        vapi_state['environments'][environment] = {
            'id': vapi_id,
            'deployed_at': datetime.now(timezone.utc).isoformat(),
            'deployed_by': deployed_by or self._get_current_user(),
            'version': current_version + 1
        }

        # Update current environment and sync time
        vapi_state['current_environment'] = environment
        vapi_state['last_sync'] = datetime.now(timezone.utc).isoformat()

        # Save state
        self.save_deployment_state(assistant_name, vapi_state)

    def mark_undeployed(self, assistant_name: str, environment: str):
        """Mark an assistant as not deployed (clear deployment info)."""
        vapi_state = self.load_deployment_state(assistant_name)

        if 'environments' in vapi_state and environment in vapi_state['environments']:
            # Reset to undeployed state
            vapi_state['environments'][environment] = {
                'id': None,
                'deployed_at': None,
                'deployed_by': None,
                'version': 0
            }

            # Update sync time
            vapi_state['last_sync'] = datetime.now(timezone.utc).isoformat()

            # Clear current environment if it was this environment
            if vapi_state.get('current_environment') == environment:
                vapi_state['current_environment'] = None

            # Save state
            self.save_deployment_state(assistant_name, vapi_state)

    def mark_updated(
        self,
        assistant_name: str,
        environment: str,
        deployed_by: Optional[str] = None
    ):
        """Mark an assistant as updated in the specified environment (increment version)."""
        vapi_state = self.load_deployment_state(assistant_name)

        # Ensure environment exists
        if 'environments' not in vapi_state or environment not in vapi_state['environments']:
            raise ValueError(f"Assistant {assistant_name} not deployed to {environment}")

        env_data = vapi_state['environments'][environment]
        if not env_data.get('id'):
            raise ValueError(f"Assistant {assistant_name} not deployed to {environment}")

        # Update deployment info - keep existing ID but increment version
        current_version = env_data.get('version', 0)
        vapi_state['environments'][environment].update({
            'deployed_at': datetime.now(timezone.utc).isoformat(),
            'deployed_by': deployed_by or self._get_current_user(),
            'version': current_version + 1
        })

        # Update global state
        vapi_state['current_environment'] = environment
        vapi_state['last_sync'] = datetime.now(timezone.utc).isoformat()

        # Save updated state
        self.save_deployment_state(assistant_name, vapi_state)

    def get_all_deployments(self, assistant_name: str) -> Dict[str, DeploymentInfo]:
        """Get deployment info for all environments."""
        vapi_state = self.load_deployment_state(assistant_name)
        environments = vapi_state.get('environments', {})

        result = {}
        for env, data in environments.items():
            result[env] = DeploymentInfo.from_dict(data)

        return result

    def get_deployed_environments(self, assistant_name: str) -> List[str]:
        """Get list of environments where assistant is currently deployed."""
        deployments = self.get_all_deployments(assistant_name)
        return [env for env, info in deployments.items() if info.is_deployed()]

    def list_all_assistants(self) -> List[str]:
        """List all assistants with configuration files."""
        if not self.assistants_dir.exists():
            return []

        assistants = []
        for assistant_dir in self.assistants_dir.iterdir():
            if assistant_dir.is_dir() and (assistant_dir / "assistant.yaml").exists():
                assistants.append(assistant_dir.name)

        return sorted(assistants)

    def get_deployment_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get deployment summary for all assistants."""
        summary = {}

        for assistant_name in self.list_all_assistants():
            try:
                deployments = self.get_all_deployments(assistant_name)
                deployed_envs = [env for env, info in deployments.items() if info.is_deployed()]

                summary[assistant_name] = {
                    'deployed_environments': deployed_envs,
                    'total_deployments': len(deployed_envs),
                    'environments': {env: info.to_dict() for env, info in deployments.items()}
                }
            except Exception:
                # Skip assistants with invalid configs
                continue

        return summary

    def _create_empty_vapi_section(self) -> Dict[str, Any]:
        """Create an empty _vapi section with default structure."""
        return {
            'environments': {
                'development': {'id': None, 'deployed_at': None, 'deployed_by': None, 'version': 0},
                'staging': {'id': None, 'deployed_at': None, 'deployed_by': None, 'version': 0},
                'production': {'id': None, 'deployed_at': None, 'deployed_by': None, 'version': 0}
            },
            'current_environment': None,
            'last_sync': None
        }

    def _get_current_user(self) -> str:
        """Get current user for deployment tracking."""
        return os.environ.get('USER') or os.environ.get('USERNAME') or 'unknown'

    def validate_assistant_exists(self, assistant_name: str) -> bool:
        """Validate that an assistant configuration exists."""
        return self.get_config_path(assistant_name).exists()

    def backup_state(self, assistant_name: str) -> str:
        """Create a backup of the current state and return backup path."""
        config_path = self.get_config_path(assistant_name)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = config_path.with_suffix(f'.backup_{timestamp}.yaml')

        import shutil
        shutil.copy2(config_path, backup_path)

        return str(backup_path)