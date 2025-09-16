#!/usr/bin/env python3

import argparse
import asyncio
import sys
from rich.console import Console
from rich.table import Table

from ..services import AssistantService, SquadService, AgentService
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


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="VAPI Assistant and Squad Management Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Assistant commands
    assistant_parser = subparsers.add_parser("assistant", help="Manage assistants")
    assistant_subparsers = assistant_parser.add_subparsers(dest="assistant_command")

    assistant_list_parser = assistant_subparsers.add_parser("list", help="List assistants")
    assistant_list_parser.add_argument("--limit", type=int, help="Limit number of results")

    assistant_get_parser = assistant_subparsers.add_parser("get", help="Get assistant details")
    assistant_get_parser.add_argument("id", help="Assistant ID")

    # Squad commands
    squad_parser = subparsers.add_parser("squad", help="Manage squads")
    squad_subparsers = squad_parser.add_subparsers(dest="squad_command")

    squad_list_parser = squad_subparsers.add_parser("list", help="List squads")
    squad_list_parser.add_argument("--limit", type=int, help="Limit number of results")

    # Agent commands
    agent_parser = subparsers.add_parser("agent", help="Manage agents")
    agent_subparsers = agent_parser.add_subparsers(dest="agent_command")

    agent_list_parser = agent_subparsers.add_parser("list", help="List agents")
    agent_list_parser.add_argument("--limit", type=int, help="Limit number of results")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "assistant":
            if args.assistant_command == "list":
                asyncio.run(list_assistants(args.limit))
            elif args.assistant_command == "get":
                asyncio.run(get_assistant(args.id))
            else:
                assistant_parser.print_help()
        elif args.command == "squad":
            if args.squad_command == "list":
                asyncio.run(list_squads(args.limit))
            else:
                squad_parser.print_help()
        elif args.command == "agent":
            if args.agent_command == "list":
                asyncio.run(list_agents(args.limit))
            else:
                agent_parser.print_help()
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