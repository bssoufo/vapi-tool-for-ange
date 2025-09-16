"""
Template Manager for Assistant Initialization

This module handles template management and assistant initialization from templates.
"""

import os
import shutil
import re
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console

console = Console()


class TemplateManager:
    """Manages assistant templates and initialization."""

    def __init__(self, templates_dir: str = "templates", assistants_dir: str = "assistants"):
        self.templates_dir = Path(templates_dir)
        self.assistants_dir = Path(assistants_dir)

    def list_templates(self) -> List[str]:
        """List all available templates."""
        if not self.templates_dir.exists():
            return []

        return [d.name for d in self.templates_dir.iterdir() if d.is_dir()]

    def template_exists(self, template_name: str) -> bool:
        """Check if a template exists."""
        return (self.templates_dir / template_name).exists()

    def assistant_exists(self, assistant_name: str) -> bool:
        """Check if an assistant directory already exists."""
        return (self.assistants_dir / assistant_name).exists()

    def get_template_info(self, template_name: str) -> Dict[str, any]:
        """Get information about a template."""
        template_path = self.templates_dir / template_name

        if not template_path.exists():
            raise FileNotFoundError(f"Template '{template_name}' not found")

        info = {
            "name": template_name,
            "path": template_path,
            "files": {},
            "directories": []
        }

        # Check for key files
        key_files = [
            "assistant.yaml",
            "prompts/system.md",
            "prompts/first_message.md"
        ]

        for file_path in key_files:
            full_path = template_path / file_path
            info["files"][file_path] = full_path.exists()

        # Check for directories
        for item in template_path.iterdir():
            if item.is_dir():
                info["directories"].append(item.name)

        return info

    def init_assistant(
        self,
        assistant_name: str,
        template_name: str = "vicky_dental_clinic",
        force: bool = False,
        variables: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Initialize a new assistant from a template.

        Args:
            assistant_name: Name of the new assistant
            template_name: Template to use
            force: Overwrite if assistant already exists
            variables: Template variables to substitute

        Returns:
            True if successful, False otherwise
        """
        # Validate inputs
        if not self._validate_assistant_name(assistant_name):
            console.print(f"[red]Invalid assistant name: {assistant_name}[/red]")
            console.print("[yellow]Name must contain only letters, numbers, hyphens, and underscores[/yellow]")
            return False

        if not self.template_exists(template_name):
            console.print(f"[red]Template '{template_name}' not found[/red]")
            console.print(f"[yellow]Available templates: {', '.join(self.list_templates())}[/yellow]")
            return False

        # Check if assistant already exists
        if self.assistant_exists(assistant_name) and not force:
            console.print(f"[red]Assistant '{assistant_name}' already exists[/red]")
            console.print("[yellow]Use --force to overwrite[/yellow]")
            return False

        # Set up default variables
        if variables is None:
            variables = {}

        variables.setdefault("assistant_name", assistant_name)

        try:
            # Create assistant directory
            assistant_path = self.assistants_dir / assistant_name
            assistant_path.mkdir(parents=True, exist_ok=force)

            # Copy template files
            template_path = self.templates_dir / template_name
            self._copy_template(template_path, assistant_path, variables)

            console.print(f"[green]+ Assistant '{assistant_name}' created successfully![/green]")
            console.print(f"[cyan]Location:[/cyan] {assistant_path}")
            console.print(f"[cyan]Template:[/cyan] {template_name}")

            # Show next steps
            console.print("\n[cyan]Next steps:[/cyan]")
            console.print(f"  1. Edit configuration: {assistant_path}/assistant.yaml")
            console.print(f"  2. Customize prompts: {assistant_path}/prompts/")
            console.print(f"  3. Validate: poetry run vapi-manager file validate {assistant_name}")
            console.print(f"  4. Deploy: poetry run vapi-manager file deploy {assistant_name}")

            return True

        except Exception as e:
            console.print(f"[red]Failed to create assistant: {e}[/red]")
            return False

    def _validate_assistant_name(self, name: str) -> bool:
        """Validate assistant name format."""
        # Allow letters, numbers, hyphens, and underscores
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, name)) and len(name) > 0

    def _copy_template(self, template_path: Path, target_path: Path, variables: Dict[str, str]):
        """Copy template files and substitute variables."""
        for item in template_path.rglob('*'):
            if item.is_file():
                # Calculate relative path
                rel_path = item.relative_to(template_path)
                target_file = target_path / rel_path

                # Create parent directories
                target_file.parent.mkdir(parents=True, exist_ok=True)

                # Read, substitute variables, and write
                try:
                    with open(item, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Substitute template variables
                    content = self._substitute_variables(content, variables)

                    with open(target_file, 'w', encoding='utf-8') as f:
                        f.write(content)

                except Exception as e:
                    console.print(f"[yellow]Warning: Could not process {rel_path}: {e}[/yellow]")
                    # Fall back to binary copy
                    shutil.copy2(item, target_file)

    def _substitute_variables(self, content: str, variables: Dict[str, str]) -> str:
        """Substitute template variables in content."""
        # Replace {{variable}} patterns
        for key, value in variables.items():
            pattern = f"{{{{{key}}}}}"
            content = content.replace(pattern, value)

        # Replace ${ENV_VAR} patterns with environment variables
        env_pattern = r'\$\{([^}]+)\}'

        def env_replacer(match):
            env_var = match.group(1)
            return os.environ.get(env_var, match.group(0))

        content = re.sub(env_pattern, env_replacer, content)

        return content

    def show_template_info(self, template_name: str):
        """Display detailed information about a template."""
        try:
            info = self.get_template_info(template_name)

            console.print(f"\n[cyan]Template:[/cyan] {template_name}")
            console.print(f"[cyan]Path:[/cyan] {info['path']}")

            console.print(f"\n[cyan]Structure:[/cyan]")

            # Show files
            for file_path, exists in info["files"].items():
                status = "[green]+[/green]" if exists else "[red]x[/red]"
                console.print(f"  {status} {file_path}")

            # Show directories
            if info["directories"]:
                console.print(f"\n[cyan]Directories:[/cyan]")
                for directory in info["directories"]:
                    console.print(f"  [blue]DIR[/blue] {directory}/")

        except FileNotFoundError as e:
            console.print(f"[red]Error: {e}[/red]")