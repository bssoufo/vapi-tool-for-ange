"""Squad-wide parameter updater for updating all assistants in a squad with common settings."""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID

from ..services import AssistantService, SquadService
from ..core.deployment_state import DeploymentStateManager
from ..core.squad_deployment_state import SquadDeploymentStateManager
from ..core.update_strategy import UpdateStrategy, UpdateOptions, UpdateScope
from ..core.squad_update_strategy import SquadUpdateStrategy
from ..core.assistant_config import AssistantConfigLoader, AssistantBuilder

console = Console()


class SquadParameterUpdater:
    """Handles updating parameters across all assistants in a squad."""

    def __init__(self, squads_dir: str = "squads", assistants_dir: str = "assistants"):
        self.squads_dir = Path(squads_dir)
        self.assistants_dir = Path(assistants_dir)

    async def update_squad_parameters(
        self,
        squad_name: str,
        parameters: Dict[str, Any],
        environment: str = "development",
        dry_run: bool = False,
        update_vapi: bool = False,
        squads_dir: Optional[str] = None,
        assistants_dir: Optional[str] = None
    ) -> bool:
        """
        Update parameters for all assistants in a squad.

        Args:
            squad_name: Name of the squad
            parameters: Dictionary of parameters to update
            environment: Target environment
            dry_run: If True, show what would be updated without making changes
            update_vapi: If True, also update assistants in VAPI after local changes
            squads_dir: Override squads directory
            assistants_dir: Override assistants directory

        Returns:
            True if successful, False otherwise
        """
        if squads_dir:
            self.squads_dir = Path(squads_dir)
        if assistants_dir:
            self.assistants_dir = Path(assistants_dir)

        # Load squad configuration
        squad_path = self.squads_dir / squad_name
        if not squad_path.exists():
            console.print(f"[red]Squad '{squad_name}' not found[/red]")
            return False

        # Get list of assistants in the squad
        members_file = squad_path / "members.yaml"
        if not members_file.exists():
            console.print(f"[red]No members.yaml found for squad '{squad_name}'[/red]")
            return False

        with open(members_file) as f:
            members_config = yaml.safe_load(f)

        assistants = members_config.get('members', [])
        if not assistants:
            console.print(f"[yellow]No assistants found in squad '{squad_name}'[/yellow]")
            return False

        console.print(f"[cyan]Found {len(assistants)} assistants in squad '{squad_name}'[/cyan]")

        # Display update summary
        if dry_run:
            self._display_update_summary(assistants, parameters, dry_run=True)
            return True

        # Create a table to show progress
        table = Table(title=f"Updating Squad '{squad_name}' Parameters")
        table.add_column("Assistant", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="yellow")

        all_success = True
        updated_assistants = []

        # Update each assistant's configuration
        with Progress() as progress:
            task = progress.add_task("[cyan]Updating assistants...", total=len(assistants))

            for member in assistants:
                assistant_name = member.get('assistant_name', member.get('assistant'))
                if not assistant_name:
                    continue

                try:
                    # Update local configuration
                    if self._update_assistant_config(assistant_name, parameters, environment):
                        updated_assistants.append(assistant_name)
                        table.add_row(assistant_name, "✓ Updated", "Configuration updated")
                        progress.update(task, advance=1)
                    else:
                        table.add_row(assistant_name, "✗ Failed", "Failed to update configuration")
                        all_success = False

                except Exception as e:
                    table.add_row(assistant_name, "✗ Error", str(e))
                    all_success = False

        console.print(table)

        # Update in VAPI if requested
        if update_vapi and updated_assistants:
            console.print(f"\n[cyan]Updating {len(updated_assistants)} assistants in VAPI...[/cyan]")

            for assistant_name in updated_assistants:
                try:
                    await self._update_assistant_in_vapi(assistant_name, environment)
                    console.print(f"[green]✓ Updated '{assistant_name}' in VAPI[/green]")
                except Exception as e:
                    console.print(f"[red]✗ Failed to update '{assistant_name}' in VAPI: {e}[/red]")
                    all_success = False

        return all_success

    def _update_assistant_config(
        self,
        assistant_name: str,
        parameters: Dict[str, Any],
        environment: str
    ) -> bool:
        """
        Update an assistant's YAML configuration with new parameters.

        Args:
            assistant_name: Name of the assistant
            parameters: Parameters to update
            environment: Target environment

        Returns:
            True if successful, False otherwise
        """
        assistant_path = self.assistants_dir / assistant_name / "assistant.yaml"
        if not assistant_path.exists():
            console.print(f"[yellow]Assistant configuration not found: {assistant_path}[/yellow]")
            return False

        try:
            # Load existing configuration
            with open(assistant_path) as f:
                config = yaml.safe_load(f)

            # Apply updates to base configuration
            for key, value in parameters.items():
                if key in ['voice', 'model', 'transcriber']:
                    # For nested configs, merge with existing values
                    if isinstance(value, dict):
                        if key not in config:
                            config[key] = {}
                        config[key].update(value)
                    else:
                        config[key] = value
                elif key == 'features':
                    # For features, merge with existing
                    if 'features' not in config:
                        config['features'] = {}
                    config['features'].update(value)
                elif key == 'server':
                    # For server settings, merge with existing
                    if 'server' not in config:
                        config['server'] = {}
                    config['server'].update(value)
                else:
                    # For other top-level keys, replace
                    config[key] = value

            # Also update environment-specific settings if they exist
            if 'environments' in config and environment in config['environments']:
                env_config = config['environments'][environment]
                for key, value in parameters.items():
                    if key in ['voice', 'model', 'transcriber']:
                        if isinstance(value, dict):
                            if key not in env_config:
                                env_config[key] = {}
                            env_config[key].update(value)
                        else:
                            env_config[key] = value
                    elif key not in ['features', 'server']:
                        # Some settings like features and server are typically not environment-specific
                        env_config[key] = value

            # Save updated configuration
            with open(assistant_path, 'w') as f:
                yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

            return True

        except Exception as e:
            console.print(f"[red]Error updating {assistant_name}: {e}[/red]")
            return False

    async def _update_assistant_in_vapi(self, assistant_name: str, environment: str):
        """
        Update an assistant in VAPI with the new configuration.

        Args:
            assistant_name: Name of the assistant
            environment: Target environment
        """
        # Load updated configuration
        loader = AssistantConfigLoader(base_dir=str(self.assistants_dir))
        config = await loader.load_assistant_config(assistant_name)

        # Get deployment info
        state_manager = DeploymentStateManager(str(self.assistants_dir))
        deployment_info = state_manager.get_deployment_info(assistant_name, environment)

        if not deployment_info.is_deployed or not deployment_info.id:
            console.print(f"[yellow]Assistant '{assistant_name}' not deployed in {environment}[/yellow]")
            return

        # Build and update assistant
        builder = AssistantBuilder(base_dir=str(self.assistants_dir))
        assistant_config = await builder.build_assistant(config, environment)

        service = AssistantService()
        strategy = UpdateStrategy(service, state_manager, base_dir=str(self.assistants_dir))

        options = UpdateOptions(
            force=False,
            update_tools=True,
            update_prompts=True,
            update_settings=True,
            scope=UpdateScope.FULL,
            backup_before_update=False
        )

        await strategy.update(assistant_name, environment, assistant_config, options)

    def _display_update_summary(
        self,
        assistants: List[Dict[str, Any]],
        parameters: Dict[str, Any],
        dry_run: bool = False
    ):
        """Display a summary of what will be updated."""
        title = "DRY RUN - Parameters to be updated" if dry_run else "Updating Parameters"

        table = Table(title=title)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="green")

        # Voice parameters
        if 'voice' in parameters:
            for key, value in parameters['voice'].items():
                table.add_row(f"voice.{key}", str(value))

        # Model parameters
        if 'model' in parameters:
            for key, value in parameters['model'].items():
                table.add_row(f"model.{key}", str(value))

        # Transcriber parameters
        if 'transcriber' in parameters:
            for key, value in parameters['transcriber'].items():
                table.add_row(f"transcriber.{key}", str(value))

        # Other parameters
        for key, value in parameters.items():
            if key not in ['voice', 'model', 'transcriber', 'features', 'server']:
                table.add_row(key, str(value))
            elif key == 'features':
                for fkey, fvalue in value.items():
                    table.add_row(f"features.{fkey}", str(fvalue))
            elif key == 'server':
                for skey, svalue in value.items():
                    table.add_row(f"server.{skey}", str(svalue))

        console.print(table)

        # List assistants that will be affected
        console.print(f"\n[cyan]Assistants to be updated ({len(assistants)}):[/cyan]")
        for member in assistants:
            if isinstance(member, dict):
                assistant_name = member.get('assistant_name', member.get('assistant', 'Unknown'))
            else:
                assistant_name = str(member)
            console.print(f"  • {assistant_name}")

    def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate parameters before applying updates.

        Args:
            parameters: Parameters to validate

        Returns:
            Dictionary of validation errors by parameter
        """
        errors = {}

        # Validate voice parameters
        if 'voice' in parameters:
            voice = parameters['voice']
            if 'provider' in voice:
                valid_providers = ['vapi', 'azure', 'cartesia', 'deepgram', 'elevenlabs',
                                  'lmnt', 'neets', 'openai', 'playht', 'rime']
                if voice['provider'] not in valid_providers:
                    errors.setdefault('voice', []).append(
                        f"Invalid voice provider: {voice['provider']}"
                    )

        # Validate model parameters
        if 'model' in parameters:
            model = parameters['model']
            if 'temperature' in model:
                temp = model['temperature']
                if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                    errors.setdefault('model', []).append(
                        f"Temperature must be between 0.0 and 2.0"
                    )
            if 'provider' in model:
                valid_providers = ['openai', 'anthropic', 'azure', 'google', 'together',
                                  'anyscale', 'openrouter', 'perplexity', 'deepinfra', 'groq']
                if model['provider'] not in valid_providers:
                    errors.setdefault('model', []).append(
                        f"Invalid model provider: {model['provider']}"
                    )

        # Validate transcriber parameters
        if 'transcriber' in parameters:
            trans = parameters['transcriber']
            if 'provider' in trans:
                valid_providers = ['deepgram', 'assembly', 'azure', 'google', 'groq']
                if trans['provider'] not in valid_providers:
                    errors.setdefault('transcriber', []).append(
                        f"Invalid transcriber provider: {trans['provider']}"
                    )

        return errors