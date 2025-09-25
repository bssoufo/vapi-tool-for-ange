"""
Dependency resolver for squad deployments.
Handles checking and resolving assistant dependencies before squad creation.
"""

from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path
from rich.console import Console

from ..core.deployment_state import DeploymentStateManager
from ..core.squad_config import SquadConfigLoader
from ..services.assistant_service import AssistantService
from ..core.exceptions.vapi_exceptions import VAPIException

console = Console()


class SquadDependencyResolver:
    """
    Resolves assistant dependencies for squad deployments.
    Checks which assistants need to be deployed and optionally deploys them.
    """

    def __init__(
        self,
        squads_directory: str = "squads",
        assistants_directory: str = "assistants"
    ):
        """
        Initialize the dependency resolver.

        Args:
            squads_directory: Directory containing squad configurations
            assistants_directory: Directory containing assistant configurations
        """
        self.squads_directory = Path(squads_directory)
        self.assistants_directory = Path(assistants_directory)
        self.deployment_state_manager = DeploymentStateManager(assistants_directory)
        self.squad_config_loader = SquadConfigLoader(squads_directory)
        self.assistant_service = AssistantService()

    async def check_missing_assistants(
        self,
        squad_name: str,
        environment: str = "development"
    ) -> List[str]:
        """
        Check which assistants are missing (not deployed) for a squad.

        Args:
            squad_name: Name of the squad
            environment: Target environment

        Returns:
            List of assistant names that are not deployed
        """
        missing_assistants = []

        try:
            # Load squad configuration
            squad_config = self.squad_config_loader.load_squad(squad_name, environment)

            # Check each member assistant
            for member in squad_config.members:
                assistant_name = member.get('assistant_name')
                if not assistant_name:
                    continue

                # Check if assistant is deployed
                deployment_info = self.deployment_state_manager.get_deployment_info(
                    assistant_name, environment
                )

                if not deployment_info.is_deployed():
                    missing_assistants.append(assistant_name)

            return missing_assistants

        except Exception as e:
            raise VAPIException(f"Error checking assistant dependencies: {str(e)}")

    async def get_dependency_status(
        self,
        squad_name: str,
        environment: str = "development"
    ) -> Dict[str, bool]:
        """
        Get deployment status for all assistant dependencies.

        Args:
            squad_name: Name of the squad
            environment: Target environment

        Returns:
            Dictionary mapping assistant names to deployment status
        """
        status = {}

        try:
            # Load squad configuration
            squad_config = self.squad_config_loader.load_squad(squad_name, environment)

            # Check each member assistant
            for member in squad_config.members:
                assistant_name = member.get('assistant_name')
                if not assistant_name:
                    continue

                # Check if assistant is deployed
                deployment_info = self.deployment_state_manager.get_deployment_info(
                    assistant_name, environment
                )

                status[assistant_name] = deployment_info.is_deployed()

            return status

        except Exception as e:
            raise VAPIException(f"Error getting dependency status: {str(e)}")

    async def deploy_assistant(
        self,
        assistant_name: str,
        environment: str = "development"
    ) -> Optional[str]:
        """
        Deploy a single assistant to VAPI.

        Args:
            assistant_name: Name of the assistant to deploy
            environment: Target environment

        Returns:
            Assistant ID if successful, None otherwise
        """
        from vapi_manager.core.assistant_config import AssistantConfigLoader, AssistantBuilder

        try:
            # Check if assistant directory exists
            assistant_path = self.assistants_directory / assistant_name
            if not assistant_path.exists():
                console.print(f"[red]Assistant configuration not found: {assistant_path}[/red]")
                return None

            # Load assistant configuration
            config_loader = AssistantConfigLoader(str(self.assistants_directory))
            assistant_config = config_loader.load_assistant(assistant_name, environment)

            # Validate configuration
            config_loader.validate_config(assistant_config)
            console.print("[green]Configuration validated successfully[/green]")

            # Build assistant request
            assistant_request = AssistantBuilder.build_from_config(assistant_config)

            # Create assistant in VAPI
            assistant = await self.assistant_service.create_assistant(assistant_request)

            if assistant:
                # Update deployment state
                self.deployment_state_manager.mark_deployed(
                    assistant_name,
                    environment,
                    assistant.id,
                    1  # Version defaults to 1 for new deployments
                )

                console.print(f"[green]+ Assistant created successfully![/green]")
                console.print(f"[cyan]Assistant ID:[/cyan] {assistant.id}")
                console.print(f"[cyan]Name:[/cyan] {assistant.name}")
                console.print(f"[cyan]Environment:[/cyan] {environment}")
                console.print(f"[cyan]Version:[/cyan] 1")
                console.print(f"[cyan]Deployed at:[/cyan] {assistant.created_at}")

                return assistant.id
            else:
                console.print(f"[red]Failed to create assistant '{assistant_name}'[/red]")
                return None

        except Exception as e:
            console.print(f"[red]Error deploying assistant '{assistant_name}': {str(e)}[/red]")
            return None

    async def deploy_missing_assistants(
        self,
        squad_name: str,
        environment: str = "development",
        force: bool = False
    ) -> Tuple[List[str], List[str]]:
        """
        Deploy all missing assistants for a squad.

        Args:
            squad_name: Name of the squad
            environment: Target environment
            force: Deploy without confirmation

        Returns:
            Tuple of (successfully deployed assistants, failed assistants)
        """
        missing_assistants = await self.check_missing_assistants(squad_name, environment)

        if not missing_assistants:
            console.print(f"[green]All assistants are already deployed for squad '{squad_name}'[/green]")
            return [], []

        console.print(f"[yellow]Found {len(missing_assistants)} missing assistant(s):[/yellow]")
        for assistant in missing_assistants:
            console.print(f"  - {assistant}")

        # Confirm deployment unless force is used
        if not force:
            from rich.prompt import Confirm
            confirmed = Confirm.ask(
                f"[yellow]Deploy {len(missing_assistants)} missing assistant(s)?[/yellow]"
            )
            if not confirmed:
                console.print("[yellow]Assistant deployment cancelled[/yellow]")
                return [], missing_assistants

        successfully_deployed = []
        failed_deployments = []

        for assistant_name in missing_assistants:
            console.print(f"\n[cyan]Deploying assistant: {assistant_name}...[/cyan]")
            assistant_id = await self.deploy_assistant(assistant_name, environment)

            if assistant_id:
                successfully_deployed.append(assistant_name)
            else:
                failed_deployments.append(assistant_name)

        # Summary
        if successfully_deployed:
            console.print(f"\n[green]Successfully deployed {len(successfully_deployed)} assistant(s):[/green]")
            for assistant in successfully_deployed:
                console.print(f"  + {assistant}")

        if failed_deployments:
            console.print(f"\n[red]Failed to deploy {len(failed_deployments)} assistant(s):[/red]")
            for assistant in failed_deployments:
                console.print(f"  - {assistant}")

        return successfully_deployed, failed_deployments

    async def ensure_squad_dependencies(
        self,
        squad_name: str,
        environment: str = "development",
        auto_deploy: bool = False,
        force: bool = False
    ) -> bool:
        """
        Ensure all squad dependencies are met.

        Args:
            squad_name: Name of the squad
            environment: Target environment
            auto_deploy: Automatically deploy missing assistants
            force: Deploy without confirmation

        Returns:
            True if all dependencies are met, False otherwise
        """
        missing_assistants = await self.check_missing_assistants(squad_name, environment)

        if not missing_assistants:
            console.print(f"[green]+ All assistants are deployed for squad '{squad_name}'[/green]")
            return True

        console.print(f"[yellow]Missing assistants for squad '{squad_name}':[/yellow]")
        for assistant in missing_assistants:
            console.print(f"  - {assistant}")

        if auto_deploy:
            console.print(f"\n[cyan]Auto-deploying {len(missing_assistants)} missing assistant(s)...[/cyan]")
            successfully_deployed, failed_deployments = await self.deploy_missing_assistants(
                squad_name, environment, force
            )

            if failed_deployments:
                console.print(f"[red]Failed to deploy all required assistants[/red]")
                return False

            return True
        else:
            console.print(f"\n[yellow]To deploy missing assistants, use one of these options:[/yellow]")
            console.print(f"  1. Deploy individually: vapi-manager assistant create <name> --env {environment}")
            console.print(f"  2. Auto-deploy with squad: vapi-manager squad create {squad_name} --env {environment} --auto-deploy-assistants")
            return False

    def get_all_squad_assistants(self, squad_name: str) -> Set[str]:
        """
        Get all assistant names referenced by a squad.

        Args:
            squad_name: Name of the squad

        Returns:
            Set of assistant names
        """
        assistants = set()

        try:
            # Load squad configuration (use development as default to get all members)
            squad_config = self.squad_config_loader.load_squad(squad_name, "development")

            for member in squad_config.members:
                assistant_name = member.get('assistant_name')
                if assistant_name:
                    assistants.add(assistant_name)

            return assistants

        except Exception as e:
            console.print(f"[yellow]Warning: Could not get squad assistants: {str(e)}[/yellow]")
            return set()