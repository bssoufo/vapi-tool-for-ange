"""
Squad Backup Utilities

This module provides utility functions for squad backup operations including
validation, integrity checks, and backup organization.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from ..core.squad_backup_models import SquadBackupManifest, SquadBackupMetadata
from ..core.squad_backup_manager import SquadBackupManager


class SquadBackupUtils:
    """Utility functions for squad backup management."""

    @staticmethod
    def validate_squad_backup_file(backup_path: str) -> Tuple[bool, List[str]]:
        """
        Validate a squad backup file for integrity and completeness.

        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        backup_file = Path(backup_path)

        if not backup_file.exists():
            return False, ["Squad backup file does not exist"]

        try:
            # Load and parse JSON
            with open(backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate required fields
            if 'metadata' not in data:
                errors.append("Missing metadata section")

            if 'squad_backup' not in data:
                errors.append("Missing squad_backup section")

            if 'backup_format_version' not in data:
                errors.append("Missing backup_format_version")

            if errors:
                return False, errors

            # Create manifest and validate integrity
            manifest = SquadBackupManifest.from_dict(data)

            if not manifest.validate_integrity():
                errors.append("Squad backup integrity check failed - checksum mismatch")

            # Validate squad data
            squad_backup = manifest.squad_backup
            if not squad_backup.squad_name:
                errors.append("Missing squad name")

            if not squad_backup.squad_vapi_data and not squad_backup.squad_local_config:
                errors.append("No squad backup data found (neither VAPI nor local config)")

            # Validate assistant data
            for i, assistant in enumerate(squad_backup.assistant_backups):
                if not assistant.assistant_name:
                    errors.append(f"Assistant {i}: Missing assistant_name")

            return len(errors) == 0, errors

        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON format: {str(e)}"]
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]

    @staticmethod
    def analyze_squad_backup(backup_path: str) -> Dict[str, Any]:
        """
        Analyze a squad backup and return detailed information.

        Returns:
            Dictionary with backup analysis
        """
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            manifest = SquadBackupManifest.from_dict(data)
            squad_backup = manifest.squad_backup

            analysis = {
                'backup_id': manifest.metadata.backup_id,
                'squad_name': squad_backup.squad_name,
                'created_at': manifest.metadata.created_at.isoformat(),
                'environment': manifest.metadata.environment,
                'backup_type': manifest.metadata.squad_backup_type.value,
                'total_size': manifest.metadata.total_size_bytes,
                'integrity_valid': manifest.validate_integrity(),

                # Squad data analysis
                'squad_data': {
                    'has_vapi_data': bool(squad_backup.squad_vapi_data),
                    'has_local_config': bool(squad_backup.squad_local_config),
                    'has_deployment_state': bool(squad_backup.squad_deployment_state),
                    'file_count': len(squad_backup.squad_file_contents) if squad_backup.squad_file_contents else 0,
                    'member_count': len(squad_backup.assistant_dependencies)
                },

                # Assistant analysis
                'assistants': {
                    'total_count': len(squad_backup.assistant_backups),
                    'with_vapi_data': sum(1 for a in squad_backup.assistant_backups if a.vapi_data),
                    'with_local_config': sum(1 for a in squad_backup.assistant_backups if a.local_config),
                    'with_files': sum(1 for a in squad_backup.assistant_backups if a.file_contents),
                    'assistant_list': [
                        {
                            'name': a.assistant_name,
                            'has_vapi': bool(a.vapi_data),
                            'has_config': bool(a.local_config),
                            'file_count': len(a.file_contents) if a.file_contents else 0
                        }
                        for a in squad_backup.assistant_backups
                    ]
                },

                # Dependencies analysis
                'dependencies': {
                    'assistant_mapping': squad_backup.assistant_dependencies,
                    'total_dependencies': len(squad_backup.assistant_dependencies)
                }
            }

            return analysis

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def compare_squad_backups(backup_path1: str, backup_path2: str) -> Dict[str, Any]:
        """
        Compare two squad backup files and return differences.

        Returns:
            Dictionary with comparison results
        """
        comparison = {
            'squad_differences': {},
            'assistants_backup1_only': [],
            'assistants_backup2_only': [],
            'assistants_common': [],
            'assistant_differences': {}
        }

        try:
            # Load both backups
            with open(backup_path1, 'r', encoding='utf-8') as f:
                data1 = json.load(f)
            with open(backup_path2, 'r', encoding='utf-8') as f:
                data2 = json.load(f)

            manifest1 = SquadBackupManifest.from_dict(data1)
            manifest2 = SquadBackupManifest.from_dict(data2)

            # Compare squad metadata
            comparison['squad_differences'] = {
                'backup1': {
                    'squad_name': manifest1.squad_backup.squad_name,
                    'created_at': manifest1.metadata.created_at.isoformat(),
                    'environment': manifest1.metadata.environment,
                    'backup_type': manifest1.metadata.squad_backup_type.value,
                    'assistant_count': len(manifest1.squad_backup.assistant_backups)
                },
                'backup2': {
                    'squad_name': manifest2.squad_backup.squad_name,
                    'created_at': manifest2.metadata.created_at.isoformat(),
                    'environment': manifest2.metadata.environment,
                    'backup_type': manifest2.metadata.squad_backup_type.value,
                    'assistant_count': len(manifest2.squad_backup.assistant_backups)
                }
            }

            # Compare assistants
            assistants1 = {a.assistant_name for a in manifest1.squad_backup.assistant_backups}
            assistants2 = {a.assistant_name for a in manifest2.squad_backup.assistant_backups}

            comparison['assistants_backup1_only'] = list(assistants1 - assistants2)
            comparison['assistants_backup2_only'] = list(assistants2 - assistants1)
            comparison['assistants_common'] = list(assistants1 & assistants2)

            return comparison

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def extract_assistant_list(backup_path: str) -> List[str]:
        """
        Extract list of assistant names from a squad backup.

        Returns:
            List of assistant names
        """
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            manifest = SquadBackupManifest.from_dict(data)
            return [a.assistant_name for a in manifest.squad_backup.assistant_backups]

        except Exception:
            return []

    @staticmethod
    def validate_restore_compatibility(
        backup_path: str,
        target_environment: str,
        existing_squads: List[str],
        existing_assistants: List[str]
    ) -> Dict[str, Any]:
        """
        Validate if a squad backup can be restored to the target environment.

        Returns:
            Dictionary with compatibility analysis
        """
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            manifest = SquadBackupManifest.from_dict(data)
            squad_backup = manifest.squad_backup

            compatibility = {
                'can_restore': True,
                'issues': [],
                'warnings': [],
                'squad_conflicts': [],
                'assistant_conflicts': [],
                'missing_dependencies': []
            }

            # Check squad name conflicts
            if squad_backup.squad_name in existing_squads:
                compatibility['squad_conflicts'].append(squad_backup.squad_name)
                compatibility['warnings'].append(f"Squad '{squad_backup.squad_name}' already exists")

            # Check assistant name conflicts
            for assistant_backup in squad_backup.assistant_backups:
                if assistant_backup.assistant_name in existing_assistants:
                    compatibility['assistant_conflicts'].append(assistant_backup.assistant_name)
                    compatibility['warnings'].append(f"Assistant '{assistant_backup.assistant_name}' already exists")

            # Check for missing data
            if not squad_backup.squad_vapi_data and not squad_backup.squad_local_config:
                compatibility['issues'].append("No squad data available for restore")
                compatibility['can_restore'] = False

            # Check assistant data completeness
            assistants_without_data = []
            for assistant_backup in squad_backup.assistant_backups:
                if not assistant_backup.vapi_data and not assistant_backup.local_config:
                    assistants_without_data.append(assistant_backup.assistant_name)

            if assistants_without_data:
                compatibility['issues'].extend([
                    f"Assistant '{name}' has no backup data" for name in assistants_without_data
                ])

            return compatibility

        except Exception as e:
            return {
                'can_restore': False,
                'issues': [f"Failed to analyze backup: {str(e)}"],
                'warnings': [],
                'squad_conflicts': [],
                'assistant_conflicts': [],
                'missing_dependencies': []
            }

    @staticmethod
    def generate_squad_backup_report(backup_manager: SquadBackupManager) -> Dict[str, Any]:
        """
        Generate a comprehensive squad backup report.

        Returns:
            Dictionary with backup statistics and health information
        """
        backups = backup_manager.list_squad_backups()

        if not backups:
            return {
                'total_backups': 0,
                'total_size': 0,
                'backup_health': 'No squad backups found',
                'squad_coverage': {},
                'environment_coverage': {}
            }

        # Calculate statistics
        total_size = 0
        valid_backups = 0
        corrupted_backups = 0
        squad_names = set()
        environments = set()
        backup_types = {}

        for backup in backups:
            backup_file = backup_manager.backups_dir / f"{backup.backup_id}.json"
            if backup_file.exists():
                total_size += backup_file.stat().st_size

                # Check backup validity
                is_valid, _ = SquadBackupUtils.validate_squad_backup_file(str(backup_file))
                if is_valid:
                    valid_backups += 1

                    # Analyze backup content
                    try:
                        manifest = backup_manager.get_squad_backup_details(backup.backup_id)
                        if manifest:
                            squad_names.add(manifest.squad_backup.squad_name)
                            environments.add(backup.environment)

                            backup_type = backup.squad_backup_type.value
                            backup_types[backup_type] = backup_types.get(backup_type, 0) + 1
                    except Exception:
                        pass
                else:
                    corrupted_backups += 1

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
            'total_size_formatted': SquadBackupUtils.format_file_size(total_size),
            'backup_health': health,
            'unique_squads': len(squad_names),
            'squad_names': list(squad_names),
            'environments': list(environments),
            'backup_types': backup_types,
            'oldest_backup': min(backups, key=lambda b: b.created_at).created_at.isoformat() if backups else None,
            'newest_backup': max(backups, key=lambda b: b.created_at).created_at.isoformat() if backups else None
        }

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