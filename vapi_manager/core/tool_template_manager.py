"""
Tool Template Manager for Shared Tool Creation

This module handles tool template management and shared tool generation from templates.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from rich.console import Console
from jinja2 import Environment, FileSystemLoader, meta

console = Console()


class ToolTemplateValidationError(Exception):
    """Raised when a tool template or generated tool is invalid."""
    pass


class ToolTemplateManager:
    """Manages tool templates and shared tool generation."""

    def __init__(self, templates_dir: str = "templates/tools", output_dir: str = "shared/tools"):
        self.templates_dir = Path(templates_dir)
        self.output_dir = Path(output_dir)
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=False
        )

    def list_templates(self) -> List[str]:
        """List all available tool templates."""
        if not self.templates_dir.exists():
            return []

        templates = []
        for file_path in self.templates_dir.glob("*.yaml"):
            templates.append(file_path.stem)

        return sorted(templates)

    def template_exists(self, template_name: str) -> bool:
        """Check if a template exists."""
        template_path = self.templates_dir / f"{template_name}.yaml"
        return template_path.exists()

    def tool_exists(self, tool_name: str) -> bool:
        """Check if a shared tool already exists."""
        tool_path = self.output_dir / f"{tool_name}.yaml"
        return tool_path.exists()

    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """Get information about a template."""
        template_path = self.templates_dir / f"{template_name}.yaml"

        if not template_path.exists():
            raise FileNotFoundError(f"Template '{template_name}' not found")

        info = {
            "name": template_name,
            "path": template_path,
            "variables": [],
            "description": None
        }

        try:
            # Read template content
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()

            # Extract Jinja2 variables
            parsed_content = self.jinja_env.parse(template_content)
            variables = meta.find_undeclared_variables(parsed_content)
            info["variables"] = sorted(list(variables))

            # Try to extract description from template metadata
            try:
                # Look for a comment at the top of the file
                lines = template_content.split('\n')
                for line in lines[:5]:  # Check first 5 lines
                    if line.strip().startswith('# Description:'):
                        info["description"] = line.strip()[13:].strip()
                        break
            except:
                pass

        except Exception as e:
            console.print(f"[yellow]Warning: Could not parse template '{template_name}': {e}[/yellow]")

        return info

    def create_tool(
        self,
        tool_name: str,
        template_name: str = "basic_webhook",
        force: bool = False,
        dry_run: bool = False,
        variables: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Create a new shared tool from a template.

        Args:
            tool_name: Name of the new tool (filename without .yaml)
            template_name: Template to use
            force: Overwrite if tool already exists
            dry_run: Show what would be created without actually creating
            variables: Template variables to substitute

        Returns:
            True if successful, False otherwise
        """
        # Validate inputs
        if not self._validate_tool_name(tool_name):
            console.print(f"[red]Invalid tool name: {tool_name}[/red]")
            console.print("[yellow]Name must contain only letters, numbers, hyphens, and underscores[/yellow]")
            return False

        if not self.template_exists(template_name):
            console.print(f"[red]Template '{template_name}' not found[/red]")
            available = self.list_templates()
            if available:
                console.print(f"[yellow]Available templates: {', '.join(available)}[/yellow]")
            else:
                console.print("[yellow]No templates found. Create templates in templates/tools/[/yellow]")
            return False

        # Check if tool already exists
        if self.tool_exists(tool_name) and not force:
            console.print(f"[red]Tool '{tool_name}' already exists[/red]")
            console.print("[yellow]Use --force to overwrite[/yellow]")
            return False

        # Prepare variables for template substitution
        template_vars = self._prepare_template_variables(tool_name, variables or {})

        try:
            # Load and render template
            template = self.jinja_env.get_template(f"{template_name}.yaml")
            rendered_content = template.render(**template_vars)

            # Validate the generated tool configuration
            tool_config = self._validate_generated_tool(rendered_content, tool_name)

            if dry_run:
                console.print(f"[cyan]Would create tool: {tool_name}.yaml[/cyan]")
                console.print(f"[cyan]Template: {template_name}[/cyan]")
                console.print(f"[cyan]Variables: {template_vars}[/cyan]")
                console.print("\n[cyan]Generated content:[/cyan]")
                console.print(rendered_content)
                return True

            # Create output directory if it doesn't exist
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Write the tool file
            tool_path = self.output_dir / f"{tool_name}.yaml"
            with open(tool_path, 'w', encoding='utf-8') as f:
                f.write(rendered_content)

            console.print(f"[green]Successfully created tool: {tool_path}[/green]")
            console.print(f"[cyan]Template used: {template_name}[/cyan]")

            # Show usage hint
            console.print(f"\n[cyan]Usage hint:[/cyan]")
            console.print(f"vapi-manager assistant add-tool <assistant_name> --tool shared/tools/{tool_name}.yaml")

            return True

        except ToolTemplateValidationError as e:
            console.print(f"[red]Tool validation failed: {e}[/red]")
            return False
        except Exception as e:
            console.print(f"[red]Error creating tool: {e}[/red]")
            return False

    def _validate_tool_name(self, name: str) -> bool:
        """Validate tool name format."""
        if not name:
            return False

        # Allow letters, numbers, hyphens, and underscores
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, name))

    def _prepare_template_variables(self, tool_name: str, user_variables: Dict[str, str]) -> Dict[str, str]:
        """Prepare template variables with defaults and user overrides."""
        # Start with default variables
        variables = {
            'tool_name': tool_name,
            'tool_name_upper': tool_name.upper().replace('-', '_'),
            'tool_name_camel': self._to_camel_case(tool_name),
        }

        # Add user variables, applying default filters
        for key, value in user_variables.items():
            if value is not None:
                variables[key] = value

        return variables

    def _to_camel_case(self, snake_str: str) -> str:
        """Convert snake_case or kebab-case to camelCase."""
        components = re.split(r'[_-]', snake_str)
        return components[0] + ''.join(word.capitalize() for word in components[1:])

    def _validate_generated_tool(self, content: str, tool_name: str) -> Dict[str, Any]:
        """Validate the generated tool configuration."""
        try:
            # Parse YAML
            tool_config = yaml.safe_load(content)

            if not isinstance(tool_config, dict):
                raise ToolTemplateValidationError("Tool configuration must be a YAML object")

            # Check required fields
            required_fields = ['name', 'description', 'parameters']
            for field in required_fields:
                if field not in tool_config:
                    raise ToolTemplateValidationError(f"Missing required field: {field}")

            # Validate name
            if not tool_config['name']:
                raise ToolTemplateValidationError("Tool name cannot be empty")

            # Validate description
            if not tool_config['description'] or not isinstance(tool_config['description'], str):
                raise ToolTemplateValidationError("Tool description must be a non-empty string")

            # Validate parameters structure
            parameters = tool_config.get('parameters', {})
            if not isinstance(parameters, dict):
                raise ToolTemplateValidationError("Parameters must be an object")

            if parameters.get('type') != 'object':
                raise ToolTemplateValidationError("Parameters type must be 'object'")

            # Validate server URL if present
            if 'server' in tool_config:
                server = tool_config['server']
                if isinstance(server, dict) and 'url' in server:
                    url = server['url']
                    if not url or not isinstance(url, str):
                        raise ToolTemplateValidationError("Server URL must be a non-empty string")

                    # Check URL format (allow environment variables)
                    if not (url.startswith('http') or url.startswith('${') or url.startswith('wss')):
                        raise ToolTemplateValidationError("Server URL must start with http, https, wss, or be an environment variable")

            return tool_config

        except yaml.YAMLError as e:
            raise ToolTemplateValidationError(f"Invalid YAML: {e}")
        except Exception as e:
            raise ToolTemplateValidationError(f"Validation error: {e}")

    def get_template_variables(self, template_name: str) -> List[str]:
        """Get list of variables used in a template."""
        try:
            template_info = self.get_template_info(template_name)
            return template_info.get('variables', [])
        except Exception:
            return []

    def preview_tool(self, tool_name: str, template_name: str, variables: Optional[Dict[str, str]] = None) -> str:
        """Preview what a tool would look like without creating it."""
        template_vars = self._prepare_template_variables(tool_name, variables or {})

        try:
            template = self.jinja_env.get_template(f"{template_name}.yaml")
            return template.render(**template_vars)
        except Exception as e:
            return f"Error previewing template: {e}"