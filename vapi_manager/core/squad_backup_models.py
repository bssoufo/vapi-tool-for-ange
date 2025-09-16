"""
Squad Backup and Restore Data Models

This module defines the data structures for backing up and restoring complete squads
including all related assistants, configurations, and deployment states.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from ..core.backup_models import (
    BackupType, BackupScope, BackupStatus, AssistantBackupData,
    BackupMetadata, RestoreOptions, RestoreResult
)


class SquadBackupType(str, Enum):
    """Type of squad backup."""
    COMPLETE = "complete"        # Squad + all assistants + local configs
    SQUAD_ONLY = "squad_only"    # Only squad data
    WITH_ASSISTANTS = "with_assistants"  # Squad + assistants (no local configs)


@dataclass
class SquadBackupData:
    """Complete backup data for a squad with all related components."""
    squad_name: str
    squad_vapi_data: Optional[Dict[str, Any]] = None  # VAPI squad data
    squad_local_config: Optional[Dict[str, Any]] = None  # Local squad configuration
    squad_deployment_state: Optional[Dict[str, Any]] = None  # Squad deployment tracking
    squad_file_contents: Optional[Dict[str, str]] = None  # Squad config files

    # Related assistants data
    assistant_backups: List[AssistantBackupData] = field(default_factory=list)
    assistant_dependencies: Dict[str, str] = field(default_factory=dict)  # assistant_name -> assistant_id mapping

    backup_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'squad_name': self.squad_name,
            'squad_vapi_data': self.squad_vapi_data,
            'squad_local_config': self.squad_local_config,
            'squad_deployment_state': self.squad_deployment_state,
            'squad_file_contents': self.squad_file_contents,
            'assistant_backups': [a.to_dict() for a in self.assistant_backups],
            'assistant_dependencies': self.assistant_dependencies,
            'backup_timestamp': self.backup_timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SquadBackupData':
        """Create from dictionary."""
        from ..core.backup_models import AssistantBackupData

        return cls(
            squad_name=data['squad_name'],
            squad_vapi_data=data.get('squad_vapi_data'),
            squad_local_config=data.get('squad_local_config'),
            squad_deployment_state=data.get('squad_deployment_state'),
            squad_file_contents=data.get('squad_file_contents'),
            assistant_backups=[AssistantBackupData.from_dict(a) for a in data.get('assistant_backups', [])],
            assistant_dependencies=data.get('assistant_dependencies', {}),
            backup_timestamp=datetime.fromisoformat(data['backup_timestamp'])
        )

    def get_assistant_names(self) -> Set[str]:
        """Get set of all assistant names in this backup."""
        return {backup.assistant_name for backup in self.assistant_backups}

    def get_assistant_backup(self, assistant_name: str) -> Optional[AssistantBackupData]:
        """Get backup data for a specific assistant."""
        for backup in self.assistant_backups:
            if backup.assistant_name == assistant_name:
                return backup
        return None


@dataclass
class SquadBackupMetadata(BackupMetadata):
    """Extended metadata for squad backups."""
    squad_backup_type: SquadBackupType = SquadBackupType.COMPLETE
    squad_member_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            'squad_backup_type': self.squad_backup_type.value,
            'squad_member_count': self.squad_member_count
        })
        return base_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SquadBackupMetadata':
        """Create from dictionary."""
        return cls(
            backup_id=data['backup_id'],
            created_at=datetime.fromisoformat(data['created_at']),
            created_by=data['created_by'],
            backup_type=BackupType(data['backup_type']),
            backup_scope=BackupScope(data['backup_scope']),
            environment=data['environment'],
            assistant_count=data['assistant_count'],
            total_size_bytes=data['total_size_bytes'],
            description=data.get('description'),
            tags=data.get('tags', []),
            status=BackupStatus(data.get('status', 'created')),
            squad_backup_type=SquadBackupType(data.get('squad_backup_type', 'complete')),
            squad_member_count=data.get('squad_member_count', 0)
        )


class SquadBackupManifest:
    """Complete squad backup manifest containing all squad and assistant data."""

    def __init__(
        self,
        metadata: SquadBackupMetadata,
        squad_backup: SquadBackupData,
        backup_format_version: str = "1.0",
        checksum: Optional[str] = None
    ):
        self.metadata = metadata
        self.squad_backup = squad_backup
        self.backup_format_version = backup_format_version
        self.checksum = checksum

    def calculate_checksum(self) -> str:
        """Calculate checksum for backup integrity."""
        import hashlib
        from datetime import datetime

        def json_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)

        # Create a deterministic string representation
        data_str = json.dumps({
            'metadata': self.metadata.to_dict(),
            'squad_backup': self.squad_backup.to_dict(),
            'backup_format_version': self.backup_format_version
        }, sort_keys=True, default=json_serializer)

        return hashlib.sha256(data_str.encode()).hexdigest()

    def validate_integrity(self) -> bool:
        """Validate backup integrity using checksum."""
        if not self.checksum:
            return False
        return self.calculate_checksum() == self.checksum

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'metadata': self.metadata.to_dict(),
            'squad_backup': self.squad_backup.to_dict(),
            'backup_format_version': self.backup_format_version,
            'checksum': self.checksum
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SquadBackupManifest':
        """Create from dictionary."""
        return cls(
            metadata=SquadBackupMetadata.from_dict(data['metadata']),
            squad_backup=SquadBackupData.from_dict(data['squad_backup']),
            backup_format_version=data.get('backup_format_version', '1.0'),
            checksum=data.get('checksum')
        )


@dataclass
class SquadRestoreOptions(RestoreOptions):
    """Extended restore options for squad restoration."""
    restore_assistants: bool = True
    create_missing_assistants: bool = True
    assistant_name_prefix: str = ""  # Prefix for restored assistant names
    squad_name_override: Optional[str] = None  # Override squad name
    skip_assistant_deployment: bool = False  # Skip deploying assistants to VAPI

    def validate(self) -> List[str]:
        """Validate squad restore options."""
        errors = super().validate()

        if not self.restore_local_config and not self.restore_vapi_data and not self.restore_assistants:
            errors.append("At least one of restore_local_config, restore_vapi_data, or restore_assistants must be True")

        return errors


@dataclass
class SquadRestoreResult(RestoreResult):
    """Extended result for squad restore operations."""
    restored_squad: Optional[str] = None
    skipped_squad: bool = False
    failed_squad: bool = False

    # Assistant-specific results are inherited from RestoreResult
    assistant_restore_details: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def add_assistant_detail(self, assistant_name: str, details: Dict[str, Any]):
        """Add detailed restore information for an assistant."""
        self.assistant_restore_details[assistant_name] = details

    def mark_squad_restored(self, squad_name: str):
        """Mark squad as successfully restored."""
        self.restored_squad = squad_name

    def mark_squad_skipped(self):
        """Mark squad as skipped."""
        self.skipped_squad = True

    def mark_squad_failed(self):
        """Mark squad as failed to restore."""
        self.failed_squad = True