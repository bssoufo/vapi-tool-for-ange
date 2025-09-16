"""
Squad Deployment State Management

This module manages the deployment state and lifecycle of squads,
tracking their VAPI IDs and deployment history across environments.
"""

import os
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .deployment_state import DeploymentInfo


class SquadDeploymentStateManager:
    """Manages deployment state for squads."""

    def __init__(self, base_dir: str = "squads"):
        self.base_dir = Path(base_dir)

    def get_config_path(self, squad_name: str) -> Path:
        """Get the path to the squad's configuration file."""
        return self.base_dir / squad_name / "squad.yaml"

    def validate_squad_exists(self, squad_name: str) -> bool:
        """Check if a squad configuration exists."""
        config_path = self.get_config_path(squad_name)
        return config_path.exists()

    def load_deployment_state(self, squad_name: str) -> Dict[str, Any]:
        """Load the _vapi deployment state section from squad config."""
        config_path = self.get_config_path(squad_name)

        if not config_path.exists():
            raise FileNotFoundError(f"Squad config not found: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        # Return _vapi section or initialize empty structure
        return config.get('_vapi', {
            'environments': {
                'development': {'id': None, 'deployed_at': None, 'deployed_by': None, 'version': 0},
                'staging': {'id': None, 'deployed_at': None, 'deployed_by': None, 'version': 0},
                'production': {'id': None, 'deployed_at': None, 'deployed_by': None, 'version': 0}
            },
            'current_environment': None,
            'last_sync': None
        })

    def save_deployment_state(self, squad_name: str, vapi_state: Dict[str, Any]):
        """Save the _vapi state section back to the squad config."""
        config_path = self.get_config_path(squad_name)

        if not config_path.exists():
            raise FileNotFoundError(f"Squad config not found: {config_path}")

        # Load current config
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        # Update _vapi section
        config['_vapi'] = vapi_state

        # Save back to file
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    def get_deployment_info(self, squad_name: str, environment: str) -> DeploymentInfo:
        """Get deployment info for a specific environment."""
        vapi_state = self.load_deployment_state(squad_name)
        env_data = vapi_state.get('environments', {}).get(environment, {})
        return DeploymentInfo.from_dict(env_data)

    def is_deployed(self, squad_name: str, environment: str) -> bool:
        """Check if squad is deployed in the specified environment."""
        try:
            deployment_info = self.get_deployment_info(squad_name, environment)
            return deployment_info.is_deployed()
        except FileNotFoundError:
            return False

    def mark_deployed(
        self,
        squad_name: str,
        environment: str,
        vapi_id: str,
        deployed_by: Optional[str] = None
    ):
        """Mark a squad as deployed in the specified environment."""
        vapi_state = self.load_deployment_state(squad_name)

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
        self.save_deployment_state(squad_name, vapi_state)

    def mark_undeployed(self, squad_name: str, environment: str):
        """Mark a squad as not deployed (clear deployment info)."""
        vapi_state = self.load_deployment_state(squad_name)

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
            self.save_deployment_state(squad_name, vapi_state)

    def mark_updated(
        self,
        squad_name: str,
        environment: str,
        deployed_by: Optional[str] = None
    ):
        """Mark a squad as updated in the specified environment (increment version)."""
        vapi_state = self.load_deployment_state(squad_name)

        # Ensure environment exists
        if 'environments' not in vapi_state or environment not in vapi_state['environments']:
            raise ValueError(f"Squad {squad_name} not deployed to {environment}")

        env_data = vapi_state['environments'][environment]
        if not env_data.get('id'):
            raise ValueError(f"Squad {squad_name} not deployed to {environment}")

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
        self.save_deployment_state(squad_name, vapi_state)

    def get_all_deployments(self, squad_name: str) -> Dict[str, DeploymentInfo]:
        """Get deployment info for all environments."""
        vapi_state = self.load_deployment_state(squad_name)
        environments = vapi_state.get('environments', {})

        result = {}
        for env, data in environments.items():
            result[env] = DeploymentInfo.from_dict(data)

        return result

    def list_deployed_squads(self, environment: str) -> List[str]:
        """List all squads deployed to a specific environment."""
        deployed_squads = []

        if not self.base_dir.exists():
            return deployed_squads

        for squad_dir in self.base_dir.iterdir():
            if squad_dir.is_dir():
                try:
                    if self.is_deployed(squad_dir.name, environment):
                        deployed_squads.append(squad_dir.name)
                except FileNotFoundError:
                    continue

        return deployed_squads

    def get_deployed_environments(self, squad_name: str) -> List[str]:
        """Get list of environments where the squad is deployed."""
        try:
            deployments = self.get_all_deployments(squad_name)
            return [env for env, info in deployments.items() if info.is_deployed()]
        except FileNotFoundError:
            return []

    def get_deployment_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get a summary of all squad deployments."""
        summary = {}

        if not self.base_dir.exists():
            return summary

        for squad_dir in self.base_dir.iterdir():
            if squad_dir.is_dir():
                squad_name = squad_dir.name
                try:
                    deployments = self.get_all_deployments(squad_name)
                    summary[squad_name] = {
                        'deployments': deployments,
                        'total_deployed': sum(1 for d in deployments.values() if d.is_deployed())
                    }
                except FileNotFoundError:
                    summary[squad_name] = {
                        'deployments': {},
                        'total_deployed': 0
                    }

        return summary

    def _get_current_user(self) -> str:
        """Get the current user for deployment tracking."""
        return os.environ.get('USER') or os.environ.get('USERNAME') or 'unknown'