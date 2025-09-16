"""
Squad Template Manager for Squad Initialization

This module handles squad template management and squad initialization from templates.
Extends the existing template system to support squad configurations.
"""

import os
import shutil
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from rich.console import Console

console = Console()


class SquadTemplateManager:
    """Manages squad templates and initialization."""

    def __init__(self, templates_dir: str = "templates/squads", squads_dir: str = "squads"):
        self.templates_dir = Path(templates_dir)
        self.squads_dir = Path(squads_dir)

    def list_templates(self) -> List[str]:
        """List all available squad templates."""
        if not self.templates_dir.exists():
            return []

        return [d.name for d in self.templates_dir.iterdir() if d.is_dir()]

    def template_exists(self, template_name: str) -> bool:
        """Check if a squad template exists."""
        return (self.templates_dir / template_name).exists()

    def squad_exists(self, squad_name: str) -> bool:
        """Check if a squad directory already exists."""
        return (self.squads_dir / squad_name).exists()

    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """Get information about a squad template."""
        template_path = self.templates_dir / template_name

        if not template_path.exists():
            raise FileNotFoundError(f"Squad template '{template_name}' not found")

        info = {
            "name": template_name,
            "path": template_path,
            "files": {},
            "directories": []
        }

        # Check for main configuration files
        squad_config = template_path / "squad.yaml"
        members_config = template_path / "members.yaml"

        if squad_config.exists():
            info["files"]["squad_config"] = squad_config
        if members_config.exists():
            info["files"]["members_config"] = members_config

        # Check for optional directories
        for subdir in ["overrides", "routing"]:
            subdir_path = template_path / subdir
            if subdir_path.exists():
                info["directories"].append(subdir)

        return info

    def initialize_squad(
        self,
        squad_name: str,
        template_name: str,
        assistants: Optional[List[str]] = None,
        description: Optional[str] = None,
        force: bool = False,
        env: str = "development"
    ) -> Path:
        """
        Initialize a new squad from a template.

        Args:
            squad_name: Name for the new squad
            template_name: Template to use
            assistants: List of assistant names to use
            description: Squad description
            force: Overwrite existing squad
            env: Target environment

        Returns:
            Path to the created squad directory
        """
        # Validate template exists
        if not self.template_exists(template_name):
            available = self.list_templates()
            raise FileNotFoundError(
                f"Squad template '{template_name}' not found. "
                f"Available templates: {', '.join(available) if available else 'None'}"
            )

        # Check if squad already exists
        squad_path = self.squads_dir / squad_name
        if squad_path.exists() and not force:
            raise FileExistsError(
                f"Squad '{squad_name}' already exists. Use --force to overwrite."
            )

        # Remove existing squad if force is enabled
        if squad_path.exists() and force:
            shutil.rmtree(squad_path)

        # Create squad directory
        squad_path.mkdir(parents=True, exist_ok=True)

        # Copy and process template files
        template_path = self.templates_dir / template_name
        variables = {
            "squad_name": squad_name,
            "description": description or f"Squad {squad_name}",
            "assistants": assistants or [],
            "env": env
        }

        self._copy_and_process_template(template_path, squad_path, variables)

        console.print(f"[green]+[/green] Squad '{squad_name}' initialized successfully")
        console.print(f"[cyan]Location:[/cyan] {squad_path}")

        return squad_path

    def _copy_and_process_template(self, source_path: Path, dest_path: Path, variables: Dict[str, Any]):
        """Copy template files and process variable substitutions."""
        for item in source_path.iterdir():
            if item.is_file():
                # Process file content
                dest_file = dest_path / item.name
                self._process_template_file(item, dest_file, variables)
            elif item.is_dir():
                # Copy directory recursively
                dest_dir = dest_path / item.name
                dest_dir.mkdir(exist_ok=True)
                self._copy_and_process_template(item, dest_dir, variables)

    def _process_template_file(self, source_file: Path, dest_file: Path, variables: Dict[str, Any]):
        """Process a single template file with variable substitution."""
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Process template variables
            processed_content = self._replace_template_variables(content, variables)

            with open(dest_file, 'w', encoding='utf-8') as f:
                f.write(processed_content)

        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not process {source_file.name}: {e}")
            # Fall back to simple copy
            shutil.copy2(source_file, dest_file)

    def _replace_template_variables(self, content: str, variables: Dict[str, Any]) -> str:
        """Replace template variables in content."""
        # Handle {{variable}} syntax
        def replace_var(match):
            var_expr = match.group(1).strip()

            # Handle default values: {{variable|default_value}}
            if '|' in var_expr:
                var_name, default_value = var_expr.split('|', 1)
                var_name = var_name.strip()
                default_value = default_value.strip()
            else:
                var_name = var_expr
                default_value = ''

            # Handle array access: {{assistants[0]}}
            if '[' in var_name and ']' in var_name:
                base_var, index_part = var_name.split('[', 1)
                index = int(index_part.split(']')[0])

                if base_var in variables and isinstance(variables[base_var], list):
                    try:
                        return str(variables[base_var][index])
                    except (IndexError, TypeError):
                        return default_value
                else:
                    return default_value

            # Simple variable replacement
            if var_name in variables:
                value = variables[var_name]
                if isinstance(value, list):
                    return ','.join(str(v) for v in value)
                return str(value)
            else:
                return default_value

        # Replace {{variable}} patterns
        content = re.sub(r'\{\{([^}]+)\}\}', replace_var, content)

        # Replace environment variables ${VAR}
        content = re.sub(r'\$\{([^}]+)\}', lambda m: os.environ.get(m.group(1), m.group(0)), content)

        return content

    def show_template_info(self, template_name: str):
        """Display detailed information about a squad template."""
        try:
            info = self.get_template_info(template_name)

            console.print(f"\n[bold cyan]Squad Template: {info['name']}[/bold cyan]")
            console.print(f"[dim]Location: {info['path']}[/dim]\n")

            # Show files
            if info["files"]:
                console.print("[bold]Configuration Files:[/bold]")
                if "squad_config" in info["files"]:
                    console.print("  [green]+[/green] Squad configuration (squad.yaml)")
                if "members_config" in info["files"]:
                    console.print("  [green]+[/green] Members configuration (members.yaml)")

            # Show directories
            if info["directories"]:
                console.print(f"\n[bold]Additional Components:[/bold]")
                for directory in info["directories"]:
                    console.print(f"  [blue]DIR[/blue] {directory}/")

            console.print()

        except FileNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")

    def validate_assistants(self, assistants: List[str], assistants_dir: str = "assistants") -> Dict[str, bool]:
        """
        Validate that specified assistants exist in the assistants directory.

        Args:
            assistants: List of assistant names to validate
            assistants_dir: Directory containing assistants

        Returns:
            Dictionary mapping assistant names to their existence status
        """
        assistants_path = Path(assistants_dir)
        validation_results = {}

        for assistant in assistants:
            assistant_path = assistants_path / assistant
            validation_results[assistant] = assistant_path.exists()

        return validation_results

    def list_available_assistants(self, assistants_dir: str = "assistants") -> List[str]:
        """List all available assistants in the assistants directory."""
        assistants_path = Path(assistants_dir)

        if not assistants_path.exists():
            return []

        return [d.name for d in assistants_path.iterdir() if d.is_dir()]