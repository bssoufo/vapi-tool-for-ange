"""
Assistant Backup and Restore Manager

This module provides comprehensive backup and restore functionality for VAPI assistants,
including local configurations, deployed VAPI data, and deployment state management.
"""

import os
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from ..services import AssistantService
from ..core.assistant_config import AssistantConfigLoader
from ..core.deployment_state import DeploymentStateManager
from ..core.backup_models import (
    BackupMetadata, AssistantBackupData, BackupManifest, RestoreOptions, RestoreResult,
    BackupType, BackupScope, BackupStatus
)
from ..core.exceptions.vapi_exceptions import VAPIException


class BackupManager:
    """Manages backup and restore operations for assistants."""

    def __init__(self, assistants_dir: str = "assistants", backups_dir: str = "backups"):
        self.assistants_dir = Path(assistants_dir)
        self.backups_dir = Path(backups_dir)
        self.assistant_service = AssistantService()
        self.config_loader = AssistantConfigLoader(assistants_dir)
        self.deployment_manager = DeploymentStateManager(assistants_dir)

        # Ensure backups directory exists
        self.backups_dir.mkdir(exist_ok=True)

    async def create_backup(
        self,
        assistant_names: Optional[List[str]] = None,
        environment: str = "development",
        backup_type: BackupType = BackupType.FULL,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> BackupManifest:
        """
        Create a comprehensive backup of assistants.

        Args:
            assistant_names: List of assistant names to backup (None = all)
            environment: Environment to backup from
            backup_type: Type of backup to create
            description: Optional description for the backup
            tags: Optional tags for organizing backups

        Returns:
            BackupManifest with complete backup data
        """
        # Generate unique backup ID
        backup_id = f"backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Determine assistants to backup
        if assistant_names is None:
            assistant_names = self._get_all_assistant_names()
            backup_scope = BackupScope.ALL
        elif len(assistant_names) == 1:
            backup_scope = BackupScope.SINGLE
        else:
            backup_scope = BackupScope.MULTIPLE

        # Validate assistant names
        missing_assistants = self._validate_assistant_names(assistant_names)
        if missing_assistants:
            raise ValueError(f"Assistants not found: {', '.join(missing_assistants)}")

        # Create backup data for each assistant
        backup_data = []
        total_size = 0

        for assistant_name in assistant_names:
            try:
                assistant_backup = await self._backup_single_assistant(
                    assistant_name, environment, backup_type
                )
                backup_data.append(assistant_backup)

                # Calculate size (rough estimate)
                size = self._estimate_backup_size(assistant_backup)
                total_size += size

            except Exception as e:
                raise VAPIException(f"Failed to backup assistant '{assistant_name}': {str(e)}")

        # Create metadata
        metadata = BackupMetadata(
            backup_id=backup_id,
            created_at=datetime.now(timezone.utc),
            created_by=self._get_current_user(),
            backup_type=backup_type,
            backup_scope=backup_scope,
            environment=environment,
            assistant_count=len(backup_data),
            total_size_bytes=total_size,
            description=description,
            tags=tags or [],
            status=BackupStatus.CREATED
        )

        # Create manifest
        manifest = BackupManifest(
            metadata=metadata,
            assistants=backup_data
        )

        # Calculate and set checksum
        manifest.checksum = manifest.calculate_checksum()

        # Save backup to file
        backup_file = self.backups_dir / f"{backup_id}.json"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(manifest.to_dict(), f, indent=2, default=self._json_serializer)

        metadata.status = BackupStatus.VALIDATED
        return manifest

    async def _backup_single_assistant(
        self,
        assistant_name: str,
        environment: str,
        backup_type: BackupType
    ) -> AssistantBackupData:
        """Create backup data for a single assistant."""
        backup_data = AssistantBackupData(assistant_name=assistant_name)

        # Backup VAPI data if requested
        if backup_type in [BackupType.FULL, BackupType.VAPI_ONLY]:
            try:
                if self.deployment_manager.is_deployed(assistant_name, environment):
                    deployment_info = self.deployment_manager.get_deployment_info(assistant_name, environment)
                    assistant = await self.assistant_service.get_assistant(deployment_info.id)
                    backup_data.vapi_data = json.loads(json.dumps(assistant.model_dump(by_alias=True), default=self._json_serializer))
            except Exception as e:
                # VAPI data not available, but continue with local backup
                backup_data.vapi_data = None

        # Backup local configuration if requested
        if backup_type in [BackupType.FULL, BackupType.CONFIG_ONLY]:
            try:
                # Load local configuration
                config = self.config_loader.load_assistant(assistant_name, environment)
                backup_data.local_config = {
                    'config': config.config,
                    'schemas': config.schemas,
                    'tools': config.tools
                }

                # Backup file contents
                backup_data.file_contents = self._backup_assistant_files(assistant_name)

                # Backup deployment state
                try:
                    all_deployments = self.deployment_manager.get_all_deployments(assistant_name)
                    backup_data.deployment_state = {
                        env: deployment.to_dict() for env, deployment in all_deployments.items()
                    }
                except:
                    backup_data.deployment_state = {}

            except Exception as e:
                # Local config not available
                backup_data.local_config = None
                backup_data.file_contents = None
                backup_data.deployment_state = None

        return backup_data

    def _backup_assistant_files(self, assistant_name: str) -> Dict[str, str]:
        """Backup all files for an assistant."""
        assistant_path = self.assistants_dir / assistant_name
        file_contents = {}

        if not assistant_path.exists():
            return file_contents

        # Recursively backup all files
        for file_path in assistant_path.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(assistant_path)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_contents[str(relative_path)] = f.read()
                except (UnicodeDecodeError, OSError):
                    # Skip binary files or files that can't be read
                    continue

        return file_contents

    async def restore_backup(
        self,
        backup_path: str,
        options: RestoreOptions
    ) -> RestoreResult:
        """
        Restore assistants from a backup.

        Args:
            backup_path: Path to backup file
            options: Restore options and configuration

        Returns:
            RestoreResult with operation details
        """
        result = RestoreResult(success=False)

        # Validate restore options
        option_errors = options.validate()
        if option_errors:
            for error in option_errors:
                result.add_error(error)
            return result

        try:
            # Load backup manifest
            manifest = self._load_backup_manifest(backup_path)

            # Validate backup integrity
            if not manifest.validate_integrity():
                result.add_error("Backup integrity check failed - corrupted backup file")
                return result

            # Create safety backup if requested
            if options.backup_before_restore:
                try:
                    safety_backup = await self.create_backup(
                        assistant_names=None,  # Backup all
                        environment=options.target_environment,
                        backup_type=BackupType.FULL,
                        description=f"Safety backup before restore from {Path(backup_path).name}",
                        tags=["safety", "auto-generated"]
                    )
                    result.backup_created = safety_backup.metadata.backup_id
                except Exception as e:
                    result.add_warning(f"Failed to create safety backup: {str(e)}")

            # Restore each assistant
            for assistant_backup in manifest.assistants:
                try:
                    if options.dry_run:
                        result.mark_restored(assistant_backup.assistant_name)
                        continue

                    await self._restore_single_assistant(assistant_backup, options, result)

                except Exception as e:
                    result.mark_failed(assistant_backup.assistant_name)
                    result.add_error(f"Failed to restore {assistant_backup.assistant_name}: {str(e)}")

            # Determine overall success
            result.success = len(result.failed_assistants) == 0

            return result

        except Exception as e:
            result.add_error(f"Restore operation failed: {str(e)}")
            return result

    async def _restore_single_assistant(
        self,
        backup_data: AssistantBackupData,
        options: RestoreOptions,
        result: RestoreResult
    ):
        """Restore a single assistant from backup data."""
        assistant_name = backup_data.assistant_name
        assistant_path = self.assistants_dir / assistant_name

        # Check if assistant exists
        assistant_exists = assistant_path.exists()
        vapi_deployed = self.deployment_manager.is_deployed(assistant_name, options.target_environment)

        if (assistant_exists or vapi_deployed) and not options.overwrite_existing:
            result.mark_skipped(assistant_name)
            result.add_warning(f"Assistant '{assistant_name}' already exists (use --overwrite to replace)")
            return

        # Restore local configuration
        if options.restore_local_config and backup_data.local_config:
            await self._restore_local_config(assistant_name, backup_data, options)

        # Restore VAPI data
        if options.restore_vapi_data and backup_data.vapi_data:
            await self._restore_vapi_data(assistant_name, backup_data, options)

        # Restore deployment state
        if options.restore_deployment_state and backup_data.deployment_state:
            self._restore_deployment_state(assistant_name, backup_data, options)

        result.mark_restored(assistant_name)

    async def _restore_local_config(
        self,
        assistant_name: str,
        backup_data: AssistantBackupData,
        options: RestoreOptions
    ):
        """Restore local configuration files."""
        assistant_path = self.assistants_dir / assistant_name

        # Create directory if needed
        if options.create_missing_directories:
            assistant_path.mkdir(parents=True, exist_ok=True)

        # Restore file contents
        if backup_data.file_contents:
            for relative_path, content in backup_data.file_contents.items():
                file_path = assistant_path / relative_path
                file_path.parent.mkdir(parents=True, exist_ok=True)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

    async def _restore_vapi_data(
        self,
        assistant_name: str,
        backup_data: AssistantBackupData,
        options: RestoreOptions
    ):
        """Restore assistant to VAPI."""
        from ..core.models.assistant import AssistantCreateRequest

        vapi_data = backup_data.vapi_data.copy()

        # Remove fields that shouldn't be in create request
        vapi_data.pop('id', None)
        vapi_data.pop('orgId', None)
        vapi_data.pop('createdAt', None)
        vapi_data.pop('updatedAt', None)

        # Create assistant in VAPI
        create_request = AssistantCreateRequest.model_validate(vapi_data)
        assistant = await self.assistant_service.create_assistant(create_request)

        # Track deployment
        self.deployment_manager.mark_deployed(
            assistant_name,
            options.target_environment,
            assistant.id
        )

    def _restore_deployment_state(
        self,
        assistant_name: str,
        backup_data: AssistantBackupData,
        options: RestoreOptions
    ):
        """Restore deployment state information."""
        if not backup_data.deployment_state:
            return

        # Only restore state for target environment
        env_state = backup_data.deployment_state.get(options.target_environment)
        if env_state and env_state.get('id'):
            # Note: We don't restore the exact deployment state as IDs will be different
            # This is mainly for reference
            pass

    def list_backups(self) -> List[BackupMetadata]:
        """List all available backups."""
        backups = []

        for backup_file in self.backups_dir.glob("*.json"):
            try:
                manifest = self._load_backup_manifest(str(backup_file))
                backups.append(manifest.metadata)
            except:
                # Skip corrupted backup files
                continue

        # Sort by creation date (newest first)
        return sorted(backups, key=lambda b: b.created_at, reverse=True)

    def get_backup_details(self, backup_id: str) -> Optional[BackupManifest]:
        """Get detailed information about a specific backup."""
        backup_file = self.backups_dir / f"{backup_id}.json"
        if not backup_file.exists():
            return None

        return self._load_backup_manifest(str(backup_file))

    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup file."""
        backup_file = self.backups_dir / f"{backup_id}.json"
        if backup_file.exists():
            backup_file.unlink()
            return True
        return False

    def _load_backup_manifest(self, backup_path: str) -> BackupManifest:
        """Load backup manifest from file."""
        with open(backup_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return BackupManifest.from_dict(data)

    def _get_all_assistant_names(self) -> List[str]:
        """Get list of all assistant names."""
        if not self.assistants_dir.exists():
            return []

        return [d.name for d in self.assistants_dir.iterdir()
                if d.is_dir() and not d.name.startswith('.')]

    def _validate_assistant_names(self, assistant_names: List[str]) -> List[str]:
        """Validate that assistant names exist locally."""
        all_assistants = set(self._get_all_assistant_names())
        return [name for name in assistant_names if name not in all_assistants]

    def _estimate_backup_size(self, backup_data: AssistantBackupData) -> int:
        """Estimate backup size in bytes."""
        import sys

        size = 0
        if backup_data.vapi_data:
            size += sys.getsizeof(json.dumps(backup_data.vapi_data))
        if backup_data.local_config:
            size += sys.getsizeof(json.dumps(backup_data.local_config))
        if backup_data.file_contents:
            size += sum(len(content.encode('utf-8')) for content in backup_data.file_contents.values())

        return size

    def _get_current_user(self) -> str:
        """Get current user for backup tracking."""
        return os.environ.get('USER') or os.environ.get('USERNAME') or 'unknown'

    def _json_serializer(self, obj):
        """JSON serializer for datetime and other objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")