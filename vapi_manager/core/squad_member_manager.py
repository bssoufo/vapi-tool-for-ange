"""
Squad Member Manager

This module provides functionality to manage squad members by adding,
removing, and updating members in the members.yaml file.
"""

import os
import yaml
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class SquadMemberManager:
    """Manages squad members in the members.yaml file."""

    def __init__(self, squads_dir: str = "squads"):
        self.squads_dir = Path(squads_dir)

    def add_member_to_squad(
        self,
        squad_name: str,
        assistant_name: str,
        role: Optional[str] = None,
        priority: Optional[int] = None,
        description: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
        destinations: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Add a new member to a squad's members.yaml file.

        Args:
            squad_name: Name of the squad
            assistant_name: Name of the assistant to add
            role: Optional role for the assistant
            priority: Optional priority (will auto-increment if not provided)
            description: Optional description of the assistant's role
            overrides: Optional configuration overrides
            destinations: Optional routing destinations

        Returns:
            Dict with operation result including backup path if created
        """
        members_file = self.squads_dir / squad_name / "members.yaml"

        if not members_file.exists():
            raise FileNotFoundError(f"Members file not found: {members_file}")

        # Create backup before modifying
        backup_path = self._create_backup(members_file)

        try:
            # Load existing configuration
            with open(members_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}

            # Ensure members list exists
            if 'members' not in config:
                config['members'] = []

            # Check if assistant already exists
            existing_members = config['members']
            for member in existing_members:
                if member.get('assistant_name') == assistant_name:
                    raise ValueError(f"Assistant '{assistant_name}' is already a member of squad '{squad_name}'")

            # Auto-calculate priority if not provided
            if priority is None:
                priorities = [m.get('priority', 0) for m in existing_members]
                priority = max(priorities) + 1 if priorities else 1

            # Build new member entry
            new_member = {
                'assistant_name': assistant_name,
                'role': role or assistant_name.replace('-ange', '').replace('_', ' '),
                'priority': priority,
                'description': description or f"Assistant {assistant_name}"
            }

            # Add optional fields if provided
            if overrides:
                new_member['overrides'] = overrides

            if destinations:
                new_member['destinations'] = destinations

            # Add the new member
            config['members'].append(new_member)

            # Sort members by priority
            config['members'] = sorted(config['members'], key=lambda x: x.get('priority', 999))

            # Save updated configuration
            with open(members_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            return {
                'success': True,
                'message': f"Successfully added '{assistant_name}' to squad '{squad_name}'",
                'backup_path': str(backup_path),
                'member_data': new_member
            }

        except Exception as e:
            # Restore backup on error
            if backup_path and backup_path.exists():
                shutil.copy2(backup_path, members_file)
            raise e

    def remove_member_from_squad(self, squad_name: str, assistant_name: str) -> Dict[str, Any]:
        """
        Remove a member from a squad's members.yaml file.

        Args:
            squad_name: Name of the squad
            assistant_name: Name of the assistant to remove

        Returns:
            Dict with operation result
        """
        members_file = self.squads_dir / squad_name / "members.yaml"

        if not members_file.exists():
            raise FileNotFoundError(f"Members file not found: {members_file}")

        # Create backup before modifying
        backup_path = self._create_backup(members_file)

        try:
            # Load existing configuration
            with open(members_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}

            if 'members' not in config:
                raise ValueError(f"No members found in squad '{squad_name}'")

            # Find and remove the member
            original_count = len(config['members'])
            config['members'] = [m for m in config['members'] if m.get('assistant_name') != assistant_name]

            if len(config['members']) == original_count:
                raise ValueError(f"Assistant '{assistant_name}' is not a member of squad '{squad_name}'")

            # Save updated configuration
            with open(members_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            return {
                'success': True,
                'message': f"Successfully removed '{assistant_name}' from squad '{squad_name}'",
                'backup_path': str(backup_path)
            }

        except Exception as e:
            # Restore backup on error
            if backup_path and backup_path.exists():
                shutil.copy2(backup_path, members_file)
            raise e

    def list_squad_members(self, squad_name: str) -> List[str]:
        """
        List all members of a squad.

        Args:
            squad_name: Name of the squad

        Returns:
            List of assistant names
        """
        members_file = self.squads_dir / squad_name / "members.yaml"

        if not members_file.exists():
            raise FileNotFoundError(f"Members file not found: {members_file}")

        with open(members_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        members = config.get('members', [])
        return [m.get('assistant_name') for m in members if m.get('assistant_name')]

    def _create_backup(self, file_path: Path) -> Path:
        """Create a backup of the file before modifying."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = file_path.parent / ".backups"
        backup_dir.mkdir(exist_ok=True)

        backup_path = backup_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
        shutil.copy2(file_path, backup_path)

        return backup_path

    def validate_squad_exists(self, squad_name: str) -> bool:
        """Check if a squad configuration exists."""
        squad_dir = self.squads_dir / squad_name
        members_file = squad_dir / "members.yaml"
        return squad_dir.exists() and members_file.exists()