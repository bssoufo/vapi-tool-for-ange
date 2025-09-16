"""
Squad Backup and Restore Manager

This module provides comprehensive backup and restore functionality for complete squads
including all related assistants, configurations, and deployment dependencies.
"""

import os
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

from ..services import SquadService, AssistantService
from ..core.squad_config import SquadConfigLoader, SquadBuilder
from ..core.squad_deployment_state import SquadDeploymentStateManager
from ..core.backup_manager import BackupManager
from ..core.squad_backup_models import (
    SquadBackupData, SquadBackupMetadata, SquadBackupManifest,
    SquadBackupType, SquadRestoreOptions, SquadRestoreResult
)
from ..core.backup_models import BackupType, BackupScope, BackupStatus, AssistantBackupData
from ..core.exceptions.vapi_exceptions import VAPIException


class SquadBackupManager:
    """Manages backup and restore operations for complete squads with all dependencies."""

    def __init__(
        self,
        squads_dir: str = "squads",
        assistants_dir: str = "assistants",
        backups_dir: str = "backups"
    ):
        self.squads_dir = Path(squads_dir)
        self.assistants_dir = Path(assistants_dir)
        self.backups_dir = Path(backups_dir)

        # Initialize services
        self.squad_service = SquadService()
        self.assistant_service = AssistantService()

        # Initialize managers
        self.squad_config_loader = SquadConfigLoader(squads_dir)
        self.squad_deployment_manager = SquadDeploymentStateManager(squads_dir)
        self.assistant_backup_manager = BackupManager(assistants_dir, backups_dir)

        # Ensure backups directory exists
        self.backups_dir.mkdir(exist_ok=True)

    async def create_squad_backup(
        self,
        squad_name: str,
        environment: str = "development",
        backup_type: SquadBackupType = SquadBackupType.COMPLETE,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> SquadBackupManifest:
        """
        Create a comprehensive backup of a squad with all related components.

        Args:
            squad_name: Name of the squad to backup
            environment: Environment to backup from
            backup_type: Type of squad backup to create
            description: Optional description for the backup
            tags: Optional tags for organizing backups

        Returns:
            SquadBackupManifest with complete backup data
        """
        # Generate unique backup ID
        backup_id = f"squad_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Validate squad exists
        if not self.squad_deployment_manager.validate_squad_exists(squad_name):
            raise ValueError(f"Squad '{squad_name}' not found locally")

        # Check if squad is deployed
        if not self.squad_deployment_manager.is_deployed(squad_name, environment):
            raise ValueError(f"Squad '{squad_name}' is not deployed to {environment}")

        try:
            # Create squad backup data
            squad_backup = await self._backup_complete_squad(squad_name, environment, backup_type)

            # Calculate total size
            total_size = self._estimate_squad_backup_size(squad_backup)

            # Create metadata
            metadata = SquadBackupMetadata(
                backup_id=backup_id,
                created_at=datetime.now(timezone.utc),
                created_by=self._get_current_user(),
                backup_type=BackupType.FULL,  # Squad backups are always considered "full"
                backup_scope=BackupScope.SINGLE,
                environment=environment,
                assistant_count=len(squad_backup.assistant_backups),
                total_size_bytes=total_size,
                description=description,
                tags=tags or [],
                status=BackupStatus.CREATED,
                squad_backup_type=backup_type,
                squad_member_count=len(squad_backup.assistant_dependencies)
            )

            # Create manifest
            manifest = SquadBackupManifest(
                metadata=metadata,
                squad_backup=squad_backup
            )

            # Calculate and set checksum
            manifest.checksum = manifest.calculate_checksum()

            # Save backup to file
            backup_file = self.backups_dir / f"{backup_id}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(manifest.to_dict(), f, indent=2, default=self._json_serializer)

            metadata.status = BackupStatus.VALIDATED
            return manifest

        except Exception as e:
            raise VAPIException(f"Failed to create squad backup: {str(e)}")

    async def _backup_complete_squad(
        self,
        squad_name: str,
        environment: str,
        backup_type: SquadBackupType
    ) -> SquadBackupData:
        """Create complete backup data for a squad and all related assistants."""
        squad_backup = SquadBackupData(squad_name=squad_name)

        # 1. Backup squad VAPI data
        if backup_type in [SquadBackupType.COMPLETE, SquadBackupType.SQUAD_ONLY, SquadBackupType.WITH_ASSISTANTS]:
            squad_backup.squad_vapi_data = await self._backup_squad_vapi_data(squad_name, environment)

        # 2. Backup squad local configuration
        if backup_type in [SquadBackupType.COMPLETE]:
            squad_backup.squad_local_config = self._backup_squad_local_config(squad_name, environment)
            squad_backup.squad_file_contents = self._backup_squad_files(squad_name)
            squad_backup.squad_deployment_state = self._backup_squad_deployment_state(squad_name)

        # 3. Get squad member assistants
        assistant_names = await self._get_squad_assistant_names(squad_name, environment)

        # 4. Backup all related assistants
        if backup_type in [SquadBackupType.COMPLETE, SquadBackupType.WITH_ASSISTANTS]:
            for assistant_name in assistant_names:
                try:
                    # Determine assistant backup type based on squad backup type
                    if backup_type == SquadBackupType.COMPLETE:
                        assistant_backup_type = BackupType.FULL
                    else:  # WITH_ASSISTANTS
                        assistant_backup_type = BackupType.VAPI_ONLY

                    # Create assistant backup
                    assistant_backup = await self.assistant_backup_manager._backup_single_assistant(
                        assistant_name, environment, assistant_backup_type
                    )
                    squad_backup.assistant_backups.append(assistant_backup)

                    # Track assistant ID mapping
                    if assistant_backup.vapi_data and assistant_backup.vapi_data.get('id'):
                        squad_backup.assistant_dependencies[assistant_name] = assistant_backup.vapi_data['id']

                except Exception as e:
                    # Continue with other assistants if one fails
                    print(f"Warning: Failed to backup assistant '{assistant_name}': {e}")

        return squad_backup

    async def _backup_squad_vapi_data(self, squad_name: str, environment: str) -> Optional[Dict[str, Any]]:
        """Backup squad data from VAPI."""
        try:
            deployment_info = self.squad_deployment_manager.get_deployment_info(squad_name, environment)
            squad = await self.squad_service.get_squad(deployment_info.id)
            return json.loads(json.dumps(squad.model_dump(by_alias=True), default=self._json_serializer))
        except Exception:
            return None

    def _backup_squad_local_config(self, squad_name: str, environment: str) -> Optional[Dict[str, Any]]:
        """Backup local squad configuration."""
        try:
            config = self.squad_config_loader.load_squad(squad_name, environment)
            return {
                'config': config.config,
                'members': config.members,
                'overrides': config.overrides,
                'routing': config.routing
            }
        except Exception:
            return None

    def _backup_squad_files(self, squad_name: str) -> Dict[str, str]:
        """Backup all files for a squad."""
        squad_path = self.squads_dir / squad_name
        file_contents = {}

        if not squad_path.exists():
            return file_contents

        # Recursively backup all files
        for file_path in squad_path.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(squad_path)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_contents[str(relative_path)] = f.read()
                except (UnicodeDecodeError, OSError):
                    # Skip binary files or files that can't be read
                    continue

        return file_contents

    def _backup_squad_deployment_state(self, squad_name: str) -> Dict[str, Any]:
        """Backup squad deployment state."""
        try:
            all_deployments = self.squad_deployment_manager.get_all_deployments(squad_name)
            return {
                env: deployment.to_dict() for env, deployment in all_deployments.items()
            }
        except Exception:
            return {}

    async def _get_squad_assistant_names(self, squad_name: str, environment: str) -> List[str]:
        """Get list of assistant names from squad members."""
        try:
            # Get from VAPI data if possible
            deployment_info = self.squad_deployment_manager.get_deployment_info(squad_name, environment)
            squad = await self.squad_service.get_squad(deployment_info.id)

            # Extract assistant names from squad members
            assistant_names = []
            if squad.members:
                # We need to map assistant IDs back to names
                # This requires checking deployment states
                from ..core.deployment_state import DeploymentStateManager
                assistant_manager = DeploymentStateManager(self.assistants_dir)

                for member in squad.members:
                    assistant_id = member.assistant_id
                    # Find assistant name by ID
                    assistant_name = self._find_assistant_name_by_id(assistant_id, environment, assistant_manager)
                    if assistant_name:
                        assistant_names.append(assistant_name)

            return assistant_names

        except Exception:
            # Fallback to local config
            try:
                config = self.squad_config_loader.load_squad(squad_name, environment)
                return [member.get('assistant_name') for member in config.members if member.get('assistant_name')]
            except Exception:
                return []

    def _find_assistant_name_by_id(self, assistant_id: str, environment: str, assistant_manager) -> Optional[str]:
        """Find assistant name by VAPI ID."""
        # Get all assistant directories
        if not self.assistants_dir.exists():
            return None

        for assistant_dir in self.assistants_dir.iterdir():
            if assistant_dir.is_dir():
                try:
                    deployment_info = assistant_manager.get_deployment_info(assistant_dir.name, environment)
                    if deployment_info.id == assistant_id:
                        return assistant_dir.name
                except Exception:
                    continue

        return None

    async def restore_squad_backup(
        self,
        backup_path: str,
        options: SquadRestoreOptions
    ) -> SquadRestoreResult:
        """
        Restore a complete squad from backup with all related components.

        Args:
            backup_path: Path to squad backup file
            options: Restore options and configuration

        Returns:
            SquadRestoreResult with operation details
        """
        result = SquadRestoreResult(success=False)

        # Validate restore options
        option_errors = options.validate()
        if option_errors:
            for error in option_errors:
                result.add_error(error)
            return result

        try:
            # Load backup manifest
            manifest = self._load_squad_backup_manifest(backup_path)

            # Validate backup integrity
            if not manifest.validate_integrity():
                result.add_error("Squad backup integrity check failed - corrupted backup file")
                return result

            # Create safety backup if requested
            if options.backup_before_restore:
                try:
                    safety_backup = await self.create_squad_backup(
                        manifest.squad_backup.squad_name,
                        environment=options.target_environment,
                        backup_type=SquadBackupType.COMPLETE,
                        description=f"Safety backup before restore from {Path(backup_path).name}",
                        tags=["safety", "auto-generated"]
                    )
                    result.backup_created = safety_backup.metadata.backup_id
                except Exception as e:
                    result.add_warning(f"Failed to create safety backup: {str(e)}")

            # Restore squad and assistants
            if options.dry_run:
                result = self._simulate_squad_restore(manifest, options, result)
            else:
                result = await self._perform_squad_restore(manifest, options, result)

            # Determine overall success
            result.success = not result.failed_squad and len(result.failed_assistants) == 0

            return result

        except Exception as e:
            result.add_error(f"Squad restore operation failed: {str(e)}")
            return result

    def _simulate_squad_restore(
        self,
        manifest: SquadBackupManifest,
        options: SquadRestoreOptions,
        result: SquadRestoreResult
    ) -> SquadRestoreResult:
        """Simulate squad restore for dry-run mode."""
        squad_backup = manifest.squad_backup

        # Simulate squad restore
        squad_name = options.squad_name_override or squad_backup.squad_name
        result.mark_squad_restored(squad_name)

        # Simulate assistant restores
        for assistant_backup in squad_backup.assistant_backups:
            assistant_name = options.assistant_name_prefix + assistant_backup.assistant_name
            result.mark_restored(assistant_name)
            result.add_assistant_detail(assistant_name, {
                'has_vapi_data': bool(assistant_backup.vapi_data),
                'has_local_config': bool(assistant_backup.local_config),
                'file_count': len(assistant_backup.file_contents) if assistant_backup.file_contents else 0
            })

        return result

    async def _perform_squad_restore(
        self,
        manifest: SquadBackupManifest,
        options: SquadRestoreOptions,
        result: SquadRestoreResult
    ) -> SquadRestoreResult:
        """Perform actual squad restore."""
        squad_backup = manifest.squad_backup

        try:
            # 1. Restore assistants first (dependencies)
            if options.restore_assistants:
                await self._restore_squad_assistants(squad_backup, options, result)

            # 2. Restore squad configuration and data
            await self._restore_squad_data(squad_backup, options, result)

            return result

        except Exception as e:
            result.mark_squad_failed()
            result.add_error(f"Squad restore failed: {str(e)}")
            return result

    async def _restore_squad_assistants(
        self,
        squad_backup: SquadBackupData,
        options: SquadRestoreOptions,
        result: SquadRestoreResult
    ):
        """Restore all assistants related to the squad."""
        for assistant_backup in squad_backup.assistant_backups:
            try:
                assistant_name = options.assistant_name_prefix + assistant_backup.assistant_name

                # Check if assistant already exists
                assistant_path = self.assistants_dir / assistant_name
                assistant_exists = assistant_path.exists()

                from ..core.deployment_state import DeploymentStateManager
                assistant_manager = DeploymentStateManager(self.assistants_dir)
                vapi_deployed = assistant_manager.is_deployed(assistant_name, options.target_environment)

                if (assistant_exists or vapi_deployed) and not options.overwrite_existing:
                    result.mark_skipped(assistant_name)
                    result.add_warning(f"Assistant '{assistant_name}' already exists (use --overwrite to replace)")
                    continue

                # Restore assistant local configuration
                if options.restore_local_config and assistant_backup.local_config:
                    await self._restore_assistant_local_config(assistant_name, assistant_backup, options)

                # Restore assistant to VAPI
                if options.restore_vapi_data and assistant_backup.vapi_data and not options.skip_assistant_deployment:
                    await self._restore_assistant_vapi_data(assistant_name, assistant_backup, options)

                # Restore deployment state
                if options.restore_deployment_state and assistant_backup.deployment_state:
                    self._restore_assistant_deployment_state(assistant_name, assistant_backup, options)

                result.mark_restored(assistant_name)
                result.add_assistant_detail(assistant_name, {
                    'restored_config': bool(assistant_backup.local_config),
                    'restored_vapi': bool(assistant_backup.vapi_data),
                    'file_count': len(assistant_backup.file_contents) if assistant_backup.file_contents else 0
                })

            except Exception as e:
                result.mark_failed(assistant_backup.assistant_name)
                result.add_error(f"Failed to restore assistant {assistant_backup.assistant_name}: {str(e)}")

    async def _restore_squad_data(
        self,
        squad_backup: SquadBackupData,
        options: SquadRestoreOptions,
        result: SquadRestoreResult
    ):
        """Restore squad data and configuration."""
        squad_name = options.squad_name_override or squad_backup.squad_name

        try:
            # Restore local squad configuration
            if options.restore_local_config and squad_backup.squad_local_config:
                await self._restore_squad_local_config(squad_name, squad_backup, options)

            # Restore squad to VAPI
            if options.restore_vapi_data and squad_backup.squad_vapi_data:
                await self._restore_squad_vapi_data(squad_name, squad_backup, options)

            # Restore squad deployment state
            if options.restore_deployment_state and squad_backup.squad_deployment_state:
                self._restore_squad_deployment_state(squad_name, squad_backup, options)

            result.mark_squad_restored(squad_name)

        except Exception as e:
            result.mark_squad_failed()
            result.add_error(f"Failed to restore squad '{squad_name}': {str(e)}")

    async def _restore_assistant_local_config(
        self,
        assistant_name: str,
        assistant_backup: AssistantBackupData,
        options: SquadRestoreOptions
    ):
        """Restore assistant local configuration files."""
        assistant_path = self.assistants_dir / assistant_name

        # Create directory if needed
        if options.create_missing_directories:
            assistant_path.mkdir(parents=True, exist_ok=True)

        # Restore file contents
        if assistant_backup.file_contents:
            for relative_path, content in assistant_backup.file_contents.items():
                file_path = assistant_path / relative_path
                file_path.parent.mkdir(parents=True, exist_ok=True)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

    async def _restore_assistant_vapi_data(
        self,
        assistant_name: str,
        assistant_backup: AssistantBackupData,
        options: SquadRestoreOptions
    ):
        """Restore assistant to VAPI."""
        from ..core.models.assistant import AssistantCreateRequest

        vapi_data = assistant_backup.vapi_data.copy()

        # Remove fields that shouldn't be in create request
        vapi_data.pop('id', None)
        vapi_data.pop('orgId', None)
        vapi_data.pop('createdAt', None)
        vapi_data.pop('updatedAt', None)

        # Create assistant in VAPI
        create_request = AssistantCreateRequest.model_validate(vapi_data)
        assistant = await self.assistant_service.create_assistant(create_request)

        # Track deployment
        from ..core.deployment_state import DeploymentStateManager
        assistant_manager = DeploymentStateManager(self.assistants_dir)
        assistant_manager.mark_deployed(assistant_name, options.target_environment, assistant.id)

    def _restore_assistant_deployment_state(
        self,
        assistant_name: str,
        assistant_backup: AssistantBackupData,
        options: SquadRestoreOptions
    ):
        """Restore assistant deployment state information."""
        # This is mainly for reference as IDs will be different
        pass

    async def _restore_squad_local_config(
        self,
        squad_name: str,
        squad_backup: SquadBackupData,
        options: SquadRestoreOptions
    ):
        """Restore squad local configuration files."""
        squad_path = self.squads_dir / squad_name

        # Create directory if needed
        if options.create_missing_directories:
            squad_path.mkdir(parents=True, exist_ok=True)

        # Restore file contents
        if squad_backup.squad_file_contents:
            for relative_path, content in squad_backup.squad_file_contents.items():
                file_path = squad_path / relative_path
                file_path.parent.mkdir(parents=True, exist_ok=True)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

    async def _restore_squad_vapi_data(
        self,
        squad_name: str,
        squad_backup: SquadBackupData,
        options: SquadRestoreOptions
    ):
        """Restore squad to VAPI with updated assistant IDs."""
        from ..core.models.squad import SquadCreateRequest, SquadMember

        vapi_data = squad_backup.squad_vapi_data.copy()

        # Remove fields that shouldn't be in create request
        vapi_data.pop('id', None)
        vapi_data.pop('orgId', None)
        vapi_data.pop('createdAt', None)
        vapi_data.pop('updatedAt', None)

        # Update member assistant IDs with newly restored assistants
        if 'members' in vapi_data:
            updated_members = []
            from ..core.deployment_state import DeploymentStateManager
            assistant_manager = DeploymentStateManager(self.assistants_dir)

            for member_data in vapi_data['members']:
                # Find the assistant name and get its new ID
                old_assistant_id = member_data.get('assistantId')
                assistant_name = None

                # Find assistant name from backup data
                for assistant_backup in squad_backup.assistant_backups:
                    if assistant_backup.vapi_data and assistant_backup.vapi_data.get('id') == old_assistant_id:
                        assistant_name = options.assistant_name_prefix + assistant_backup.assistant_name
                        break

                if assistant_name:
                    try:
                        deployment_info = assistant_manager.get_deployment_info(assistant_name, options.target_environment)
                        if deployment_info.is_deployed():
                            member_data['assistantId'] = deployment_info.id
                            updated_members.append(SquadMember.model_validate(member_data))
                    except Exception:
                        # Skip member if assistant not found
                        continue

            vapi_data['members'] = updated_members

        # Create squad in VAPI
        create_request = SquadCreateRequest.model_validate(vapi_data)
        squad = await self.squad_service.create_squad(create_request)

        # Track deployment
        self.squad_deployment_manager.mark_deployed(squad_name, options.target_environment, squad.id)

    def _restore_squad_deployment_state(
        self,
        squad_name: str,
        squad_backup: SquadBackupData,
        options: SquadRestoreOptions
    ):
        """Restore squad deployment state information."""
        # This is mainly for reference as IDs will be different
        pass

    def list_squad_backups(self) -> List[SquadBackupMetadata]:
        """List all available squad backups."""
        backups = []

        for backup_file in self.backups_dir.glob("squad_backup_*.json"):
            try:
                manifest = self._load_squad_backup_manifest(str(backup_file))
                backups.append(manifest.metadata)
            except Exception:
                # Skip corrupted backup files
                continue

        # Sort by creation date (newest first)
        return sorted(backups, key=lambda b: b.created_at, reverse=True)

    def get_squad_backup_details(self, backup_id: str) -> Optional[SquadBackupManifest]:
        """Get detailed information about a specific squad backup."""
        backup_file = self.backups_dir / f"{backup_id}.json"
        if not backup_file.exists():
            return None

        return self._load_squad_backup_manifest(str(backup_file))

    def delete_squad_backup(self, backup_id: str) -> bool:
        """Delete a squad backup file."""
        backup_file = self.backups_dir / f"{backup_id}.json"
        if backup_file.exists():
            backup_file.unlink()
            return True
        return False

    def _load_squad_backup_manifest(self, backup_path: str) -> SquadBackupManifest:
        """Load squad backup manifest from file."""
        with open(backup_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return SquadBackupManifest.from_dict(data)

    def _estimate_squad_backup_size(self, squad_backup: SquadBackupData) -> int:
        """Estimate squad backup size in bytes."""
        import sys

        size = 0

        # Squad data
        if squad_backup.squad_vapi_data:
            size += sys.getsizeof(json.dumps(squad_backup.squad_vapi_data))
        if squad_backup.squad_local_config:
            size += sys.getsizeof(json.dumps(squad_backup.squad_local_config))
        if squad_backup.squad_file_contents:
            size += sum(len(content.encode('utf-8')) for content in squad_backup.squad_file_contents.values())

        # Assistant data
        for assistant_backup in squad_backup.assistant_backups:
            if assistant_backup.vapi_data:
                size += sys.getsizeof(json.dumps(assistant_backup.vapi_data))
            if assistant_backup.local_config:
                size += sys.getsizeof(json.dumps(assistant_backup.local_config))
            if assistant_backup.file_contents:
                size += sum(len(content.encode('utf-8')) for content in assistant_backup.file_contents.values())

        return size

    def _get_current_user(self) -> str:
        """Get current user for backup tracking."""
        return os.environ.get('USER') or os.environ.get('USERNAME') or 'unknown'

    def _json_serializer(self, obj):
        """JSON serializer for datetime and other objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")