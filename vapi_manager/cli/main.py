import typer
from rich.console import Console
from rich.table import Table
import asyncio
from typing import Optional, List

from ..services import AssistantService, SquadService, AgentService
from ..core.models import (
    AssistantCreateRequest, AssistantUpdateRequest,
    SquadCreateRequest, SquadUpdateRequest, SquadMember,
    AgentCreateRequest, AgentUpdateRequest
)
from ..core.exceptions.vapi_exceptions import VAPIException

app = typer.Typer(help="VAPI Assistant and Squad Management Tool")
console = Console()

# Subcommands
assistant_app = typer.Typer(help="Manage VAPI assistants")
squad_app = typer.Typer(help="Manage VAPI squads")
agent_app = typer.Typer(help="Manage VAPI agents")

app.add_typer(assistant_app, name="assistant")
app.add_typer(squad_app, name="squad")
app.add_typer(agent_app, name="agent")


def handle_error(func):
    """Decorator to handle async exceptions."""
    def wrapper(*args, **kwargs):
        try:
            return asyncio.run(func(*args, **kwargs))
        except VAPIException as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
            raise typer.Exit(1)
    return wrapper


@assistant_app.command("list")
@handle_error
async def list_assistants(limit: Optional[int] = None):
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
            assistant.voice.provider,
            assistant.created_at.strftime("%Y-%m-%d %H:%M") if assistant.created_at else "N/A"
        )

    console.print(table)


@assistant_app.command("get")
@handle_error
async def get_assistant(assistant_id: str):
    """Get assistant details by ID."""
    service = AssistantService()
    assistant = await service.get_assistant(assistant_id)

    console.print(f"[cyan]Assistant ID:[/cyan] {assistant.id}")
    console.print(f"[cyan]Name:[/cyan] {assistant.name}")
    console.print(f"[cyan]Model:[/cyan] {assistant.model.model} ({assistant.model.provider})")
    console.print(f"[cyan]Voice:[/cyan] {assistant.voice.voice_id} ({assistant.voice.provider})")
    if assistant.first_message:
        console.print(f"[cyan]First Message:[/cyan] {assistant.first_message}")
    console.print(f"[cyan]Created:[/cyan] {assistant.created_at}")
    console.print(f"[cyan]Updated:[/cyan] {assistant.updated_at}")


@assistant_app.command("delete")
@handle_error
async def delete_assistant(assistant_id: str):
    """Delete an assistant."""
    service = AssistantService()
    success = await service.delete_assistant(assistant_id)

    if success:
        console.print(f"[green]Successfully deleted assistant {assistant_id}[/green]")
    else:
        console.print(f"[red]Failed to delete assistant {assistant_id}[/red]")


@squad_app.command("list")
@handle_error
async def list_squads(limit: Optional[int] = None):
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
            squad.name,
            str(members_count),
            squad.created_at.strftime("%Y-%m-%d %H:%M") if squad.created_at else "N/A"
        )

    console.print(table)


@squad_app.command("get")
@handle_error
async def get_squad(squad_id: str):
    """Get squad details by ID."""
    service = SquadService()
    squad = await service.get_squad(squad_id)

    console.print(f"[cyan]Squad ID:[/cyan] {squad.id}")
    console.print(f"[cyan]Name:[/cyan] {squad.name}")
    console.print(f"[cyan]Members:[/cyan] {len(squad.members)}")

    if squad.members:
        console.print("[cyan]Assistant IDs:[/cyan]")
        for member in squad.members:
            console.print(f"  • {member.assistant_id}")

    console.print(f"[cyan]Created:[/cyan] {squad.created_at}")
    console.print(f"[cyan]Updated:[/cyan] {squad.updated_at}")


@squad_app.command("delete")
@handle_error
async def delete_squad(squad_id: str):
    """Delete a squad."""
    service = SquadService()
    success = await service.delete_squad(squad_id)

    if success:
        console.print(f"[green]Successfully deleted squad {squad_id}[/green]")
    else:
        console.print(f"[red]Failed to delete squad {squad_id}[/red]")


@agent_app.command("list")
@handle_error
async def list_agents(limit: Optional[int] = None):
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


@agent_app.command("get")
@handle_error
async def get_agent(squad_id: str):
    """Get agent details by squad ID."""
    service = AgentService()
    agent = await service.get_agent_by_squad_id(squad_id)

    console.print(f"[cyan]Agent Name:[/cyan] {agent.name}")
    console.print(f"[cyan]Squad ID:[/cyan] {agent.squad.id}")
    console.print(f"[cyan]Assistants:[/cyan] {len(agent.assistants)}")

    if agent.assistants:
        console.print("[cyan]Assistant Details:[/cyan]")
        for assistant in agent.assistants:
            console.print(f"  • {assistant.name} ({assistant.id}) - {assistant.model.model}")

    console.print(f"[cyan]Created:[/cyan] {agent.created_at}")
    console.print(f"[cyan]Updated:[/cyan] {agent.updated_at}")


@agent_app.command("delete")
@handle_error
async def delete_agent(squad_id: str):
    """Delete an agent (deletes the squad, assistants remain)."""
    service = AgentService()
    success = await service.delete_agent(squad_id)

    if success:
        console.print(f"[green]Successfully deleted agent with squad ID {squad_id}[/green]")
    else:
        console.print(f"[red]Failed to delete agent with squad ID {squad_id}[/red]")


if __name__ == "__main__":
    app()