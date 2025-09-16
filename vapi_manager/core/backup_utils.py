"""
Backup Management Utilities

This module provides utility functions for backup operations including
validation, cleanup, compression, and backup organization.
"""

import json
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from ..core.backup_models import BackupMetadata, BackupManifest, BackupStatus
from ..core.backup_manager import BackupManager


class BackupUtils:
    """Utility functions for backup management."""

    @staticmethod
    def validate_backup_file(backup_path: str) -> Tuple[bool, List[str]]:
        """
        Validate a backup file for integrity and completeness.

        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        backup_file = Path(backup_path)

        if not backup_file.exists():
            return False, ["Backup file does not exist"]

        try:
            # Load and parse JSON
            with open(backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate required fields
            if 'metadata' not in data:
                errors.append("Missing metadata section")

            if 'assistants' not in data:
                errors.append("Missing assistants section")

            if 'backup_format_version' not in data:
                errors.append("Missing backup_format_version")

            if errors:
                return False, errors

            # Create manifest and validate integrity
            manifest = BackupManifest.from_dict(data)

            if not manifest.validate_integrity():
                errors.append("Backup integrity check failed - checksum mismatch")

            # Validate assistant data
            for i, assistant in enumerate(manifest.assistants):
                if not assistant.assistant_name:
                    errors.append(f"Assistant {i}: Missing assistant_name")

                if not assistant.vapi_data and not assistant.local_config:
                    errors.append(f"Assistant {assistant.assistant_name}: No backup data found")

            return len(errors) == 0, errors

        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON format: {str(e)}"]
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]

    @staticmethod
    def compress_backup(backup_path: str, remove_original: bool = True) -> str:
        """
        Compress a backup file using gzip.

        Returns:
            Path to compressed backup file
        """
        backup_file = Path(backup_path)
        compressed_path = backup_file.with_suffix(backup_file.suffix + '.gz')

        with open(backup_file, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        if remove_original:
            backup_file.unlink()

        return str(compressed_path)

    @staticmethod
    def decompress_backup(compressed_path: str, output_path: Optional[str] = None) -> str:
        """
        Decompress a gzipped backup file.

        Returns:
            Path to decompressed backup file
        """
        compressed_file = Path(compressed_path)

        if output_path:
            output_file = Path(output_path)
        else:
            # Remove .gz extension
            output_file = compressed_file.with_suffix('')

        with gzip.open(compressed_file, 'rb') as f_in:
            with open(output_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        return str(output_file)

    @staticmethod
    def cleanup_old_backups(
        backup_manager: BackupManager,
        days_to_keep: int = 30,
        max_backups: int = 100
    ) -> List[str]:
        """
        Clean up old backup files based on age and count limits.

        Returns:
            List of deleted backup IDs
        """
        backups = backup_manager.list_backups()
        deleted_backups = []

        # Sort by creation date (oldest first)
        backups.sort(key=lambda b: b.created_at)

        cutoff_date = datetime.now().replace(tzinfo=None) - timedelta(days=days_to_keep)

        # Delete backups older than cutoff date
        for backup in backups:
            backup_date = backup.created_at.replace(tzinfo=None)
            if backup_date < cutoff_date:
                if backup_manager.delete_backup(backup.backup_id):
                    deleted_backups.append(backup.backup_id)

        # If still too many backups, delete oldest ones
        remaining_backups = [b for b in backups if b.backup_id not in deleted_backups]
        if len(remaining_backups) > max_backups:
            backups_to_delete = remaining_backups[:-max_backups]
            for backup in backups_to_delete:
                if backup_manager.delete_backup(backup.backup_id):
                    deleted_backups.append(backup.backup_id)

        return deleted_backups

    @staticmethod
    def export_backup_manifest(backup_path: str, export_path: str) -> bool:
        """
        Export backup manifest (metadata only) to a separate file.

        Returns:
            True if successful
        """
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            manifest_data = {
                'metadata': data['metadata'],
                'backup_format_version': data.get('backup_format_version', '1.0'),
                'assistant_names': [a['assistant_name'] for a in data.get('assistants', [])]
            }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(manifest_data, f, indent=2, default=str)

            return True

        except Exception:
            return False

    @staticmethod
    def compare_backups(backup_path1: str, backup_path2: str) -> Dict[str, Any]:
        """
        Compare two backup files and return differences.

        Returns:
            Dictionary with comparison results
        """
        comparison = {
            'backup1_only': [],
            'backup2_only': [],
            'common': [],
            'differences': {}
        }

        try:
            # Load both backups
            with open(backup_path1, 'r', encoding='utf-8') as f:
                data1 = json.load(f)
            with open(backup_path2, 'r', encoding='utf-8') as f:
                data2 = json.load(f)

            # Get assistant names from both backups
            assistants1 = {a['assistant_name'] for a in data1.get('assistants', [])}
            assistants2 = {a['assistant_name'] for a in data2.get('assistants', [])}

            comparison['backup1_only'] = list(assistants1 - assistants2)
            comparison['backup2_only'] = list(assistants2 - assistants1)
            comparison['common'] = list(assistants1 & assistants2)

            # Compare metadata
            meta1 = data1.get('metadata', {})
            meta2 = data2.get('metadata', {})

            comparison['metadata_differences'] = {
                'backup1': {
                    'created_at': meta1.get('created_at'),
                    'environment': meta1.get('environment'),
                    'assistant_count': meta1.get('assistant_count')
                },
                'backup2': {
                    'created_at': meta2.get('created_at'),
                    'environment': meta2.get('environment'),
                    'assistant_count': meta2.get('assistant_count')
                }
            }

            return comparison

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def get_backup_size(backup_path: str) -> int:
        """Get backup file size in bytes."""
        return Path(backup_path).stat().st_size

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size in human-readable format."""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math

        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)

        return f"{s} {size_names[i]}"

    @staticmethod
    def generate_backup_report(backup_manager: BackupManager) -> Dict[str, Any]:
        """
        Generate a comprehensive backup report.

        Returns:
            Dictionary with backup statistics and health information
        """
        backups = backup_manager.list_backups()

        if not backups:
            return {
                'total_backups': 0,
                'total_size': 0,
                'oldest_backup': None,
                'newest_backup': None,
                'backup_health': 'No backups found'
            }

        # Calculate statistics
        total_size = 0
        valid_backups = 0
        corrupted_backups = 0

        for backup in backups:
            backup_file = backup_manager.backups_dir / f"{backup.backup_id}.json"
            if backup_file.exists():
                total_size += backup_file.stat().st_size

                # Check backup validity
                is_valid, _ = BackupUtils.validate_backup_file(str(backup_file))
                if is_valid:
                    valid_backups += 1
                else:
                    corrupted_backups += 1

        # Sort by date
        backups.sort(key=lambda b: b.created_at)

        # Determine health status
        if corrupted_backups == 0:
            health = 'Healthy'
        elif corrupted_backups < len(backups) * 0.1:  # Less than 10% corrupted
            health = 'Minor Issues'
        else:
            health = 'Needs Attention'

        return {
            'total_backups': len(backups),
            'valid_backups': valid_backups,
            'corrupted_backups': corrupted_backups,
            'total_size': total_size,
            'total_size_formatted': BackupUtils.format_file_size(total_size),
            'oldest_backup': backups[0].created_at.isoformat() if backups else None,
            'newest_backup': backups[-1].created_at.isoformat() if backups else None,
            'backup_health': health,
            'environments': list(set(b.environment for b in backups)),
            'backup_types': list(set(b.backup_type.value for b in backups))
        }