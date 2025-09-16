"""
Assistant Update Strategy Implementation

This module provides functionality to update VAPI assistants following
the architectural recommendations for safe, state-aware updates.
"""

import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from enum import Enum

from .assistant_config import AssistantConfigLoader, AssistantBuilder, AssistantConfig
from .deployment_state import DeploymentStateManager
from ..services.assistant_service import AssistantService
from ..core.models import AssistantUpdateRequest, Assistant
from ..core.exceptions.vapi_exceptions import VAPIException


class UpdateScope(str, Enum):
    """Different scopes for assistant updates."""
    CONFIGURATION = "configuration"  # Model, voice, transcriber settings
    PROMPTS = "prompts"              # System prompt, first message
    TOOLS = "tools"                  # Functions, transfers
    ANALYSIS = "analysis"            # Analytics, structured data extraction
    FULL = "full"                    # Everything (default)


@dataclass
class Change:
    """Represents a single configuration change."""
    field: str
    old_value: Any
    new_value: Any
    change_type: str = "modified"  # modified, added, removed


@dataclass
class ChangeSet:
    """Collection of changes detected in configuration."""
    changes: List[Change] = field(default_factory=list)

    def add(self, field: str, new_value: Any, old_value: Any = None, change_type: str = "modified"):
        """Add a change to the changeset."""
        self.changes.append(Change(field, old_value, new_value, change_type))

    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return len(self.changes) > 0

    def get_changes_for_scope(self, scope: UpdateScope) -> List[Change]:
        """Get changes relevant to a specific update scope."""
        if scope == UpdateScope.FULL:
            return self.changes

        scope_fields = {
            UpdateScope.CONFIGURATION: {'model', 'voice', 'transcriber', 'server', 'firstMessageMode'},
            UpdateScope.PROMPTS: {'system_prompt', 'first_message'},
            UpdateScope.TOOLS: {'tools', 'functions', 'transfers'},
            UpdateScope.ANALYSIS: {'analysisPlan', 'structuredDataPlan', 'summaryPlan'}
        }

        relevant_fields = scope_fields.get(scope, set())
        return [change for change in self.changes if any(field in change.field for field in relevant_fields)]


@dataclass
class UpdateOptions:
    """Options for assistant update operation."""
    force: bool = False
    backup: bool = True
    dry_run: bool = False
    scope: UpdateScope = UpdateScope.FULL
    environment: str = "development"


class ConfigDiffer:
    """Detects changes between local and remote assistant configurations."""

    def analyze_changes(self, local_config: AssistantConfig, remote_assistant: Assistant) -> ChangeSet:
        """
        Analyze changes between local configuration and remote assistant.

        Args:
            local_config: Local assistant configuration
            remote_assistant: Current remote assistant state

        Returns:
            ChangeSet with detected changes
        """
        changes = ChangeSet()
        local = local_config.config

        # Convert remote assistant back to config format for comparison
        remote = self._assistant_to_config_dict(remote_assistant)

        # Check model changes
        if local.get('model') != remote.get('model'):
            changes.add('model', local.get('model'), remote.get('model'))

        # Check voice changes
        if local.get('voice') != remote.get('voice'):
            changes.add('voice', local.get('voice'), remote.get('voice'))

        # Check transcriber changes
        if local.get('transcriber') != remote.get('transcriber'):
            changes.add('transcriber', local.get('transcriber'), remote.get('transcriber'))

        # Check prompt changes (hash-based detection for large content)
        if local_config.system_prompt:
            local_prompt_hash = hashlib.md5(local_config.system_prompt.encode()).hexdigest()
            remote_prompt = self._extract_system_prompt(remote_assistant)
            remote_prompt_hash = hashlib.md5((remote_prompt or "").encode()).hexdigest()

            if local_prompt_hash != remote_prompt_hash:
                changes.add('system_prompt', local_config.system_prompt, remote_prompt)

        # Check first message changes
        if local_config.first_message != remote_assistant.first_message:
            changes.add('first_message', local_config.first_message, remote_assistant.first_message)

        # Check firstMessageMode changes
        local_first_mode = local.get('firstMessageMode')
        remote_first_mode = remote_assistant.first_message_mode
        if local_first_mode != remote_first_mode:
            changes.add('firstMessageMode', local_first_mode, remote_first_mode)

        # Check tools changes (semantic comparison)
        if self._tools_changed(local_config.tools, remote_assistant.model.tools):
            changes.add('tools', local_config.tools, remote_assistant.model.tools)

        # Check server configuration
        local_server = local.get('server')
        remote_server = self._server_to_dict(remote_assistant.server)
        if local_server != remote_server:
            changes.add('server', local_server, remote_server)

        return changes

    def _assistant_to_config_dict(self, assistant: Assistant) -> Dict[str, Any]:
        """Convert Assistant object back to config dictionary format."""
        config = {}

        if assistant.model:
            config['model'] = {
                'provider': assistant.model.provider,
                'model': assistant.model.model,
                'temperature': assistant.model.temperature
            }

        if assistant.voice:
            config['voice'] = {
                'provider': assistant.voice.provider,
                'voiceId': assistant.voice.voice_id
            }

        if assistant.transcriber:
            config['transcriber'] = {
                'provider': assistant.transcriber.provider,
                'model': assistant.transcriber.model,
                'language': assistant.transcriber.language
            }

        if assistant.server:
            config['server'] = {
                'url': assistant.server.url,
                'timeoutSeconds': assistant.server.timeout_seconds
            }

        config['firstMessageMode'] = assistant.first_message_mode

        return config

    def _extract_system_prompt(self, assistant: Assistant) -> Optional[str]:
        """Extract system prompt from assistant model messages."""
        if not assistant.model or not assistant.model.messages:
            return None

        for message in assistant.model.messages:
            if message.get('role') == 'system':
                return message.get('content')

        return None

    def _tools_changed(self, local_tools: Dict[str, Any], remote_tools: Optional[List]) -> bool:
        """Check if tools configuration has changed."""
        # This is a simplified comparison - in production you might want more sophisticated comparison
        if not local_tools and not remote_tools:
            return False

        if not local_tools or not remote_tools:
            return True

        # Convert to JSON strings for comparison (normalized)
        try:
            local_json = json.dumps(local_tools, sort_keys=True)
            remote_json = json.dumps([tool.model_dump() if hasattr(tool, 'model_dump') else tool for tool in remote_tools], sort_keys=True)
            return local_json != remote_json
        except Exception:
            # If comparison fails, assume they're different
            return True

    def _server_to_dict(self, server) -> Optional[Dict[str, Any]]:
        """Convert server object to dictionary."""
        if not server:
            return None

        return {
            'url': server.url,
            'timeoutSeconds': server.timeout_seconds
        }


class UpdateStrategy:
    """Main class for handling assistant updates with safety measures."""

    def __init__(self, base_dir: str = "assistants"):
        self.config_loader = AssistantConfigLoader(base_dir)
        self.state_manager = DeploymentStateManager()
        self.assistant_service = AssistantService()
        self.differ = ConfigDiffer()
        self.base_dir = Path(base_dir)

    async def update_assistant(self, assistant_name: str, options: UpdateOptions) -> Dict[str, Any]:
        """
        Update an assistant with safety measures and change detection.

        Args:
            assistant_name: Name of the assistant to update
            options: Update options including environment, scope, etc.

        Returns:
            Dictionary with update results and metadata
        """
        # 1. Pre-update validation
        self._validate_deployment_exists(assistant_name, options.environment)

        # Load current configuration
        current_config = self.config_loader.load_assistant(assistant_name, options.environment)

        # Get remote state
        deployment_info = self.state_manager.get_deployment_info(assistant_name, options.environment)
        if not deployment_info or not deployment_info.id:
            raise VAPIException(f"Assistant {assistant_name} not deployed to {options.environment}")

        remote_assistant = await self.assistant_service.get_assistant(deployment_info.id)

        # 2. Diff analysis
        changes = self.differ.analyze_changes(current_config, remote_assistant)

        # Filter changes by scope
        relevant_changes = changes.get_changes_for_scope(options.scope)

        if not relevant_changes and not options.force:
            return {
                'status': 'no_changes',
                'message': f"No changes detected for scope '{options.scope}'",
                'changes': []
            }

        # 3. Safety measures
        backup_path = None
        if options.backup:
            backup_path = self._create_backup(assistant_name, options.environment)

        if options.dry_run:
            return self._preview_changes(relevant_changes, options)

        # 4. Apply updates
        try:
            updated_assistant = await self._apply_updates(
                current_config,
                deployment_info.id,
                options
            )

            # Increment version and update state
            self.state_manager.mark_updated(assistant_name, options.environment)

            if backup_path:
                # Clean up successful backup
                self._cleanup_backup(backup_path)

            return {
                'status': 'success',
                'message': f"Assistant {assistant_name} updated successfully",
                'changes': [self._change_to_dict(change) for change in relevant_changes],
                'assistant_id': updated_assistant.id,
                'version': self.state_manager.get_deployment_info(assistant_name, options.environment).version
            }

        except Exception as e:
            if backup_path:
                self._restore_from_backup(backup_path, assistant_name, options.environment)
            raise VAPIException(f"Update failed: {e}") from e

    def _validate_deployment_exists(self, assistant_name: str, environment: str):
        """Validate that assistant is deployed to the specified environment."""
        if not self.state_manager.is_deployed(assistant_name, environment):
            raise VAPIException(f"Assistant {assistant_name} is not deployed to {environment}")

    async def _apply_updates(self, config: AssistantConfig, assistant_id: str, options: UpdateOptions) -> Assistant:
        """Apply the configuration updates to the remote assistant."""
        # Build the update request from current configuration
        assistant_request = AssistantBuilder.build_from_config(config)

        # Convert to update request (excluding fields that shouldn't be updated)
        update_data = assistant_request.model_dump(by_alias=True, exclude_none=True)

        # Remove name from updates as it's typically immutable
        update_data.pop('name', None)

        # Create update request
        update_request = AssistantUpdateRequest(**update_data)

        # Apply the update
        return await self.assistant_service.update_assistant(assistant_id, update_request)

    def _create_backup(self, assistant_name: str, environment: str) -> Path:
        """Create a backup of the current assistant state."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.base_dir / assistant_name / ".backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        backup_path = backup_dir / f"backup_{environment}_{timestamp}.yaml"

        # Copy current assistant.yaml
        assistant_file = self.base_dir / assistant_name / "assistant.yaml"
        if assistant_file.exists():
            shutil.copy2(assistant_file, backup_path)

        return backup_path

    def _cleanup_backup(self, backup_path: Path):
        """Clean up successful backup file."""
        if backup_path.exists():
            backup_path.unlink()

    def _restore_from_backup(self, backup_path: Path, assistant_name: str, environment: str):
        """Restore assistant configuration from backup."""
        if backup_path.exists():
            assistant_file = self.base_dir / assistant_name / "assistant.yaml"
            shutil.copy2(backup_path, assistant_file)
            # Keep backup for reference

    def _preview_changes(self, changes: List[Change], options: UpdateOptions) -> Dict[str, Any]:
        """Generate a preview of changes without applying them."""
        return {
            'status': 'preview',
            'message': f"Preview of changes for scope '{options.scope}'",
            'changes': [self._change_to_dict(change) for change in changes],
            'total_changes': len(changes)
        }

    def _change_to_dict(self, change: Change) -> Dict[str, Any]:
        """Convert Change object to dictionary for serialization."""
        return {
            'field': change.field,
            'change_type': change.change_type,
            'old_value': change.old_value,
            'new_value': change.new_value
        }