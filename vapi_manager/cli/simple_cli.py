#!/usr/bin/env python3

import argparse
import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from ..services import AssistantService, SquadService, AgentService
from ..core.assistant_config import AssistantConfigLoader, AssistantBuilder
from ..core.template_manager import TemplateManager
from ..core.squad_template_manager import SquadTemplateManager
from ..core.squad_config import SquadConfigLoader, SquadBuilder
from ..core.squad_deployment_state import SquadDeploymentStateManager
from ..core.deployment_state import DeploymentStateManager
from ..core.update_strategy import UpdateStrategy, UpdateOptions, UpdateScope
from ..core.squad_update_strategy import SquadUpdateStrategy
from ..core.backup_manager import BackupManager
from ..core.backup_models import BackupType, RestoreOptions
from ..core.backup_utils import BackupUtils
from ..core.squad_backup_manager import SquadBackupManager
from ..core.squad_backup_models import SquadBackupType, SquadRestoreOptions
from ..core.squad_backup_utils import SquadBackupUtils
from ..core.exceptions.vapi_exceptions import VAPIException

console = Console()


async def list_assistants(limit=None):
    """List all assistants."""
    service = AssistantService()
    assistants = await service.list_assistants(limit=limit)

    if not assistants:
        console.print("[yellow]No assistants found[/yellow]")
        return

    table = Table(title="VAPI Assistants")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Model", style="green")
    table.add_column("Voice Provider", style="blue")
    table.add_column("Created", style="dim")

    for assistant in assistants:
        table.add_row(
            assistant.id or "N/A",
            assistant.name,
            assistant.model.model,
            assistant.voice.provider if assistant.voice else "N/A",
            assistant.created_at.strftime("%Y-%m-%d %H:%M") if assistant.created_at else "N/A"
        )

    console.print(table)


async def get_assistant(assistant_id):
    """Get assistant details by ID."""
    service = AssistantService()
    assistant = await service.get_assistant(assistant_id)

    console.print(f"[cyan]Assistant ID:[/cyan] {assistant.id}")
    console.print(f"[cyan]Name:[/cyan] {assistant.name}")
    console.print(f"[cyan]Model:[/cyan] {assistant.model.model} ({assistant.model.provider})")
    if assistant.voice:
        console.print(f"[cyan]Voice:[/cyan] {assistant.voice.voice_id} ({assistant.voice.provider})")
    else:
        console.print(f"[cyan]Voice:[/cyan] N/A")
    if assistant.first_message:
        console.print(f"[cyan]First Message:[/cyan] {assistant.first_message}")
    console.print(f"[cyan]Created:[/cyan] {assistant.created_at}")
    console.print(f"[cyan]Updated:[/cyan] {assistant.updated_at}")


async def delete_assistant(assistant_name, environment="development", force=False, directory="assistants"):
    """Delete an assistant from VAPI."""
    try:
        # Check if assistant configuration exists
        assistant_path = Path(directory) / assistant_name
        if not assistant_path.exists():
            console.print(f"[red]Assistant configuration not found: {assistant_path}[/red]")
            return False

        # Check deployment state
        from ..core.deployment_state import DeploymentStateManager
        state_manager = DeploymentStateManager(directory)
        deployment_info = state_manager.get_deployment_info(assistant_name, environment)

        assistant_id = None
        from ..services import AssistantService
        service = AssistantService()

        if deployment_info.is_deployed and deployment_info.id:
            assistant_id = deployment_info.id
        else:
            # If not tracked locally, try to find the assistant by name in VAPI
            console.print(f"[yellow]Assistant '{assistant_name}' not tracked locally. Searching in VAPI...[/yellow]")
            assistants = await service.list_assistants()

            # Find assistant by name
            matching_assistant = None
            for assistant in assistants:
                if assistant.name == assistant_name:
                    matching_assistant = assistant
                    break

            if matching_assistant:
                assistant_id = matching_assistant.id
                console.print(f"[green]Found assistant '{assistant_name}' in VAPI (ID: {assistant_id})[/green]")
            else:
                console.print(f"[red]Assistant '{assistant_name}' not found in VAPI[/red]")
                return False

        # Confirm deletion unless force is used
        if not force:
            from rich.prompt import Confirm
            deletion_message = f"[red]Are you sure you want to delete assistant '{assistant_name}' (ID: {assistant_id}) from {environment}?[/red]"
            confirmed = Confirm.ask(deletion_message)
            if not confirmed:
                console.print("[yellow]Assistant deletion cancelled[/yellow]")
                return False

        console.print(f"[yellow]Deleting assistant '{assistant_name}' from {environment}...[/yellow]")

        # Delete assistant from VAPI
        success = await service.delete_assistant(assistant_id)

        if success:
            # Remove assistant deployment tracking if it was tracked
            if deployment_info.is_deployed:
                state_manager.mark_undeployed(assistant_name, environment)
            console.print(f"[green]+ Assistant '{assistant_name}' deleted successfully from {environment}[/green]")
            console.print(f"[dim]Assistant ID: {assistant_id}[/dim]")
            return True
        else:
            console.print(f"[red]Failed to delete assistant '{assistant_name}' from {environment}[/red]")
            return False

    except Exception as e:
        console.print(f"[red]Error deleting assistant '{assistant_name}': {e}[/red]")
        return False


async def list_squads(limit=None):
    """List all squads."""
    service = SquadService()
    squads = await service.list_squads(limit=limit)

    if not squads:
        console.print("[yellow]No squads found[/yellow]")
        return

    table = Table(title="VAPI Squads")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Members", style="green")
    table.add_column("Created", style="dim")

    for squad in squads:
        members_count = len(squad.members) if squad.members else 0
        table.add_row(
            squad.id or "N/A",
            squad.name or "N/A",
            str(members_count),
            squad.created_at.strftime("%Y-%m-%d %H:%M") if squad.created_at else "N/A"
        )

    console.print(table)


async def get_squad(squad_id):
    """Get squad details by ID."""
    service = SquadService()
    squad = await service.get_squad(squad_id)

    console.print(f"[cyan]Squad ID:[/cyan] {squad.id}")
    console.print(f"[cyan]Name:[/cyan] {squad.name}")
    console.print(f"[cyan]Members:[/cyan] {len(squad.members)}")

    if squad.members:
        console.print("[cyan]Member Details:[/cyan]")
        for i, member in enumerate(squad.members, 1):
            console.print(f"  {i}. Assistant ID: {member.assistant_id}")
            if member.assistant_destinations:
                console.print(f"     Destinations: {len(member.assistant_destinations)}")

    console.print(f"[cyan]Created:[/cyan] {squad.created_at}")
    console.print(f"[cyan]Updated:[/cyan] {squad.updated_at}")


async def list_agents(limit=None):
    """List all agents."""
    service = AgentService()
    agents = await service.list_agents(limit=limit)

    if not agents:
        console.print("[yellow]No agents found[/yellow]")
        return

    table = Table(title="VAPI Agents")
    table.add_column("Squad ID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Assistants", style="green")
    table.add_column("Created", style="dim")

    for agent in agents:
        assistants_count = len(agent.assistants) if agent.assistants else 0
        table.add_row(
            agent.squad.id or "N/A",
            agent.name,
            str(assistants_count),
            agent.created_at.strftime("%Y-%m-%d %H:%M") if agent.created_at else "N/A"
        )

    console.print(table)


def list_file_assistants(directory="assistants"):
    """List all file-based assistant configurations."""
    loader = AssistantConfigLoader(directory)
    assistants = loader.list_assistants()

    if not assistants:
        console.print(f"[yellow]No assistant configurations found in {directory}/[/yellow]")
        return

    tree = Tree(f"[cyan]{directory}/[/cyan]")

    for assistant in assistants:
        assistant_path = Path(directory) / assistant
        branch = tree.add(f"[magenta]{assistant}/[/magenta]")

        # Check for key files
        if (assistant_path / "assistant.yaml").exists():
            branch.add("[green]+[/green] assistant.yaml")

        if (assistant_path / "prompts" / "system.md").exists():
            branch.add("[green]+[/green] prompts/system.md")

        if (assistant_path / "schemas").exists():
            schemas = list((assistant_path / "schemas").glob("*.{yaml,yml,json}"))
            if schemas:
                branch.add(f"[blue]{len(schemas)} schema(s)[/blue]")

        if (assistant_path / "tools").exists():
            tools = list((assistant_path / "tools").glob("*.{yaml,yml,json}"))
            if tools:
                branch.add(f"[yellow]{len(tools)} tool config(s)[/yellow]")

    console.print(tree)


async def update_assistant(assistant_name, environment="development", scope="full", dry_run=False, backup=True, force=False, directory="assistants"):
    """Update an existing assistant with safety measures and change detection."""
    console.print(f"[cyan]Updating assistant:[/cyan] {assistant_name}")
    console.print(f"[cyan]Environment:[/cyan] {environment}")
    console.print(f"[cyan]Scope:[/cyan] {scope}")

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No changes will be applied[/yellow]")

    try:
        # Create update strategy
        update_strategy = UpdateStrategy(directory)

        # Configure update options
        options = UpdateOptions(
            environment=environment,
            scope=UpdateScope(scope),
            dry_run=dry_run,
            backup=backup,
            force=force
        )

        # Perform the update
        result = await update_strategy.update_assistant(assistant_name, options)

        # Display results
        if result['status'] == 'no_changes':
            console.print(f"[yellow]{result['message']}[/yellow]")
        elif result['status'] == 'preview':
            console.print(f"[blue]{result['message']}[/blue]")
            console.print(f"[cyan]Total changes:[/cyan] {result['total_changes']}")

            if result['changes']:
                console.print("\n[bold]Changes to be applied:[/bold]")
                for change in result['changes']:
                    console.print(f"  [cyan]•[/cyan] {change['field']}: {change['change_type']}")
                    if change['change_type'] == 'modified':
                        console.print(f"    [red]- {change['old_value']}[/red]")
                        console.print(f"    [green]+ {change['new_value']}[/green]")
                    elif change['change_type'] == 'added':
                        console.print(f"    [green]+ {change['new_value']}[/green]")
                    elif change['change_type'] == 'removed':
                        console.print(f"    [red]- {change['old_value']}[/red]")

        elif result['status'] == 'success':
            console.print(f"[green]{result['message']}[/green]")
            console.print(f"[cyan]Assistant ID:[/cyan] {result['assistant_id']}")
            console.print(f"[cyan]Version:[/cyan] {result['version']}")

            if result['changes']:
                console.print(f"\n[bold]Changes applied:[/bold]")
                for change in result['changes']:
                    console.print(f"  [green]+[/green] {change['field']}: {change['change_type']}")

        console.print("\n[green]Update completed successfully![/green]")

    except VAPIException as e:
        console.print(f"[red]Update failed: {e}[/red]")
        raise


def init_squad(squad_name, template_name="dental_clinic_squad", assistants=None, description=None, force=False, directory="squads"):
    """Initialize a new squad from a template."""
    console.print(f"[cyan]Initializing squad:[/cyan] {squad_name}")
    console.print(f"[cyan]Template:[/cyan] {template_name}")

    if assistants:
        console.print(f"[cyan]Assistants:[/cyan] {', '.join(assistants)}")
    if description:
        console.print(f"[cyan]Description:[/cyan] {description}")

    try:
        # Create squad template manager
        squad_manager = SquadTemplateManager(squads_dir=directory)

        # Validate assistants if provided
        if assistants:
            validation_results = squad_manager.validate_assistants(assistants)
            missing_assistants = [name for name, exists in validation_results.items() if not exists]

            if missing_assistants:
                console.print(f"[yellow]Warning:[/yellow] Some assistants not found:")
                for assistant in missing_assistants:
                    console.print(f"  [red]x[/red] {assistant}")

                available_assistants = squad_manager.list_available_assistants()
                if available_assistants:
                    console.print(f"\n[cyan]Available assistants:[/cyan]")
                    for assistant in available_assistants:
                        console.print(f"  [green]+[/green] {assistant}")

                if not force:
                    console.print(f"\n[yellow]Use --force to proceed anyway[/yellow]")
                    return

        # Initialize the squad
        squad_path = squad_manager.initialize_squad(
            squad_name=squad_name,
            template_name=template_name,
            assistants=assistants,
            description=description,
            force=force
        )

        # Show success message with next steps
        console.print(f"\n[bold green]Squad '{squad_name}' created successfully![/bold green]")
        console.print(f"[cyan]Location:[/cyan] {squad_path}")

        console.print(f"\n[bold]Next steps:[/bold]")
        console.print(f"  1. Review configuration: [cyan]{squad_path}/squad.yaml[/cyan]")
        console.print(f"  2. Customize members: [cyan]{squad_path}/members.yaml[/cyan]")
        console.print(f"  3. Deploy squad: [cyan]vapi-manager squad create {squad_name} --env development[/cyan]")

    except Exception as e:
        console.print(f"[red]Error initializing squad: {e}[/red]")
        raise


def list_squad_templates():
    """List all available squad templates."""
    manager = SquadTemplateManager()
    templates = manager.list_templates()

    if not templates:
        console.print("[yellow]No squad templates found[/yellow]")
        console.print("[cyan]Templates should be in:[/cyan] templates/squads/")
        return

    console.print("[bold]Available Squad Templates:[/bold]\n")

    for template in templates:
        try:
            info = manager.get_template_info(template)
            console.print(f"[bold cyan]{template}[/bold cyan]")

            # Show available files
            has_config = "squad_config" in info["files"]
            has_members = "members_config" in info["files"]

            if has_config:
                console.print("  [green]+[/green] Squad configuration")
            if has_members:
                console.print("  [green]+[/green] Members configuration")

            # Show directories
            if info["directories"]:
                dirs_str = ", ".join(info["directories"])
                console.print(f"  [blue]Includes:[/blue] {dirs_str}")

            console.print()

        except Exception as e:
            console.print(f"  [red]Error reading template: {e}[/red]\n")


def show_squad_template_info(template_name):
    """Show detailed information about a squad template."""
    manager = SquadTemplateManager()
    manager.show_template_info(template_name)


def list_file_squads(directory="squads"):
    """List all squad configurations."""
    loader = SquadConfigLoader(directory)
    squads = loader.list_squads()

    if not squads:
        console.print("[yellow]No squads found[/yellow]")
        console.print(f"[cyan]Create a squad with:[/cyan] vapi-manager squad init <squad_name>")
        return

    console.print("[bold]Squad Configurations:[/bold]\n")

    for squad_name in squads:
        try:
            squad_config = loader.load_squad(squad_name)
            console.print(f"[bold cyan]{squad_name}[/bold cyan]")

            if squad_config.config.get('description'):
                console.print(f"  [dim]{squad_config.config['description']}[/dim]")

            member_count = len(squad_config.members)
            console.print(f"  [green]Members:[/green] {member_count}")

            for member in squad_config.members:
                role = member.get('role', 'assistant')
                assistant_name = member.get('assistant_name', 'Unknown')
                console.print(f"    • {assistant_name} ([blue]{role}[/blue])")

            console.print()

        except Exception as e:
            console.print(f"  [red]Error reading squad: {e}[/red]\n")


async def create_squad(squad_name, environment="development", force=False, directory="squads"):
    """Create a squad in VAPI and track its ID."""
    squad_state_manager = SquadDeploymentStateManager(directory)

    console.print(f"[cyan]Creating squad:[/cyan] {squad_name}")
    console.print(f"[cyan]Environment:[/cyan] {environment}")

    try:
        # Validate squad exists
        if not squad_state_manager.validate_squad_exists(squad_name):
            console.print(f"[red]Squad '{squad_name}' not found[/red]")
            console.print(f"[cyan]Use:[/cyan] vapi-manager squad init {squad_name}")
            return

        # Check if already deployed
        if squad_state_manager.is_deployed(squad_name, environment) and not force:
            deployment_info = squad_state_manager.get_deployment_info(squad_name, environment)
            console.print(f"[yellow]Squad '{squad_name}' already deployed to {environment}[/yellow]")
            console.print(f"[cyan]VAPI ID:[/cyan] {deployment_info.id}")
            console.print(f"[cyan]Deployed at:[/cyan] {deployment_info.deployed_at}")
            console.print(f"[cyan]Version:[/cyan] {deployment_info.version}")
            console.print("\n[cyan]Options:[/cyan]")
            console.print(f"  • Use --force to recreate squad")
            console.print(f"  • Use 'squad status' to see all deployments")
            return

        # Load squad configuration
        loader = SquadConfigLoader(directory)
        squad_config = loader.load_squad(squad_name, environment)

        # Validate configuration
        if not loader.validate_config(squad_config):
            console.print(f"[red]Invalid squad configuration[/red]")
            return

        # Build squad request
        builder = SquadBuilder()
        try:
            squad_request = builder.build_from_config(squad_config, environment)
        except ValueError as e:
            console.print(f"[red]Squad build failed: {e}[/red]")
            console.print(f"[yellow]Ensure all referenced assistants are deployed to {environment}[/yellow]")
            return

        # Create squad via VAPI
        service = SquadService()
        squad = await service.create_squad(squad_request)

        # Track deployment state
        squad_state_manager.mark_deployed(squad_name, environment, squad.id)

        console.print(f"[green]Squad created successfully![/green]")
        console.print(f"[cyan]Squad ID:[/cyan] {squad.id}")
        console.print(f"[cyan]Name:[/cyan] {squad.name}")
        console.print(f"[cyan]Members:[/cyan] {len(squad.members)}")
        console.print(f"[cyan]Version:[/cyan] 1")

        # Show member details
        console.print(f"\n[bold]Squad Members:[/bold]")
        for i, member in enumerate(squad.members, 1):
            console.print(f"  {i}. Assistant ID: {member.assistant_id}")
            if member.assistant_destinations:
                console.print(f"     Destinations: {len(member.assistant_destinations)}")

    except VAPIException as e:
        console.print(f"[red]Failed to create squad: {e}[/red]")
        raise


async def update_squad(squad_name, environment="development", dry_run=False, force=False, directory="squads"):
    """Update an existing squad with comprehensive validation and change detection."""
    console.print(f"[cyan]Updating squad:[/cyan] {squad_name}")
    console.print(f"[cyan]Environment:[/cyan] {environment}")

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No changes will be applied[/yellow]")

    try:
        # Create update strategy
        update_strategy = SquadUpdateStrategy(directory)

        # Perform the update
        result = await update_strategy.update_squad(squad_name, environment, dry_run, force)

        # Display results based on status
        if result.status == 'failed':
            console.print(f"[red]Update failed: {result.message}[/red]")
            return

        elif result.status == 'no_changes':
            console.print(f"[yellow]{result.message}[/yellow]")
            console.print("[cyan]Squad is already up to date[/cyan]")

        elif result.status == 'preview':
            console.print(f"[blue]{result.message}[/blue]")
            console.print(f"[cyan]Total changes:[/cyan] {result.total_changes}")

            if result.changes:
                console.print("\n[bold]Changes to be applied:[/bold]")
                for change in result.changes:
                    if change.change_type.value == 'added':
                        console.print(f"  [green]+[/green] {change.field}: {change.description}")
                    elif change.change_type.value == 'removed':
                        console.print(f"  [red]-[/red] {change.field}: {change.description}")
                    elif change.change_type.value == 'modified':
                        console.print(f"  [yellow]~[/yellow] {change.field}: {change.description}")

                console.print(f"\n[cyan]To apply these changes, run without --dry-run[/cyan]")

        elif result.status == 'success':
            console.print(f"[green]{result.message}[/green]")
            console.print(f"[cyan]Squad ID:[/cyan] {result.squad_id}")
            console.print(f"[cyan]Version:[/cyan] {result.version}")

            if result.changes:
                console.print(f"\n[bold]Changes applied:[/bold]")
                for change in result.changes:
                    if change.change_type.value == 'added':
                        console.print(f"  [green]+[/green] {change.description}")
                    elif change.change_type.value == 'removed':
                        console.print(f"  [red]-[/red] {change.description}")
                    elif change.change_type.value == 'modified':
                        console.print(f"  [yellow]~[/yellow] {change.description}")

        console.print("\n[green]Update operation completed[/green]")

    except VAPIException as e:
        console.print(f"[red]Update failed: {e}[/red]")
        raise
    except Exception as e:
        console.print(f"[red]Unexpected error during update: {e}[/red]")
        raise


async def show_squad_status(squad_name=None, directory="squads"):
    """Show deployment status for squads."""
    update_strategy = SquadUpdateStrategy(directory)

    if squad_name:
        # Show status for specific squad
        try:
            status = await update_strategy.get_squad_status(squad_name)

            if "error" in status:
                console.print(f"[red]Error getting status: {status['error']}[/red]")
                return

            console.print(f"\n[cyan]Squad:[/cyan] {squad_name}")

            # Show environment details
            table = Table(title=f"{squad_name} - Deployment Status")
            table.add_column("Environment", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Squad ID", style="blue")
            table.add_column("Version", style="yellow")
            table.add_column("Deployed At", style="dim")

            for env in ['development', 'staging', 'production']:
                env_status = status.get(env, {})
                if env_status.get('deployed', False):
                    status_text = "[green]Deployed[/green]"
                    squad_id = env_status.get('squad_id', 'N/A')
                    squad_id_short = squad_id[:8] + "..." if squad_id and len(squad_id) > 8 else squad_id or "N/A"
                    version = str(env_status.get('version', 0))
                    deployed_at = env_status.get('deployed_at', 'N/A')
                    if deployed_at and deployed_at != 'N/A':
                        deployed_at = deployed_at[:19]  # Truncate timestamp
                else:
                    status_text = "[red]Not Deployed[/red]"
                    squad_id_short = "N/A"
                    version = "0"
                    deployed_at = "N/A"

                table.add_row(env, status_text, squad_id_short, version, deployed_at)

            console.print(table)

        except Exception as e:
            console.print(f"[red]Error getting status: {e}[/red]")

    else:
        # Show status for all squads
        try:
            state_manager = SquadDeploymentStateManager(directory)
            summary = state_manager.get_deployment_summary()

            if not summary:
                console.print("[yellow]No squads found[/yellow]")
                return

            table = Table(title="All Squads - Deployment Summary")
            table.add_column("Squad", style="cyan")
            table.add_column("Dev", style="green")
            table.add_column("Staging", style="yellow")
            table.add_column("Production", style="red")
            table.add_column("Total Deployed", style="blue")

            for squad_name, info in summary.items():
                deployments = info['deployments']

                dev_status = "+" if deployments.get('development', {}).is_deployed() else "-"
                staging_status = "+" if deployments.get('staging', {}).is_deployed() else "-"
                prod_status = "+" if deployments.get('production', {}).is_deployed() else "-"
                total_deployed = str(info['total_deployed'])

                table.add_row(
                    squad_name,
                    dev_status,
                    staging_status,
                    prod_status,
                    total_deployed
                )

            console.print(table)

        except Exception as e:
            console.print(f"[red]Error getting summary: {e}[/red]")


async def delete_squad(squad_name, environment="development", force=False, delete_assistants=False, directory="squads"):
    """Delete a squad from VAPI and optionally delete its assistants too."""
    try:
        # Load squad configuration
        squad_path = Path(directory) / squad_name
        if not squad_path.exists():
            console.print(f"[red]Squad configuration not found: {squad_path}[/red]")
            return False

        # Check deployment state
        state_manager = SquadDeploymentStateManager(directory)
        deployment_info = state_manager.get_deployment_info(squad_name, environment)

        if not deployment_info.is_deployed:
            console.print(f"[yellow]Squad '{squad_name}' is not deployed to {environment}[/yellow]")
            return False

        squad_id = deployment_info.id

        # Get squad member assistants if we need to delete them
        assistant_members = []
        if delete_assistants:
            try:
                # Load squad configuration to get member assistants
                from ..core.squad_config import SquadConfigLoader
                config_loader = SquadConfigLoader(directory)
                squad_config = config_loader.load_squad(squad_name, environment)

                # Get assistant names from squad members
                for member in squad_config.members:
                    assistant_members.append(member['assistant_name'])

            except Exception as e:
                console.print(f"[yellow]Warning: Could not load squad members: {e}[/yellow]")

        # Confirm deletion unless force is used
        if not force:
            from rich.prompt import Confirm

            deletion_message = f"[red]Are you sure you want to delete squad '{squad_name}' (ID: {squad_id}) from {environment}?"
            if delete_assistants and assistant_members:
                deletion_message += f"\n\nThis will also delete {len(assistant_members)} assistant(s): {', '.join(assistant_members)}"
            deletion_message += "[/red]"

            confirmed = Confirm.ask(deletion_message)
            if not confirmed:
                console.print("[yellow]Squad deletion cancelled[/yellow]")
                return False

        console.print(f"[yellow]Deleting squad '{squad_name}' from {environment}...[/yellow]")

        # Delete squad from VAPI
        service = SquadService()
        success = await service.delete_squad(squad_id)

        if success:
            # Remove deployment tracking
            state_manager.mark_undeployed(squad_name, environment)

            console.print(f"[green]+ Squad '{squad_name}' deleted successfully from {environment}[/green]")
            console.print(f"[dim]Squad ID: {squad_id}[/dim]")

            # Delete associated assistants if requested
            if delete_assistants and assistant_members:
                console.print(f"\n[yellow]Deleting {len(assistant_members)} associated assistant(s)...[/yellow]")

                deleted_assistants = []
                failed_assistants = []

                for assistant_name in assistant_members:
                    try:
                        # Get assistant deployment info
                        from ..core.deployment_state import DeploymentStateManager
                        assistant_state_manager = DeploymentStateManager("assistants")
                        assistant_deployment_info = assistant_state_manager.get_deployment_info(assistant_name, environment)

                        if assistant_deployment_info.is_deployed:
                            # Delete assistant from VAPI
                            from ..services import AssistantService
                            assistant_service = AssistantService()
                            assistant_success = await assistant_service.delete_assistant(assistant_deployment_info.id)

                            if assistant_success:
                                # Remove assistant deployment tracking
                                assistant_state_manager.mark_undeployed(assistant_name, environment)
                                deleted_assistants.append(assistant_name)
                                console.print(f"[green]  + Assistant '{assistant_name}' deleted[/green]")
                            else:
                                failed_assistants.append(assistant_name)
                                console.print(f"[red]  - Failed to delete assistant '{assistant_name}'[/red]")
                        else:
                            console.print(f"[yellow]  ~ Assistant '{assistant_name}' was not deployed to {environment}[/yellow]")

                    except Exception as e:
                        failed_assistants.append(assistant_name)
                        console.print(f"[red]  - Error deleting assistant '{assistant_name}': {e}[/red]")

                # Summary of assistant deletion
                if deleted_assistants:
                    console.print(f"\n[green]Successfully deleted {len(deleted_assistants)} assistant(s)[/green]")
                if failed_assistants:
                    console.print(f"[red]Failed to delete {len(failed_assistants)} assistant(s): {', '.join(failed_assistants)}[/red]")

            return True
        else:
            console.print(f"[red]Failed to delete squad '{squad_name}' from {environment}[/red]")
            return False

    except Exception as e:
        console.print(f"[red]Error deleting squad: {e}[/red]")
        return False


async def backup_squad(
    squad_name,
    environment="development",
    backup_type="complete",
    description=None,
    tags=None,
    squads_directory="squads",
    assistants_directory="assistants"
):
    """Create a comprehensive backup of a squad with all related assistants."""
    console.print(f"[cyan]Creating squad backup...[/cyan]")
    console.print(f"[cyan]Squad:[/cyan] {squad_name}")
    console.print(f"[cyan]Environment:[/cyan] {environment}")
    console.print(f"[cyan]Backup type:[/cyan] {backup_type}")

    try:
        # Create squad backup manager
        backup_manager = SquadBackupManager(squads_directory, assistants_directory)

        # Convert backup type string to enum
        backup_type_enum = SquadBackupType(backup_type)

        # Parse tags if provided
        tag_list = tags.split(',') if tags else None

        # Create backup
        manifest = await backup_manager.create_squad_backup(
            squad_name=squad_name,
            environment=environment,
            backup_type=backup_type_enum,
            description=description,
            tags=tag_list
        )

        # Display results
        console.print(f"\n[green]+ Squad backup created successfully![/green]")
        console.print(f"[cyan]Backup ID:[/cyan] {manifest.metadata.backup_id}")
        console.print(f"[cyan]File:[/cyan] backups/{manifest.metadata.backup_id}.json")
        console.print(f"[cyan]Squad:[/cyan] {manifest.squad_backup.squad_name}")
        console.print(f"[cyan]Assistants backed up:[/cyan] {len(manifest.squad_backup.assistant_backups)}")
        console.print(f"[cyan]Total size:[/cyan] {SquadBackupUtils.format_file_size(manifest.metadata.total_size_bytes)}")
        console.print(f"[cyan]Created at:[/cyan] {manifest.metadata.created_at}")

        if manifest.metadata.description:
            console.print(f"[cyan]Description:[/cyan] {manifest.metadata.description}")

        if manifest.metadata.tags:
            console.print(f"[cyan]Tags:[/cyan] {', '.join(manifest.metadata.tags)}")

        # Show squad backup details
        console.print(f"\n[bold]Squad backup details:[/bold]")
        squad_indicators = []
        if manifest.squad_backup.squad_vapi_data:
            squad_indicators.append("[blue]VAPI[/blue]")
        if manifest.squad_backup.squad_local_config:
            squad_indicators.append("[green]Config[/green]")
        if manifest.squad_backup.squad_file_contents:
            squad_indicators.append("[yellow]Files[/yellow]")

        console.print(f"  Squad: {squad_name} ({', '.join(squad_indicators)})")

        # Show assistant backup details
        if manifest.squad_backup.assistant_backups:
            console.print(f"\n[bold]Related assistants backed up:[/bold]")
            for assistant_backup in manifest.squad_backup.assistant_backups:
                status_indicators = []
                if assistant_backup.vapi_data:
                    status_indicators.append("[blue]VAPI[/blue]")
                if assistant_backup.local_config:
                    status_indicators.append("[green]Config[/green]")
                if assistant_backup.file_contents:
                    status_indicators.append("[yellow]Files[/yellow]")

                console.print(f"  • {assistant_backup.assistant_name} ({', '.join(status_indicators)})")

    except Exception as e:
        console.print(f"[red]Squad backup failed: {e}[/red]")
        raise


async def restore_squad_backup(
    backup_path,
    target_environment="development",
    overwrite=False,
    restore_config=True,
    restore_vapi=True,
    restore_assistants=True,
    squad_name_override=None,
    assistant_prefix="",
    dry_run=False,
    squads_directory="squads",
    assistants_directory="assistants"
):
    """Restore a complete squad from backup with all related assistants."""
    console.print(f"[cyan]Restoring squad from backup:[/cyan] {backup_path}")
    console.print(f"[cyan]Target environment:[/cyan] {target_environment}")

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No changes will be applied[/yellow]")

    # Display restore options
    restore_opts = []
    if restore_config:
        restore_opts.append("Local Config")
    if restore_vapi:
        restore_opts.append("VAPI Data")
    if restore_assistants:
        restore_opts.append("Related Assistants")
    console.print(f"[cyan]Restore scope:[/cyan] {', '.join(restore_opts)}")

    if squad_name_override:
        console.print(f"[cyan]Squad name override:[/cyan] {squad_name_override}")

    if assistant_prefix:
        console.print(f"[cyan]Assistant prefix:[/cyan] {assistant_prefix}")

    if overwrite:
        console.print("[yellow]Overwrite mode enabled - existing components will be replaced[/yellow]")

    try:
        # Validate backup file exists
        if not Path(backup_path).exists():
            console.print(f"[red]Squad backup file not found: {backup_path}[/red]")
            return

        # Validate backup integrity
        console.print("[cyan]Validating squad backup file...[/cyan]")
        is_valid, errors = SquadBackupUtils.validate_squad_backup_file(backup_path)

        if not is_valid:
            console.print("[red]Squad backup validation failed:[/red]")
            for error in errors:
                console.print(f"  • {error}")
            return

        console.print("[green]+ Squad backup file validated[/green]")

        # Create squad backup manager
        backup_manager = SquadBackupManager(squads_directory, assistants_directory)

        # Create restore options
        options = SquadRestoreOptions(
            target_environment=target_environment,
            overwrite_existing=overwrite,
            restore_local_config=restore_config,
            restore_vapi_data=restore_vapi,
            restore_deployment_state=True,
            create_missing_directories=True,
            backup_before_restore=not dry_run,  # Skip safety backup in dry run
            dry_run=dry_run,
            restore_assistants=restore_assistants,
            create_missing_assistants=True,
            assistant_name_prefix=assistant_prefix,
            squad_name_override=squad_name_override,
            skip_assistant_deployment=False
        )

        # Perform restore
        result = await backup_manager.restore_squad_backup(backup_path, options)

        # Display results
        if result.success:
            console.print(f"\n[green]+ Squad restore completed successfully![/green]")
        else:
            console.print(f"\n[yellow]Squad restore completed with issues[/yellow]")

        # Show squad restoration status
        if result.restored_squad:
            console.print(f"[cyan]Squad restored:[/cyan] {result.restored_squad}")
        elif result.skipped_squad:
            console.print(f"[yellow]Squad skipped:[/yellow] Already exists")
        elif result.failed_squad:
            console.print(f"[red]Squad restoration failed[/red]")

        # Show assistant statistics
        console.print(f"[cyan]Assistants restored:[/cyan] {len(result.restored_assistants)}")
        console.print(f"[cyan]Assistants skipped:[/cyan] {len(result.skipped_assistants)}")
        console.print(f"[cyan]Assistants failed:[/cyan] {len(result.failed_assistants)}")

        # Show safety backup info
        if result.backup_created:
            console.print(f"[cyan]Safety backup:[/cyan] {result.backup_created}")

        # List restored assistants
        if result.restored_assistants:
            console.print(f"\n[bold]Restored assistants:[/bold]")
            for assistant_name in result.restored_assistants:
                details = result.assistant_restore_details.get(assistant_name, {})
                detail_parts = []
                if details.get('restored_config'):
                    detail_parts.append("Config")
                if details.get('restored_vapi'):
                    detail_parts.append("VAPI")
                file_count = details.get('file_count', 0)
                if file_count > 0:
                    detail_parts.append(f"{file_count} files")

                detail_str = f" ({', '.join(detail_parts)})" if detail_parts else ""
                console.print(f"  [green]+[/green] {assistant_name}{detail_str}")

        # List skipped assistants
        if result.skipped_assistants:
            console.print(f"\n[bold]Skipped assistants:[/bold]")
            for assistant_name in result.skipped_assistants:
                console.print(f"  [yellow]-[/yellow] {assistant_name}")

        # List failed assistants
        if result.failed_assistants:
            console.print(f"\n[bold]Failed assistants:[/bold]")
            for assistant_name in result.failed_assistants:
                console.print(f"  [red]x[/red] {assistant_name}")

        # Show warnings and errors
        if result.warnings:
            console.print(f"\n[bold yellow]Warnings:[/bold yellow]")
            for warning in result.warnings:
                console.print(f"  [yellow]![/yellow] {warning}")

        if result.errors:
            console.print(f"\n[bold red]Errors:[/bold red]")
            for error in result.errors:
                console.print(f"  [red]x[/red] {error}")

    except Exception as e:
        console.print(f"[red]Squad restore failed: {e}[/red]")
        raise


def list_squad_backups(squads_directory="squads", assistants_directory="assistants"):
    """List all available squad backups."""
    try:
        backup_manager = SquadBackupManager(squads_directory, assistants_directory)
        backups = backup_manager.list_squad_backups()

        if not backups:
            console.print("[yellow]No squad backups found[/yellow]")
            console.print("[cyan]Create a squad backup with:[/cyan] vapi-manager squad backup <squad_name>")
            return

        # Display backups in a table
        table = Table(title="Available Squad Backups")
        table.add_column("Backup ID", style="cyan")
        table.add_column("Created", style="dim")
        table.add_column("Squad", style="magenta")
        table.add_column("Environment", style="green")
        table.add_column("Type", style="blue")
        table.add_column("Assistants", style="yellow")
        table.add_column("Size", style="magenta")
        table.add_column("Description", style="white")

        for backup in backups:
            # Format creation date
            created_date = backup.created_at.strftime("%Y-%m-%d %H:%M")

            # Get file size
            backup_file = backup_manager.backups_dir / f"{backup.backup_id}.json"
            if backup_file.exists():
                size = SquadBackupUtils.format_file_size(backup_file.stat().st_size)
            else:
                size = "N/A"

            # Get squad name
            try:
                manifest = backup_manager.get_squad_backup_details(backup.backup_id)
                squad_name = manifest.squad_backup.squad_name if manifest else "Unknown"
            except Exception:
                squad_name = "Unknown"

            # Truncate description if too long
            description = backup.description or ""
            if len(description) > 30:
                description = description[:27] + "..."

            table.add_row(
                backup.backup_id,
                created_date,
                squad_name,
                backup.environment,
                backup.squad_backup_type.value,
                str(backup.assistant_count),
                size,
                description
            )

        console.print(table)

        # Display backup health summary
        report = SquadBackupUtils.generate_squad_backup_report(backup_manager)
        console.print(f"\n[cyan]Total squad backups:[/cyan] {report['total_backups']}")
        console.print(f"[cyan]Total size:[/cyan] {report['total_size_formatted']}")
        console.print(f"[cyan]Health status:[/cyan] {report['backup_health']}")
        console.print(f"[cyan]Unique squads:[/cyan] {report['unique_squads']}")

    except Exception as e:
        console.print(f"[red]Error listing squad backups: {e}[/red]")


def show_squad_backup_details(backup_id, squads_directory="squads", assistants_directory="assistants"):
    """Show detailed information about a specific squad backup."""
    try:
        backup_manager = SquadBackupManager(squads_directory, assistants_directory)
        manifest = backup_manager.get_squad_backup_details(backup_id)

        if not manifest:
            console.print(f"[red]Squad backup not found: {backup_id}[/red]")
            return

        metadata = manifest.metadata
        squad_backup = manifest.squad_backup

        # Display backup metadata
        console.print(f"\n[cyan]Backup ID:[/cyan] {metadata.backup_id}")
        console.print(f"[cyan]Created:[/cyan] {metadata.created_at}")
        console.print(f"[cyan]Created by:[/cyan] {metadata.created_by}")
        console.print(f"[cyan]Environment:[/cyan] {metadata.environment}")
        console.print(f"[cyan]Type:[/cyan] {metadata.squad_backup_type.value}")
        console.print(f"[cyan]Status:[/cyan] {metadata.status.value}")

        if metadata.description:
            console.print(f"[cyan]Description:[/cyan] {metadata.description}")

        if metadata.tags:
            console.print(f"[cyan]Tags:[/cyan] {', '.join(metadata.tags)}")

        console.print(f"[cyan]Squad:[/cyan] {squad_backup.squad_name}")
        console.print(f"[cyan]Assistant count:[/cyan] {len(squad_backup.assistant_backups)}")
        console.print(f"[cyan]Total size:[/cyan] {SquadBackupUtils.format_file_size(metadata.total_size_bytes)}")

        # Validate backup integrity
        if manifest.validate_integrity():
            console.print("[green]+ Squad backup integrity verified[/green]")
        else:
            console.print("[red]x Squad backup integrity check failed[/red]")

        # Display squad details
        console.print(f"\n[bold]Squad Details:[/bold]")
        squad_table = Table()
        squad_table.add_column("Component", style="cyan")
        squad_table.add_column("VAPI Data", style="blue")
        squad_table.add_column("Local Config", style="green")
        squad_table.add_column("Files", style="yellow")
        squad_table.add_column("Deployment State", style="magenta")

        vapi_status = "+" if squad_backup.squad_vapi_data else "-"
        config_status = "+" if squad_backup.squad_local_config else "-"
        files_count = len(squad_backup.squad_file_contents) if squad_backup.squad_file_contents else 0
        files_status = str(files_count) if files_count > 0 else "-"
        deploy_status = "+" if squad_backup.squad_deployment_state else "-"

        squad_table.add_row(
            squad_backup.squad_name,
            vapi_status,
            config_status,
            files_status,
            deploy_status
        )

        console.print(squad_table)

        # Display assistant details
        if squad_backup.assistant_backups:
            console.print(f"\n[bold]Assistant Details:[/bold]")
            assistant_table = Table()
            assistant_table.add_column("Assistant", style="cyan")
            assistant_table.add_column("VAPI Data", style="blue")
            assistant_table.add_column("Local Config", style="green")
            assistant_table.add_column("Files", style="yellow")
            assistant_table.add_column("Deployment State", style="magenta")

            for assistant in squad_backup.assistant_backups:
                vapi_status = "+" if assistant.vapi_data else "-"
                config_status = "+" if assistant.local_config else "-"
                files_count = len(assistant.file_contents) if assistant.file_contents else 0
                files_status = str(files_count) if files_count > 0 else "-"
                deploy_status = "+" if assistant.deployment_state else "-"

                assistant_table.add_row(
                    assistant.assistant_name,
                    vapi_status,
                    config_status,
                    files_status,
                    deploy_status
                )

            console.print(assistant_table)

        # Show dependencies
        if squad_backup.assistant_dependencies:
            console.print(f"\n[bold]Assistant Dependencies:[/bold]")
            for assistant_name, assistant_id in squad_backup.assistant_dependencies.items():
                console.print(f"  + {assistant_name} -> {assistant_id}")

    except Exception as e:
        console.print(f"[red]Error showing squad backup details: {e}[/red]")


def delete_squad_backup(backup_id, squads_directory="squads", assistants_directory="assistants"):
    """Delete a squad backup."""
    try:
        backup_manager = SquadBackupManager(squads_directory, assistants_directory)

        if backup_manager.delete_squad_backup(backup_id):
            console.print(f"[green]+ Squad backup deleted: {backup_id}[/green]")
        else:
            console.print(f"[red]Squad backup not found: {backup_id}[/red]")

    except Exception as e:
        console.print(f"[red]Error deleting squad backup: {e}[/red]")


async def backup_assistants(
    assistant_names=None,
    environment="development",
    backup_type="full",
    description=None,
    tags=None,
    directory="assistants"
):
    """Create a backup of assistants."""
    console.print(f"[cyan]Creating backup...[/cyan]")
    console.print(f"[cyan]Environment:[/cyan] {environment}")
    console.print(f"[cyan]Backup type:[/cyan] {backup_type}")

    if assistant_names:
        console.print(f"[cyan]Assistants:[/cyan] {', '.join(assistant_names)}")
    else:
        console.print("[cyan]Scope:[/cyan] All assistants")

    try:
        # Create backup manager
        backup_manager = BackupManager(directory)

        # Convert backup type string to enum
        backup_type_enum = BackupType(backup_type)

        # Parse tags if provided
        tag_list = tags.split(',') if tags else None

        # Create backup
        manifest = await backup_manager.create_backup(
            assistant_names=assistant_names,
            environment=environment,
            backup_type=backup_type_enum,
            description=description,
            tags=tag_list
        )

        # Display results
        console.print(f"\n[green]+ Backup created successfully![/green]")
        console.print(f"[cyan]Backup ID:[/cyan] {manifest.metadata.backup_id}")
        console.print(f"[cyan]File:[/cyan] backups/{manifest.metadata.backup_id}.json")
        console.print(f"[cyan]Assistants backed up:[/cyan] {manifest.metadata.assistant_count}")
        console.print(f"[cyan]Total size:[/cyan] {BackupUtils.format_file_size(manifest.metadata.total_size_bytes)}")
        console.print(f"[cyan]Created at:[/cyan] {manifest.metadata.created_at}")

        if manifest.metadata.description:
            console.print(f"[cyan]Description:[/cyan] {manifest.metadata.description}")

        if manifest.metadata.tags:
            console.print(f"[cyan]Tags:[/cyan] {', '.join(manifest.metadata.tags)}")

        # List backed up assistants
        console.print(f"\n[bold]Backed up assistants:[/bold]")
        for assistant_backup in manifest.assistants:
            status_indicators = []
            if assistant_backup.vapi_data:
                status_indicators.append("[blue]VAPI[/blue]")
            if assistant_backup.local_config:
                status_indicators.append("[green]Config[/green]")
            if assistant_backup.file_contents:
                status_indicators.append("[yellow]Files[/yellow]")

            console.print(f"  • {assistant_backup.assistant_name} ({', '.join(status_indicators)})")

    except Exception as e:
        console.print(f"[red]Backup failed: {e}[/red]")
        raise


async def restore_backup(
    backup_path,
    target_environment="development",
    overwrite=False,
    restore_config=True,
    restore_vapi=True,
    dry_run=False,
    directory="assistants"
):
    """Restore assistants from a backup."""
    console.print(f"[cyan]Restoring from backup:[/cyan] {backup_path}")
    console.print(f"[cyan]Target environment:[/cyan] {target_environment}")

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No changes will be applied[/yellow]")

    # Display restore options
    restore_opts = []
    if restore_config:
        restore_opts.append("Local Config")
    if restore_vapi:
        restore_opts.append("VAPI Data")
    console.print(f"[cyan]Restore scope:[/cyan] {', '.join(restore_opts)}")

    if overwrite:
        console.print("[yellow]Overwrite mode enabled - existing assistants will be replaced[/yellow]")

    try:
        # Validate backup file exists
        if not Path(backup_path).exists():
            console.print(f"[red]Backup file not found: {backup_path}[/red]")
            return

        # Validate backup integrity
        console.print("[cyan]Validating backup file...[/cyan]")
        is_valid, errors = BackupUtils.validate_backup_file(backup_path)

        if not is_valid:
            console.print("[red]Backup validation failed:[/red]")
            for error in errors:
                console.print(f"  • {error}")
            return

        console.print("[green]+ Backup file validated[/green]")

        # Create backup manager
        backup_manager = BackupManager(directory)

        # Create restore options
        options = RestoreOptions(
            target_environment=target_environment,
            overwrite_existing=overwrite,
            restore_local_config=restore_config,
            restore_vapi_data=restore_vapi,
            restore_deployment_state=True,
            create_missing_directories=True,
            backup_before_restore=not dry_run,  # Skip safety backup in dry run
            dry_run=dry_run
        )

        # Perform restore
        result = await backup_manager.restore_backup(backup_path, options)

        # Display results
        if result.success:
            console.print(f"\n[green]+ Restore completed successfully![/green]")
        else:
            console.print(f"\n[yellow]Restore completed with issues[/yellow]")

        # Show statistics
        console.print(f"[cyan]Restored:[/cyan] {len(result.restored_assistants)}")
        console.print(f"[cyan]Skipped:[/cyan] {len(result.skipped_assistants)}")
        console.print(f"[cyan]Failed:[/cyan] {len(result.failed_assistants)}")

        # Show safety backup info
        if result.backup_created:
            console.print(f"[cyan]Safety backup:[/cyan] {result.backup_created}")

        # List restored assistants
        if result.restored_assistants:
            console.print(f"\n[bold]Restored assistants:[/bold]")
            for assistant_name in result.restored_assistants:
                console.print(f"  [green]+[/green] {assistant_name}")

        # List skipped assistants
        if result.skipped_assistants:
            console.print(f"\n[bold]Skipped assistants:[/bold]")
            for assistant_name in result.skipped_assistants:
                console.print(f"  [yellow]-[/yellow] {assistant_name}")

        # List failed assistants
        if result.failed_assistants:
            console.print(f"\n[bold]Failed assistants:[/bold]")
            for assistant_name in result.failed_assistants:
                console.print(f"  [red]x[/red] {assistant_name}")

        # Show warnings and errors
        if result.warnings:
            console.print(f"\n[bold yellow]Warnings:[/bold yellow]")
            for warning in result.warnings:
                console.print(f"  [yellow]![/yellow] {warning}")

        if result.errors:
            console.print(f"\n[bold red]Errors:[/bold red]")
            for error in result.errors:
                console.print(f"  [red]x[/red] {error}")

    except Exception as e:
        console.print(f"[red]Restore failed: {e}[/red]")
        raise


def list_backups(directory="assistants"):
    """List all available backups."""
    try:
        backup_manager = BackupManager(directory)
        backups = backup_manager.list_backups()

        if not backups:
            console.print("[yellow]No backups found[/yellow]")
            console.print("[cyan]Create a backup with:[/cyan] vapi-manager assistant backup")
            return

        # Display backups in a table
        table = Table(title="Available Backups")
        table.add_column("Backup ID", style="cyan")
        table.add_column("Created", style="dim")
        table.add_column("Environment", style="green")
        table.add_column("Type", style="blue")
        table.add_column("Assistants", style="yellow")
        table.add_column("Size", style="magenta")
        table.add_column("Description", style="white")

        for backup in backups:
            # Format creation date
            created_date = backup.created_at.strftime("%Y-%m-%d %H:%M")

            # Get file size
            backup_file = backup_manager.backups_dir / f"{backup.backup_id}.json"
            if backup_file.exists():
                size = BackupUtils.format_file_size(backup_file.stat().st_size)
            else:
                size = "N/A"

            # Truncate description if too long
            description = backup.description or ""
            if len(description) > 40:
                description = description[:37] + "..."

            table.add_row(
                backup.backup_id,
                created_date,
                backup.environment,
                backup.backup_type.value,
                str(backup.assistant_count),
                size,
                description
            )

        console.print(table)

        # Display backup health summary
        report = BackupUtils.generate_backup_report(backup_manager)
        console.print(f"\n[cyan]Total backups:[/cyan] {report['total_backups']}")
        console.print(f"[cyan]Total size:[/cyan] {report['total_size_formatted']}")
        console.print(f"[cyan]Health status:[/cyan] {report['backup_health']}")

    except Exception as e:
        console.print(f"[red]Error listing backups: {e}[/red]")


def show_backup_details(backup_id, directory="assistants"):
    """Show detailed information about a specific backup."""
    try:
        backup_manager = BackupManager(directory)
        manifest = backup_manager.get_backup_details(backup_id)

        if not manifest:
            console.print(f"[red]Backup not found: {backup_id}[/red]")
            return

        metadata = manifest.metadata

        # Display backup metadata
        console.print(f"\n[cyan]Backup ID:[/cyan] {metadata.backup_id}")
        console.print(f"[cyan]Created:[/cyan] {metadata.created_at}")
        console.print(f"[cyan]Created by:[/cyan] {metadata.created_by}")
        console.print(f"[cyan]Environment:[/cyan] {metadata.environment}")
        console.print(f"[cyan]Type:[/cyan] {metadata.backup_type.value}")
        console.print(f"[cyan]Scope:[/cyan] {metadata.backup_scope.value}")
        console.print(f"[cyan]Status:[/cyan] {metadata.status.value}")

        if metadata.description:
            console.print(f"[cyan]Description:[/cyan] {metadata.description}")

        if metadata.tags:
            console.print(f"[cyan]Tags:[/cyan] {', '.join(metadata.tags)}")

        console.print(f"[cyan]Assistant count:[/cyan] {metadata.assistant_count}")
        console.print(f"[cyan]Total size:[/cyan] {BackupUtils.format_file_size(metadata.total_size_bytes)}")

        # Validate backup integrity
        if manifest.validate_integrity():
            console.print("[green]+ Backup integrity verified[/green]")
        else:
            console.print("[red]x Backup integrity check failed[/red]")

        # Display assistant details
        console.print(f"\n[bold]Assistant Details:[/bold]")
        table = Table()
        table.add_column("Assistant", style="cyan")
        table.add_column("VAPI Data", style="blue")
        table.add_column("Local Config", style="green")
        table.add_column("Files", style="yellow")
        table.add_column("Deployment State", style="magenta")

        for assistant in manifest.assistants:
            vapi_status = "+" if assistant.vapi_data else "-"
            config_status = "+" if assistant.local_config else "-"
            files_count = len(assistant.file_contents) if assistant.file_contents else 0
            files_status = str(files_count) if files_count > 0 else "-"
            deploy_status = "+" if assistant.deployment_state else "-"

            table.add_row(
                assistant.assistant_name,
                vapi_status,
                config_status,
                files_status,
                deploy_status
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error showing backup details: {e}[/red]")


def delete_backup(backup_id, directory="assistants"):
    """Delete a backup."""
    try:
        backup_manager = BackupManager(directory)

        if backup_manager.delete_backup(backup_id):
            console.print(f"[green]+ Backup deleted: {backup_id}[/green]")
        else:
            console.print(f"[red]Backup not found: {backup_id}[/red]")

    except Exception as e:
        console.print(f"[red]Error deleting backup: {e}[/red]")


async def deploy_assistant(assistant_name, environment="default", directory="assistants"):
    """Deploy a file-based assistant configuration to VAPI."""
    loader = AssistantConfigLoader(directory)

    try:
        # Load the assistant configuration
        config = loader.load_assistant(assistant_name, environment)
        console.print(f"[cyan]Loading assistant:[/cyan] {assistant_name}")
        console.print(f"[cyan]Environment:[/cyan] {environment}")

        # Validate configuration
        if not loader.validate_config(config):
            console.print("[red]Invalid configuration: Missing required fields[/red]")
            return

        # Build the assistant request
        request = AssistantBuilder.build_from_config(config)
        console.print("[green]Configuration validated and built successfully[/green]")

        # Deploy to VAPI
        service = AssistantService()
        assistant = await service.create_assistant(request)

        console.print(f"[green]+ Assistant deployed successfully![/green]")
        console.print(f"[cyan]Assistant ID:[/cyan] {assistant.id}")
        console.print(f"[cyan]Name:[/cyan] {assistant.name}")

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Deployment failed: {e}[/red]")


async def validate_assistant(assistant_name, directory="assistants"):
    """Validate a file-based assistant configuration."""
    loader = AssistantConfigLoader(directory)

    try:
        config = loader.load_assistant(assistant_name)

        console.print(f"\n[cyan]Validating assistant:[/cyan] {assistant_name}\n")

        # Check required files
        checks = []

        # Configuration
        if config.config:
            checks.append(("[green]+[/green]", "assistant.yaml found"))
            if 'name' in config.config:
                checks.append(("[green]+[/green]", f"Name: {config.config['name']}"))
            else:
                checks.append(("[red]x[/red]", "Name: missing"))
        else:
            checks.append(("[red]x[/red]", "assistant.yaml not found"))

        # System prompt
        if config.system_prompt:
            prompt_length = len(config.system_prompt)
            checks.append(("[green]+[/green]", f"System prompt: {prompt_length} characters"))
        else:
            checks.append(("[yellow]![/yellow]", "System prompt: not found (optional)"))

        # First message
        if config.first_message:
            checks.append(("[green]+[/green]", f"First message: configured"))
        else:
            checks.append(("[yellow]![/yellow]", "First message: not found (optional)"))

        # Schemas
        if config.schemas:
            checks.append(("[green]+[/green]", f"Schemas: {len(config.schemas)} found"))
        else:
            checks.append(("[yellow]![/yellow]", "Schemas: none found (optional)"))

        # Tools
        if config.tools:
            checks.append(("[green]+[/green]", f"Tools: {len(config.tools)} configuration(s)"))
        else:
            checks.append(("[yellow]![/yellow]", "Tools: none found (optional)"))

        # Display results
        for status, message in checks:
            console.print(f"  {status} {message}")

        # Overall validation
        if loader.validate_config(config):
            console.print(f"\n[green]+ Configuration is valid and ready to deploy[/green]")
        else:
            console.print(f"\n[red]x Configuration is missing required fields[/red]")

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Validation failed: {e}[/red]")


def init_assistant(name, template="vicky_dental_clinic", force=False):
    """Initialize a new assistant from a template."""
    manager = TemplateManager()

    # Show available templates if none specified
    if template == "list":
        templates = manager.list_templates()
        if not templates:
            console.print("[yellow]No templates found in templates/ directory[/yellow]")
            return

        console.print("[cyan]Available templates:[/cyan]")
        for tmpl in templates:
            console.print(f"  • {tmpl}")
        return

    # Initialize the assistant
    success = manager.init_assistant(
        assistant_name=name,
        template_name=template,
        force=force
    )

    if not success:
        sys.exit(1)


def list_templates():
    """List all available templates."""
    manager = TemplateManager()
    templates = manager.list_templates()

    if not templates:
        console.print("[yellow]No templates found in templates/ directory[/yellow]")
        console.print("[cyan]You can create custom templates in the templates/ directory[/cyan]")
        return

    console.print("[cyan]Available Templates:[/cyan]\n")

    for template in templates:
        try:
            info = manager.get_template_info(template)
            console.print(f"[magenta]{template}[/magenta]")

            # Show key files
            has_config = info["files"].get("assistant.yaml", False)
            has_system = info["files"].get("prompts/system.md", False)
            has_first_msg = info["files"].get("prompts/first_message.md", False)

            if has_config:
                console.print("  [green]+[/green] Configuration")
            if has_system:
                console.print("  [green]+[/green] System prompt")
            if has_first_msg:
                console.print("  [green]+[/green] First message")

            # Show directories
            if info["directories"]:
                dirs_str = ", ".join(info["directories"])
                console.print(f"  [blue]Includes:[/blue] {dirs_str}")

            console.print()

        except Exception as e:
            console.print(f"  [red]Error reading template: {e}[/red]\n")


def show_template_info(template_name):
    """Show detailed information about a template."""
    manager = TemplateManager()
    manager.show_template_info(template_name)


async def create_assistant(assistant_name, environment="production", force=False, directory="assistants"):
    """Create a new assistant in VAPI and track its ID."""
    state_manager = DeploymentStateManager(directory)
    loader = AssistantConfigLoader(directory)

    try:
        # Validate assistant exists
        if not state_manager.validate_assistant_exists(assistant_name):
            console.print(f"[red]Assistant '{assistant_name}' not found[/red]")
            console.print(f"[cyan]Use:[/cyan] poetry run vapi-manager file init {assistant_name}")
            return

        # Check if already deployed
        if state_manager.is_deployed(assistant_name, environment) and not force:
            deployment_info = state_manager.get_deployment_info(assistant_name, environment)
            console.print(f"[yellow]Assistant '{assistant_name}' already deployed to {environment}[/yellow]")
            console.print(f"[cyan]VAPI ID:[/cyan] {deployment_info.id}")
            console.print(f"[cyan]Deployed at:[/cyan] {deployment_info.deployed_at}")
            console.print(f"[cyan]Version:[/cyan] {deployment_info.version}")
            console.print("\n[cyan]Options:[/cyan]")
            console.print(f"  • Use 'update' command to modify existing assistant")
            console.print(f"  • Use --force to recreate assistant")
            console.print(f"  • Use 'status' to see all deployments")
            return

        # Load and validate configuration
        config = loader.load_assistant(assistant_name, environment)
        console.print(f"[cyan]Creating assistant:[/cyan] {assistant_name}")
        console.print(f"[cyan]Environment:[/cyan] {environment}")

        if not loader.validate_config(config):
            console.print("[red]Invalid configuration: Missing required fields[/red]")
            return

        # Build the assistant request
        request = AssistantBuilder.build_from_config(config)
        console.print("[green]Configuration validated successfully[/green]")

        # If force flag and already deployed, we should delete the old one first
        if force and state_manager.is_deployed(assistant_name, environment):
            old_deployment = state_manager.get_deployment_info(assistant_name, environment)
            console.print(f"[yellow]Force flag set - will recreate assistant[/yellow]")
            console.print(f"[yellow]Old VAPI ID: {old_deployment.id}[/yellow]")

            # Try to delete old assistant
            try:
                service = AssistantService()
                await service.delete_assistant(old_deployment.id)
                console.print("[green]Old assistant deleted successfully[/green]")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not delete old assistant: {e}[/yellow]")
                console.print("[yellow]Proceeding with creation anyway[/yellow]")

        # Create new assistant
        service = AssistantService()
        assistant = await service.create_assistant(request)

        # Track the deployment
        state_manager.mark_deployed(assistant_name, environment, assistant.id)

        console.print(f"[green]+ Assistant created successfully![/green]")
        console.print(f"[cyan]Assistant ID:[/cyan] {assistant.id}")
        console.print(f"[cyan]Name:[/cyan] {assistant.name}")
        console.print(f"[cyan]Environment:[/cyan] {environment}")

        # Show deployment status
        deployment_info = state_manager.get_deployment_info(assistant_name, environment)
        console.print(f"[cyan]Version:[/cyan] {deployment_info.version}")
        console.print(f"[cyan]Deployed at:[/cyan] {deployment_info.deployed_at}")

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Creation failed: {e}[/red]")


def show_assistant_status(assistant_name=None, directory="assistants"):
    """Show deployment status for assistants."""
    state_manager = DeploymentStateManager(directory)

    if assistant_name:
        # Show status for specific assistant
        try:
            if not state_manager.validate_assistant_exists(assistant_name):
                console.print(f"[red]Assistant '{assistant_name}' not found[/red]")
                return

            deployments = state_manager.get_all_deployments(assistant_name)
            deployed_envs = state_manager.get_deployed_environments(assistant_name)

            console.print(f"\n[cyan]Assistant:[/cyan] {assistant_name}")
            console.print(f"[cyan]Deployed environments:[/cyan] {len(deployed_envs)}")

            # Show environment details
            table = Table(title=f"{assistant_name} - Deployment Status")
            table.add_column("Environment", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("VAPI ID", style="blue")
            table.add_column("Version", style="yellow")
            table.add_column("Deployed At", style="dim")

            for env in ['development', 'staging', 'production']:
                deployment = deployments.get(env)
                if deployment and deployment.is_deployed():
                    status = "[green]Deployed[/green]"
                    vapi_id = deployment.id[:8] + "..." if deployment.id else "N/A"
                    version = str(deployment.version)
                    deployed_at = deployment.deployed_at[:19] if deployment.deployed_at else "N/A"
                else:
                    status = "[red]Not Deployed[/red]"
                    vapi_id = "N/A"
                    version = "0"
                    deployed_at = "N/A"

                table.add_row(env, status, vapi_id, version, deployed_at)

            console.print(table)

        except Exception as e:
            console.print(f"[red]Error getting status: {e}[/red]")

    else:
        # Show status for all assistants
        try:
            summary = state_manager.get_deployment_summary()

            if not summary:
                console.print("[yellow]No assistants found[/yellow]")
                return

            table = Table(title="All Assistants - Deployment Summary")
            table.add_column("Assistant", style="cyan")
            table.add_column("Dev", style="green")
            table.add_column("Staging", style="yellow")
            table.add_column("Production", style="red")
            table.add_column("Total Deployed", style="blue")

            for assistant_name, info in summary.items():
                deployed_envs = info['deployed_environments']

                dev_status = "+" if 'development' in deployed_envs else "-"
                staging_status = "+" if 'staging' in deployed_envs else "-"
                prod_status = "+" if 'production' in deployed_envs else "-"
                total_deployed = str(info['total_deployments'])

                table.add_row(
                    assistant_name,
                    dev_status,
                    staging_status,
                    prod_status,
                    total_deployed
                )

            console.print(table)

        except Exception as e:
            console.print(f"[red]Error getting summary: {e}[/red]")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="VAPI Assistant and Squad Management Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Assistant commands (with shorter aliases)
    assistant_parser = subparsers.add_parser("assistant", aliases=["ast"], help="Manage assistants")
    assistant_subparsers = assistant_parser.add_subparsers(dest="assistant_command")

    assistant_list_parser = assistant_subparsers.add_parser("list", help="List assistants")
    assistant_list_parser.add_argument("--limit", type=int, help="Limit number of results")

    assistant_get_parser = assistant_subparsers.add_parser("get", help="Get assistant details")
    assistant_get_parser.add_argument("id", help="Assistant ID")

    assistant_validate_parser = assistant_subparsers.add_parser("validate", help="Validate assistant configuration")
    assistant_validate_parser.add_argument("name", help="Assistant name (directory name)")
    assistant_validate_parser.add_argument("--dir", default="assistants", help="Directory containing assistants")

    assistant_init_parser = assistant_subparsers.add_parser("init", help="Initialize new assistant from template")
    assistant_init_parser.add_argument("name", help="Assistant name (directory name)")
    assistant_init_parser.add_argument("--template", default="vicky_dental_clinic", help="Template to use")
    assistant_init_parser.add_argument("--force", action="store_true", help="Overwrite if assistant exists")

    assistant_delete_parser = assistant_subparsers.add_parser("delete", help="Delete an assistant from VAPI")
    assistant_delete_parser.add_argument("name", help="Assistant name to delete")
    assistant_delete_parser.add_argument("--env", default="development", choices=["development", "staging", "production"], help="Environment to delete from")
    assistant_delete_parser.add_argument("--force", action="store_true", help="Force deletion without confirmation")
    assistant_delete_parser.add_argument("--dir", default="assistants", help="Directory containing assistants")

    assistant_update_parser = assistant_subparsers.add_parser("update", help="Update an existing assistant with change detection")
    assistant_update_parser.add_argument("name", help="Assistant name (directory name)")
    assistant_update_parser.add_argument("--env", default="development", choices=["development", "staging", "production"], help="Environment to update")
    assistant_update_parser.add_argument("--scope", default="full", choices=["configuration", "prompts", "tools", "analysis", "full"], help="Update scope")
    assistant_update_parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them")
    assistant_update_parser.add_argument("--no-backup", action="store_true", help="Skip backup creation")
    assistant_update_parser.add_argument("--force", action="store_true", help="Force update even if no changes detected")
    assistant_update_parser.add_argument("--dir", default="assistants", help="Directory containing assistants")

    # Add direct backup/restore commands at assistant level
    assistant_backup_parser = assistant_subparsers.add_parser("backup", help="Create a backup of assistants")
    assistant_backup_parser.add_argument("assistants", nargs="*", help="Assistant names to backup (leave empty for all)")
    assistant_backup_parser.add_argument("--env", default="development", choices=["development", "staging", "production"], help="Environment to backup from")
    assistant_backup_parser.add_argument("--type", default="full", choices=["full", "vapi_only", "config_only"], help="Backup type")
    assistant_backup_parser.add_argument("--description", help="Backup description")
    assistant_backup_parser.add_argument("--tags", help="Comma-separated tags for the backup")
    assistant_backup_parser.add_argument("--dir", default="assistants", help="Directory containing assistants")

    assistant_restore_parser = assistant_subparsers.add_parser("restore", help="Restore assistants from a backup")
    assistant_restore_parser.add_argument("backup_path", help="Path to backup file")
    assistant_restore_parser.add_argument("--env", default="development", choices=["development", "staging", "production"], help="Target environment for restore")
    assistant_restore_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing assistants")
    assistant_restore_parser.add_argument("--config-only", action="store_true", help="Restore only local configuration")
    assistant_restore_parser.add_argument("--vapi-only", action="store_true", help="Restore only VAPI data")
    assistant_restore_parser.add_argument("--dry-run", action="store_true", help="Preview restore without applying changes")
    assistant_restore_parser.add_argument("--dir", default="assistants", help="Directory for assistants")

    # Squad commands
    squad_parser = subparsers.add_parser("squad", help="Manage squads")
    squad_subparsers = squad_parser.add_subparsers(dest="squad_command")

    squad_list_parser = squad_subparsers.add_parser("list", help="List squads")
    squad_list_parser.add_argument("--limit", type=int, help="Limit number of results")

    squad_get_parser = squad_subparsers.add_parser("get", help="Get squad details")
    squad_get_parser.add_argument("id", help="Squad ID")

    # Squad file-based commands
    squad_init_parser = squad_subparsers.add_parser("init", help="Initialize new squad from template")
    squad_init_parser.add_argument("name", help="Squad name (directory name)")
    squad_init_parser.add_argument("--template", default="dental_clinic_squad", help="Template to use")
    squad_init_parser.add_argument("--assistants", help="Comma-separated list of assistant names")
    squad_init_parser.add_argument("--description", help="Squad description")
    squad_init_parser.add_argument("--force", action="store_true", help="Overwrite if squad exists")
    squad_init_parser.add_argument("--dir", default="squads", help="Directory for squads")

    squad_create_parser = squad_subparsers.add_parser("create", help="Create squad in VAPI and track ID")
    squad_create_parser.add_argument("name", help="Squad name (directory name)")
    squad_create_parser.add_argument("--env", default="development", choices=["development", "staging", "production"], help="Environment to deploy to")
    squad_create_parser.add_argument("--force", action="store_true", help="Force recreation if already deployed")
    squad_create_parser.add_argument("--dir", default="squads", help="Directory containing squads")

    squad_file_list_parser = squad_subparsers.add_parser("file-list", help="List file-based squads")
    squad_file_list_parser.add_argument("--dir", default="squads", help="Directory containing squads")

    squad_templates_parser = squad_subparsers.add_parser("templates", help="List available squad templates")

    squad_template_info_parser = squad_subparsers.add_parser("template-info", help="Show squad template information")
    squad_template_info_parser.add_argument("template", help="Template name")

    squad_update_parser = squad_subparsers.add_parser("update", help="Update an existing squad with change detection")
    squad_update_parser.add_argument("name", help="Squad name (directory name)")
    squad_update_parser.add_argument("--env", default="development", choices=["development", "staging", "production"], help="Environment to update")
    squad_update_parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them")
    squad_update_parser.add_argument("--force", action="store_true", help="Force update even if no changes detected")
    squad_update_parser.add_argument("--dir", default="squads", help="Directory containing squads")

    squad_status_parser = squad_subparsers.add_parser("status", help="Show squad deployment status")
    squad_status_parser.add_argument("name", nargs="?", help="Squad name (optional, shows all if omitted)")
    squad_status_parser.add_argument("--dir", default="squads", help="Directory containing squads")

    squad_delete_parser = squad_subparsers.add_parser("delete", help="Delete a squad from VAPI")
    squad_delete_parser.add_argument("name", help="Squad name to delete")
    squad_delete_parser.add_argument("--env", default="development", choices=["development", "staging", "production"], help="Environment to delete from")
    squad_delete_parser.add_argument("--force", action="store_true", help="Force deletion without confirmation")
    squad_delete_parser.add_argument("--delete-assistants", action="store_true", help="Also delete all assistants that are members of this squad")
    squad_delete_parser.add_argument("--dir", default="squads", help="Directory containing squads")

    # Squad backup and restore commands
    squad_backup_parser = squad_subparsers.add_parser("backup", help="Create a backup of a squad with all related components")
    squad_backup_parser.add_argument("squad_name", help="Squad name to backup")
    squad_backup_parser.add_argument("--env", default="development", choices=["development", "staging", "production"], help="Environment to backup from")
    squad_backup_parser.add_argument("--type", default="complete", choices=["complete", "squad_only", "with_assistants"], help="Squad backup type")
    squad_backup_parser.add_argument("--description", help="Backup description")
    squad_backup_parser.add_argument("--tags", help="Comma-separated tags for the backup")
    squad_backup_parser.add_argument("--dir", default="squads", help="Directory containing squads")

    squad_restore_parser = squad_subparsers.add_parser("restore", help="Restore a squad from backup with all related components")
    squad_restore_parser.add_argument("backup_path", help="Path to squad backup file")
    squad_restore_parser.add_argument("--env", default="development", choices=["development", "staging", "production"], help="Target environment for restore")
    squad_restore_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing squad and assistants")
    squad_restore_parser.add_argument("--config-only", action="store_true", help="Restore only local configuration")
    squad_restore_parser.add_argument("--vapi-only", action="store_true", help="Restore only VAPI data")
    squad_restore_parser.add_argument("--skip-assistants", action="store_true", help="Skip restoring assistants")
    squad_restore_parser.add_argument("--assistant-prefix", default="", help="Prefix for restored assistant names")
    squad_restore_parser.add_argument("--squad-name", help="Override squad name for restore")
    squad_restore_parser.add_argument("--dry-run", action="store_true", help="Preview restore without applying changes")
    squad_restore_parser.add_argument("--dir", default="squads", help="Directory for squads")

    squad_backups_parser = squad_subparsers.add_parser("backups", help="List available squad backups")
    squad_backups_parser.add_argument("--dir", default="squads", help="Directory containing squads")

    squad_backup_info_parser = squad_subparsers.add_parser("backup-info", help="Show detailed squad backup information")
    squad_backup_info_parser.add_argument("backup_id", help="Squad backup ID to show details for")
    squad_backup_info_parser.add_argument("--dir", default="squads", help="Directory containing squads")

    squad_backup_delete_parser = squad_subparsers.add_parser("backup-delete", help="Delete a squad backup")
    squad_backup_delete_parser.add_argument("backup_id", help="Squad backup ID to delete")
    squad_backup_delete_parser.add_argument("--dir", default="squads", help="Directory containing squads")

    # Agent commands
    agent_parser = subparsers.add_parser("agent", help="Manage agents")
    agent_subparsers = agent_parser.add_subparsers(dest="agent_command")

    agent_list_parser = agent_subparsers.add_parser("list", help="List agents")
    agent_list_parser.add_argument("--limit", type=int, help="Limit number of results")

    # File-based assistant commands
    file_parser = subparsers.add_parser("file", help="Manage file-based assistant configurations")
    file_subparsers = file_parser.add_subparsers(dest="file_command")

    file_list_parser = file_subparsers.add_parser("list", help="List file-based assistants")
    file_list_parser.add_argument("--dir", default="assistants", help="Directory containing assistants")

    file_validate_parser = file_subparsers.add_parser("validate", help="Validate assistant configuration")
    file_validate_parser.add_argument("name", help="Assistant name (directory name)")
    file_validate_parser.add_argument("--dir", default="assistants", help="Directory containing assistants")

    file_deploy_parser = file_subparsers.add_parser("deploy", help="Deploy assistant to VAPI")
    file_deploy_parser.add_argument("name", help="Assistant name (directory name)")
    file_deploy_parser.add_argument("--env", default="default", help="Environment (default, development, staging, production)")
    file_deploy_parser.add_argument("--dir", default="assistants", help="Directory containing assistants")

    file_init_parser = file_subparsers.add_parser("init", help="Initialize new assistant from template")
    file_init_parser.add_argument("name", help="Assistant name (directory name)")
    file_init_parser.add_argument("--template", default="vicky_dental_clinic", help="Template to use")
    file_init_parser.add_argument("--force", action="store_true", help="Overwrite if assistant exists")

    file_templates_parser = file_subparsers.add_parser("templates", help="List available templates")

    file_template_info_parser = file_subparsers.add_parser("template-info", help="Show template information")
    file_template_info_parser.add_argument("template", help="Template name")

    file_create_parser = file_subparsers.add_parser("create", help="Create assistant in VAPI and track ID")
    file_create_parser.add_argument("name", help="Assistant name (directory name)")
    file_create_parser.add_argument("--env", default="production", choices=["development", "staging", "production"], help="Environment to deploy to")
    file_create_parser.add_argument("--force", action="store_true", help="Force recreation if already deployed")
    file_create_parser.add_argument("--dir", default="assistants", help="Directory containing assistants")

    file_status_parser = file_subparsers.add_parser("status", help="Show deployment status")
    file_status_parser.add_argument("name", nargs="?", help="Assistant name (optional, shows all if omitted)")
    file_status_parser.add_argument("--dir", default="assistants", help="Directory containing assistants")

    file_update_parser = file_subparsers.add_parser("update", help="Update an existing assistant with change detection")
    file_update_parser.add_argument("name", help="Assistant name (directory name)")
    file_update_parser.add_argument("--env", default="development", choices=["development", "staging", "production"], help="Environment to update")
    file_update_parser.add_argument("--scope", default="full", choices=["configuration", "prompts", "tools", "analysis", "full"], help="Update scope")
    file_update_parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them")
    file_update_parser.add_argument("--no-backup", action="store_true", help="Skip backup creation")
    file_update_parser.add_argument("--force", action="store_true", help="Force update even if no changes detected")
    file_update_parser.add_argument("--dir", default="assistants", help="Directory containing assistants")

    # Assistant backup and restore commands
    file_backup_parser = file_subparsers.add_parser("backup", help="Create a backup of assistants")
    file_backup_parser.add_argument("assistants", nargs="*", help="Assistant names to backup (leave empty for all)")
    file_backup_parser.add_argument("--env", default="development", choices=["development", "staging", "production"], help="Environment to backup from")
    file_backup_parser.add_argument("--type", default="full", choices=["full", "vapi_only", "config_only"], help="Backup type")
    file_backup_parser.add_argument("--description", help="Backup description")
    file_backup_parser.add_argument("--tags", help="Comma-separated tags for the backup")
    file_backup_parser.add_argument("--dir", default="assistants", help="Directory containing assistants")

    file_restore_parser = file_subparsers.add_parser("restore", help="Restore assistants from a backup")
    file_restore_parser.add_argument("backup_path", help="Path to backup file")
    file_restore_parser.add_argument("--env", default="development", choices=["development", "staging", "production"], help="Target environment for restore")
    file_restore_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing assistants")
    file_restore_parser.add_argument("--config-only", action="store_true", help="Restore only local configuration")
    file_restore_parser.add_argument("--vapi-only", action="store_true", help="Restore only VAPI data")
    file_restore_parser.add_argument("--dry-run", action="store_true", help="Preview restore without applying changes")
    file_restore_parser.add_argument("--dir", default="assistants", help="Directory for assistants")

    file_backups_parser = file_subparsers.add_parser("backups", help="List available backups")
    file_backups_parser.add_argument("--dir", default="assistants", help="Directory containing assistants")

    file_backup_info_parser = file_subparsers.add_parser("backup-info", help="Show detailed backup information")
    file_backup_info_parser.add_argument("backup_id", help="Backup ID to show details for")
    file_backup_info_parser.add_argument("--dir", default="assistants", help="Directory containing assistants")

    file_backup_delete_parser = file_subparsers.add_parser("backup-delete", help="Delete a backup")
    file_backup_delete_parser.add_argument("backup_id", help="Backup ID to delete")
    file_backup_delete_parser.add_argument("--dir", default="assistants", help="Directory containing assistants")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "assistant" or args.command == "ast":
            if args.assistant_command == "list":
                asyncio.run(list_assistants(args.limit))
            elif args.assistant_command == "get":
                asyncio.run(get_assistant(args.id))
            elif args.assistant_command == "validate":
                asyncio.run(validate_assistant(args.name, args.dir))
            elif args.assistant_command == "init":
                init_assistant(args.name, args.template, args.force)
            elif args.assistant_command == "delete":
                asyncio.run(delete_assistant(args.name, args.env, args.force, args.dir))
            elif args.assistant_command == "update":
                asyncio.run(update_assistant(
                    args.name,
                    args.env,
                    args.scope,
                    args.dry_run,
                    not args.no_backup,
                    args.force,
                    args.dir
                ))
            elif args.assistant_command == "backup":
                assistant_names = args.assistants if args.assistants else None
                asyncio.run(backup_assistants(
                    assistant_names,
                    args.env,
                    args.type,
                    args.description,
                    args.tags,
                    args.dir
                ))
            elif args.assistant_command == "restore":
                # Parse restore options
                restore_config = not args.vapi_only
                restore_vapi = not args.config_only

                asyncio.run(restore_backup(
                    args.backup_path,
                    args.env,
                    args.overwrite,
                    restore_config,
                    restore_vapi,
                    args.dry_run,
                    args.dir
                ))
            else:
                assistant_parser.print_help()
        elif args.command == "squad":
            if args.squad_command == "list":
                asyncio.run(list_squads(args.limit))
            elif args.squad_command == "get":
                asyncio.run(get_squad(args.id))
            elif args.squad_command == "init":
                assistants = args.assistants.split(',') if args.assistants else None
                init_squad(args.name, args.template, assistants, args.description, args.force, args.dir)
            elif args.squad_command == "create":
                asyncio.run(create_squad(args.name, args.env, args.force, args.dir))
            elif args.squad_command == "file-list":
                list_file_squads(args.dir)
            elif args.squad_command == "templates":
                list_squad_templates()
            elif args.squad_command == "template-info":
                show_squad_template_info(args.template)
            elif args.squad_command == "update":
                asyncio.run(update_squad(args.name, args.env, args.dry_run, args.force, args.dir))
            elif args.squad_command == "status":
                asyncio.run(show_squad_status(args.name, args.dir))
            elif args.squad_command == "delete":
                asyncio.run(delete_squad(args.name, args.env, args.force, args.delete_assistants, args.dir))
            elif args.squad_command == "backup":
                asyncio.run(backup_squad(
                    args.squad_name,
                    args.env,
                    args.type,
                    args.description,
                    args.tags,
                    args.dir
                ))
            elif args.squad_command == "restore":
                # Parse restore options
                restore_config = not args.vapi_only
                restore_vapi = not args.config_only
                restore_assistants = not args.skip_assistants

                asyncio.run(restore_squad_backup(
                    args.backup_path,
                    args.env,
                    args.overwrite,
                    restore_config,
                    restore_vapi,
                    restore_assistants,
                    args.assistant_prefix,
                    args.squad_name,
                    args.dry_run,
                    args.dir
                ))
            elif args.squad_command == "backups":
                list_squad_backups(args.dir)
            elif args.squad_command == "backup-info":
                show_squad_backup_details(args.backup_id, args.dir)
            elif args.squad_command == "backup-delete":
                delete_squad_backup(args.backup_id, args.dir)
            else:
                squad_parser.print_help()
        elif args.command == "agent":
            if args.agent_command == "list":
                asyncio.run(list_agents(args.limit))
            else:
                agent_parser.print_help()
        elif args.command == "file":
            if args.file_command == "list":
                list_file_assistants(args.dir)
            elif args.file_command == "validate":
                asyncio.run(validate_assistant(args.name, args.dir))
            elif args.file_command == "deploy":
                asyncio.run(deploy_assistant(args.name, args.env, args.dir))
            elif args.file_command == "init":
                init_assistant(args.name, args.template, args.force)
            elif args.file_command == "templates":
                list_templates()
            elif args.file_command == "template-info":
                show_template_info(args.template)
            elif args.file_command == "create":
                asyncio.run(create_assistant(args.name, args.env, args.force, args.dir))
            elif args.file_command == "status":
                show_assistant_status(args.name, args.dir)
            elif args.file_command == "update":
                asyncio.run(update_assistant(
                    args.name,
                    args.env,
                    args.scope,
                    args.dry_run,
                    not args.no_backup,
                    args.force,
                    args.dir
                ))
            elif args.file_command == "backup":
                assistant_names = args.assistants if args.assistants else None
                asyncio.run(backup_assistants(
                    assistant_names,
                    args.env,
                    args.type,
                    args.description,
                    args.tags,
                    args.dir
                ))
            elif args.file_command == "restore":
                # Parse restore options
                restore_config = not args.vapi_only
                restore_vapi = not args.config_only

                asyncio.run(restore_backup(
                    args.backup_path,
                    args.env,
                    args.overwrite,
                    restore_config,
                    restore_vapi,
                    args.dry_run,
                    args.dir
                ))
            elif args.file_command == "backups":
                list_backups(args.dir)
            elif args.file_command == "backup-info":
                show_backup_details(args.backup_id, args.dir)
            elif args.file_command == "backup-delete":
                delete_backup(args.backup_id, args.dir)
            else:
                file_parser.print_help()
        else:
            parser.print_help()
    except VAPIException as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()