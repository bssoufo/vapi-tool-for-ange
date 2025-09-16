"""
Backup and Restore Data Models

This module defines the data structures for backing up and restoring VAPI assistants,
including both local configurations and deployed VAPI data.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

from ..core.models.assistant import Assistant


class BackupType(str, Enum):
    """Type of backup."""
    FULL = "full"          # Complete assistant + local config
    VAPI_ONLY = "vapi_only"    # Only VAPI assistant data
    CONFIG_ONLY = "config_only"  # Only local configuration


class BackupScope(str, Enum):
    """Scope of backup operation."""
    SINGLE = "single"      # Single assistant
    MULTIPLE = "multiple"  # Multiple specific assistants
    ALL = "all"           # All assistants
    ENVIRONMENT = "environment"  # All assistants in specific environment


class BackupStatus(str, Enum):
    """Status of backup operation."""
    CREATED = "created"
    VALIDATED = "validated"
    CORRUPTED = "corrupted"
    PARTIAL = "partial"


@dataclass
class BackupMetadata:
    """Metadata for a backup."""
    backup_id: str
    created_at: datetime
    created_by: str
    backup_type: BackupType
    backup_scope: BackupScope
    environment: str
    assistant_count: int
    total_size_bytes: int
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    status: BackupStatus = BackupStatus.CREATED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'backup_id': self.backup_id,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'backup_type': self.backup_type.value,
            'backup_scope': self.backup_scope.value,
            'environment': self.environment,
            'assistant_count': self.assistant_count,
            'total_size_bytes': self.total_size_bytes,
            'description': self.description,
            'tags': self.tags,
            'status': self.status.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupMetadata':
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
            status=BackupStatus(data.get('status', 'created'))
        )


@dataclass
class AssistantBackupData:
    """Complete backup data for a single assistant."""
    assistant_name: str
    vapi_data: Optional[Dict[str, Any]] = None  # Raw VAPI assistant data
    local_config: Optional[Dict[str, Any]] = None  # Local configuration files
    deployment_state: Optional[Dict[str, Any]] = None  # Deployment tracking
    file_contents: Optional[Dict[str, str]] = None  # File contents (prompts, schemas, etc.)
    backup_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'assistant_name': self.assistant_name,
            'vapi_data': self.vapi_data,
            'local_config': self.local_config,
            'deployment_state': self.deployment_state,
            'file_contents': self.file_contents,
            'backup_timestamp': self.backup_timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AssistantBackupData':
        """Create from dictionary."""
        return cls(
            assistant_name=data['assistant_name'],
            vapi_data=data.get('vapi_data'),
            local_config=data.get('local_config'),
            deployment_state=data.get('deployment_state'),
            file_contents=data.get('file_contents'),
            backup_timestamp=datetime.fromisoformat(data['backup_timestamp'])
        )


class BackupManifest(BaseModel):
    """Complete backup manifest containing all data."""
    model_config = ConfigDict(extra="allow")

    metadata: BackupMetadata
    assistants: List[AssistantBackupData]
    backup_format_version: str = "1.0"
    checksum: Optional[str] = None

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
            'assistants': [a.to_dict() for a in self.assistants],
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
            'assistants': [a.to_dict() for a in self.assistants],
            'backup_format_version': self.backup_format_version,
            'checksum': self.checksum
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupManifest':
        """Create from dictionary."""
        return cls(
            metadata=BackupMetadata.from_dict(data['metadata']),
            assistants=[AssistantBackupData.from_dict(a) for a in data['assistants']],
            backup_format_version=data.get('backup_format_version', '1.0'),
            checksum=data.get('checksum')
        )


@dataclass
class RestoreOptions:
    """Options for restore operations."""
    target_environment: str = "development"
    overwrite_existing: bool = False
    restore_local_config: bool = True
    restore_vapi_data: bool = True
    restore_deployment_state: bool = True
    create_missing_directories: bool = True
    backup_before_restore: bool = True
    dry_run: bool = False

    def validate(self) -> List[str]:
        """Validate restore options."""
        errors = []

        if not self.restore_local_config and not self.restore_vapi_data:
            errors.append("At least one of restore_local_config or restore_vapi_data must be True")

        if self.target_environment not in ["development", "staging", "production"]:
            errors.append(f"Invalid target_environment: {self.target_environment}")

        return errors


@dataclass
class RestoreResult:
    """Result of a restore operation."""
    success: bool
    restored_assistants: List[str] = field(default_factory=list)
    skipped_assistants: List[str] = field(default_factory=list)
    failed_assistants: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    backup_created: Optional[str] = None  # ID of backup created before restore

    def add_error(self, message: str):
        """Add error message."""
        self.errors.append(message)

    def add_warning(self, message: str):
        """Add warning message."""
        self.warnings.append(message)

    def mark_restored(self, assistant_name: str):
        """Mark assistant as successfully restored."""
        self.restored_assistants.append(assistant_name)

    def mark_skipped(self, assistant_name: str):
        """Mark assistant as skipped."""
        self.skipped_assistants.append(assistant_name)

    def mark_failed(self, assistant_name: str):
        """Mark assistant as failed to restore."""
        self.failed_assistants.append(assistant_name)