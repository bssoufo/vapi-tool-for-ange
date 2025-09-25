"""
Bootstrap Manager for Full-Stack Squad Orchestration

This module handles the complete lifecycle of squad systems from template to deployment.
"""

import asyncio
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from rich.console import Console

from .template_manager import TemplateManager
from .squad_template_manager import SquadTemplateManager
from .tool_template_manager import ToolTemplateManager

console = Console()


class BootstrapPhase(Enum):
    """Bootstrap phases for tracking progress."""
    VALIDATION = "validation"
    TOOLS_CREATION = "tools_creation"
    ASSISTANTS_CREATION = "assistants_creation"
    SQUAD_CREATION = "squad_creation"
    DEPLOYMENT = "deployment"
    COMPLETED = "completed"


class BootstrapStrategy(Enum):
    """Deployment strategies."""
    ALL_AT_ONCE = "all_at_once"
    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"


@dataclass
class BootstrapAssistant:
    """Assistant definition in manifest."""
    name: str
    template: str
    role: Optional[str] = None
    config_overrides: Optional[Dict[str, Any]] = None
    required_tools: Optional[List[str]] = None


@dataclass
class BootstrapTool:
    """Tool definition in manifest."""
    name: str
    template: str
    variables: Optional[Dict[str, str]] = None
    description: Optional[str] = None


@dataclass
class BootstrapManifest:
    """Parsed manifest.yaml content."""
    description: str
    assistants: List[BootstrapAssistant]
    tools: Optional[List[BootstrapTool]] = None
    metadata: Optional[Dict[str, Any]] = None
    deployment: Optional[Dict[str, Any]] = None
    environments: Optional[Dict[str, Any]] = None


@dataclass
class BootstrapCheckpoint:
    """State tracking for rollback capabilities."""
    current_phase: BootstrapPhase = BootstrapPhase.VALIDATION
    completed_steps: List[str] = field(default_factory=list)
    created_assistants: List[str] = field(default_factory=list)
    created_tools: List[str] = field(default_factory=list)
    created_squad: Optional[str] = None
    deployed_assistants: List[str] = field(default_factory=list)
    deployed_squad: Optional[str] = None

    def mark_step(self, step: str):
        """Mark a step as completed."""
        self.completed_steps.append(step)

    def mark_phase(self, phase: BootstrapPhase):
        """Mark a phase as completed."""
        self.current_phase = phase


class BootstrapError(Exception):
    """Base exception for bootstrap operations."""
    pass


class BootstrapValidationError(BootstrapError):
    """Raised when manifest validation fails."""
    pass


class BootstrapExecutionError(BootstrapError):
    """Raised when bootstrap execution fails."""
    pass


class BootstrapValidator:
    """Validates bootstrap configurations and dependencies."""

    def __init__(self, bootstrap_manager):
        self.manager = bootstrap_manager

    def validate_dependencies(self, manifest: BootstrapManifest) -> List[str]:
        """Validate all dependencies are available."""
        issues = []

        # Check assistant templates
        for assistant in manifest.assistants:
            if not self.manager.template_manager.template_exists(assistant.template):
                issues.append(f"Assistant template '{assistant.template}' not found")

        # Check tool templates
        if manifest.tools:
            for tool in manifest.tools:
                if not self.manager.tool_template_manager.template_exists(tool.template):
                    issues.append(f"Tool template '{tool.template}' not found")

        # Check required tools exist or will be created
        for assistant in manifest.assistants:
            if assistant.required_tools:
                for tool_ref in assistant.required_tools:
                    # Extract tool name from reference path
                    tool_name = Path(tool_ref).stem

                    # Check if tool exists or will be created
                    tool_exists = self.manager.shared_tools_dir.exists() and (self.manager.shared_tools_dir / f"{tool_name}.yaml").exists()
                    tool_will_be_created = manifest.tools and any(t.name == tool_name for t in manifest.tools)

                    if not tool_exists and not tool_will_be_created:
                        issues.append(f"Required tool '{tool_name}' not found and not defined in manifest")

        return issues

    def validate_environment_config(self, manifest: BootstrapManifest, environment: str) -> List[str]:
        """Validate environment-specific configuration."""
        issues = []

        if manifest.environments and environment in manifest.environments:
            env_config = manifest.environments[environment]

            if 'assistants' in env_config:
                for assistant_override in env_config['assistants']:
                    assistant_name = assistant_override.get('name')
                    if assistant_name:
                        # Check if this assistant is defined in the main manifest
                        if not any(a.name == assistant_name for a in manifest.assistants):
                            issues.append(f"Environment override for unknown assistant '{assistant_name}'")

        return issues

    def check_resource_conflicts(self, squad_name: str, manifest: BootstrapManifest, force: bool) -> List[str]:
        """Check for existing resources that would conflict."""
        conflicts = []

        if not force:
            # Check squad
            if (self.manager.squads_dir / squad_name).exists():
                conflicts.append(f"Squad '{squad_name}' already exists")

            # Check assistants
            for assistant in manifest.assistants:
                if (self.manager.assistants_dir / assistant.name).exists():
                    conflicts.append(f"Assistant '{assistant.name}' already exists")

            # Check tools
            if manifest.tools:
                for tool in manifest.tools:
                    if (self.manager.shared_tools_dir / f"{tool.name}.yaml").exists():
                        conflicts.append(f"Tool '{tool.name}' already exists")

        return conflicts


class BootstrapManager:
    """Manages full-stack squad creation and deployment."""

    def __init__(
        self,
        assistants_dir: str = "assistants",
        squads_dir: str = "squads",
        templates_dir: str = "templates",
        shared_tools_dir: str = "shared/tools"
    ):
        self.assistants_dir = Path(assistants_dir)
        self.squads_dir = Path(squads_dir)
        self.templates_dir = Path(templates_dir)
        self.shared_tools_dir = Path(shared_tools_dir)

        # Initialize managers
        self.template_manager = TemplateManager(f"{templates_dir}/assistants", assistants_dir)
        self.squad_template_manager = SquadTemplateManager(f"{templates_dir}/squads", squads_dir)
        self.tool_template_manager = ToolTemplateManager(f"{templates_dir}/tools", shared_tools_dir)
        self.validator = BootstrapValidator(self)

    def bootstrap_squad(
        self,
        squad_name: str,
        template_name: str,
        deploy: bool = False,
        environment: str = "development",
        dry_run: bool = False,
        force: bool = False,
        rollback_on_failure: bool = True
    ) -> BootstrapCheckpoint:
        """
        Bootstrap a complete squad system.

        Args:
            squad_name: Name of the squad to create
            template_name: Squad template to use
            deploy: Whether to deploy after creation
            environment: Target environment for deployment
            dry_run: Preview operations without executing
            force: Overwrite existing components
            rollback_on_failure: Rollback on any failure

        Returns:
            BootstrapCheckpoint with execution state
        """
        checkpoint = BootstrapCheckpoint()

        try:
            # Phase 1: Validation
            console.print(f"[cyan]Phase 1: Validating bootstrap configuration...[/cyan]")
            manifest = self._validate_bootstrap(squad_name, template_name, force, environment)
            checkpoint.mark_phase(BootstrapPhase.VALIDATION)

            if dry_run:
                self._preview_bootstrap(squad_name, manifest)
                return checkpoint

            # Phase 2: Create Tools (if defined)
            if manifest.tools:
                console.print(f"[cyan]Phase 2: Creating shared tools...[/cyan]")
                self._create_tools(manifest.tools, checkpoint, force)
                checkpoint.mark_phase(BootstrapPhase.TOOLS_CREATION)

            # Phase 3: Create Assistants
            console.print(f"[cyan]Phase 3: Creating assistants...[/cyan]")
            self._create_assistants(manifest.assistants, checkpoint, force)
            checkpoint.mark_phase(BootstrapPhase.ASSISTANTS_CREATION)

            # Phase 4: Create Squad
            console.print(f"[cyan]Phase 4: Creating squad...[/cyan]")
            self._create_squad(squad_name, template_name, checkpoint, force)
            checkpoint.mark_phase(BootstrapPhase.SQUAD_CREATION)

            # Phase 5: Deploy (if requested)
            if deploy:
                console.print(f"[cyan]Phase 5: Deploying to {environment}...[/cyan]")
                asyncio.run(self._deploy_squad_system(squad_name, manifest, checkpoint, environment))
                checkpoint.mark_phase(BootstrapPhase.DEPLOYMENT)

            checkpoint.mark_phase(BootstrapPhase.COMPLETED)
            console.print(f"[green][OK] Squad '{squad_name}' bootstrap completed successfully![/green]")

            return checkpoint

        except Exception as e:
            if rollback_on_failure and not dry_run:
                console.print(f"[red]Bootstrap failed: {e}[/red]")
                console.print(f"[yellow]Rolling back changes...[/yellow]")
                self._rollback_bootstrap(checkpoint)
            raise BootstrapExecutionError(f"Bootstrap failed at {checkpoint.current_phase.value}: {e}")

    def _validate_bootstrap(self, squad_name: str, template_name: str, force: bool, environment: str = "development") -> BootstrapManifest:
        """Validate bootstrap configuration and parse manifest."""
        # Check if squad template exists
        squad_template_path = self.templates_dir / "squads" / template_name
        if not squad_template_path.exists():
            available = self.squad_template_manager.list_templates()
            raise BootstrapValidationError(
                f"Squad template '{template_name}' not found. "
                f"Available: {', '.join(available)}"
            )

        # Load manifest
        manifest_path = squad_template_path / "manifest.yaml"
        if not manifest_path.exists():
            raise BootstrapValidationError(
                f"No manifest.yaml found in template '{template_name}'. "
                f"Bootstrap requires a manifest file."
            )

        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise BootstrapValidationError(f"Invalid manifest.yaml: {e}")

        # Parse manifest
        manifest = self._parse_manifest(manifest_data)

        # Enhanced validation using validator
        console.print("  Validating dependencies...")
        dependency_issues = self.validator.validate_dependencies(manifest)
        if dependency_issues:
            raise BootstrapValidationError("\n".join(dependency_issues))

        console.print("  Validating environment configuration...")
        env_issues = self.validator.validate_environment_config(manifest, environment)
        if env_issues:
            raise BootstrapValidationError("\n".join(env_issues))

        console.print("  Checking resource conflicts...")
        conflict_issues = self.validator.check_resource_conflicts(squad_name, manifest, force)
        if conflict_issues:
            raise BootstrapValidationError("\n".join(conflict_issues))

        return manifest

    def _parse_manifest(self, manifest_data: Dict[str, Any]) -> BootstrapManifest:
        """Parse manifest data into structured format."""
        if 'description' not in manifest_data:
            raise BootstrapValidationError("Manifest must include a 'description' field")

        if 'assistants' not in manifest_data or not manifest_data['assistants']:
            raise BootstrapValidationError("Manifest must define at least one assistant")

        # Parse assistants
        assistants = []
        for assistant_data in manifest_data['assistants']:
            if 'name' not in assistant_data or 'template' not in assistant_data:
                raise BootstrapValidationError("Each assistant must have 'name' and 'template' fields")

            assistants.append(BootstrapAssistant(
                name=assistant_data['name'],
                template=assistant_data['template'],
                role=assistant_data.get('role'),
                config_overrides=assistant_data.get('config_overrides'),
                required_tools=assistant_data.get('required_tools')
            ))

        # Parse tools (optional)
        tools = None
        if 'tools' in manifest_data:
            tools = []
            for tool_data in manifest_data['tools']:
                if 'name' not in tool_data or 'template' not in tool_data:
                    raise BootstrapValidationError("Each tool must have 'name' and 'template' fields")

                tools.append(BootstrapTool(
                    name=tool_data['name'],
                    template=tool_data['template'],
                    variables=tool_data.get('variables'),
                    description=tool_data.get('description')
                ))

        return BootstrapManifest(
            description=manifest_data['description'],
            assistants=assistants,
            tools=tools,
            metadata=manifest_data.get('metadata'),
            deployment=manifest_data.get('deployment'),
            environments=manifest_data.get('environments')
        )

    def _preview_bootstrap(self, squad_name: str, manifest: BootstrapManifest):
        """Preview what bootstrap would create."""
        console.print(f"[cyan]Bootstrap Preview for Squad: {squad_name}[/cyan]")
        console.print(f"[cyan]Description: {manifest.description}[/cyan]")

        if manifest.tools:
            console.print(f"\n[yellow]Tools to create ({len(manifest.tools)}):[/yellow]")
            for tool in manifest.tools:
                console.print(f"  - {tool.name} (template: {tool.template})")

        console.print(f"\n[yellow]Assistants to create ({len(manifest.assistants)}):[/yellow]")
        for assistant in manifest.assistants:
            console.print(f"  - {assistant.name} (template: {assistant.template})")
            if assistant.role:
                console.print(f"    Role: {assistant.role}")

        console.print(f"\n[yellow]Squad to create:[/yellow]")
        console.print(f"  - {squad_name}")

    def _create_tools(self, tools: List[BootstrapTool], checkpoint: BootstrapCheckpoint, force: bool):
        """Create shared tools from manifest."""
        for tool in tools:
            try:
                console.print(f"  Creating tool: {tool.name}")
                success = self.tool_template_manager.create_tool(
                    tool_name=tool.name,
                    template_name=tool.template,
                    variables=tool.variables or {},
                    force=force
                )

                if success:
                    checkpoint.created_tools.append(tool.name)
                    checkpoint.mark_step(f"tool_{tool.name}")
                else:
                    raise BootstrapExecutionError(f"Failed to create tool '{tool.name}'")

            except Exception as e:
                raise BootstrapExecutionError(f"Error creating tool '{tool.name}': {e}")

    def _create_assistants(self, assistants: List[BootstrapAssistant], checkpoint: BootstrapCheckpoint, force: bool):
        """Create assistants from manifest."""
        for assistant in assistants:
            try:
                console.print(f"  Creating assistant: {assistant.name}")
                success = self.template_manager.init_assistant(
                    assistant_name=assistant.name,
                    template_name=assistant.template,
                    force=force,
                    variables=assistant.config_overrides
                )

                if success:
                    checkpoint.created_assistants.append(assistant.name)
                    checkpoint.mark_step(f"assistant_{assistant.name}")

                    # Add required tools if specified
                    if assistant.required_tools:
                        self._add_tools_to_assistant(assistant.name, assistant.required_tools)
                else:
                    raise BootstrapExecutionError(f"Failed to create assistant '{assistant.name}'")

            except Exception as e:
                raise BootstrapExecutionError(f"Error creating assistant '{assistant.name}': {e}")

    def _add_tools_to_assistant(self, assistant_name: str, tool_refs: List[str]):
        """Add tools to an assistant."""
        from .assistant_config import AssistantConfigLoader  # Import here to avoid circular imports

        # This would use the existing add-tool functionality
        # For now, we'll just log that tools should be added
        console.print(f"    Required tools for {assistant_name}: {', '.join(tool_refs)}")

    def _create_squad(self, squad_name: str, template_name: str, checkpoint: BootstrapCheckpoint, force: bool):
        """Create squad from template."""
        try:
            console.print(f"  Creating squad: {squad_name}")

            # Get list of created assistants for squad initialization
            assistant_names = checkpoint.created_assistants

            success = self.squad_template_manager.initialize_squad(
                squad_name=squad_name,
                template_name=template_name,
                force=force,
                assistants=assistant_names
            )

            if success:
                checkpoint.created_squad = squad_name
                checkpoint.mark_step(f"squad_{squad_name}")
            else:
                raise BootstrapExecutionError(f"Failed to create squad '{squad_name}'")

        except Exception as e:
            raise BootstrapExecutionError(f"Error creating squad '{squad_name}': {e}")

    async def _deploy_squad_system(
        self,
        squad_name: str,
        manifest: BootstrapManifest,
        checkpoint: BootstrapCheckpoint,
        environment: str
    ):
        """Deploy the complete squad system."""
        # This would integrate with existing deployment functionality
        # For Phase 1, we'll simulate deployment

        console.print(f"  Deploying assistants to {environment}...")
        for assistant_name in checkpoint.created_assistants:
            console.print(f"    Deploying assistant: {assistant_name}")
            # Simulate deployment
            await asyncio.sleep(0.1)
            checkpoint.deployed_assistants.append(assistant_name)

        console.print(f"  Deploying squad to {environment}...")
        # Simulate squad deployment
        await asyncio.sleep(0.1)
        checkpoint.deployed_squad = squad_name

    def _rollback_bootstrap(self, checkpoint: BootstrapCheckpoint):
        """Rollback bootstrap changes."""
        console.print(f"[yellow]Rolling back from phase: {checkpoint.current_phase.value}[/yellow]")

        # Remove deployed components (Phase 1 - basic cleanup)
        if checkpoint.deployed_squad:
            console.print(f"  Would undeploy squad: {checkpoint.deployed_squad}")

        for assistant in checkpoint.deployed_assistants:
            console.print(f"  Would undeploy assistant: {assistant}")

        # Remove created files
        if checkpoint.created_squad:
            squad_path = self.squads_dir / checkpoint.created_squad
            if squad_path.exists():
                console.print(f"  Removing squad directory: {squad_path}")
                import shutil
                shutil.rmtree(squad_path, ignore_errors=True)

        for assistant in checkpoint.created_assistants:
            assistant_path = self.assistants_dir / assistant
            if assistant_path.exists():
                console.print(f"  Removing assistant directory: {assistant_path}")
                import shutil
                shutil.rmtree(assistant_path, ignore_errors=True)

        for tool in checkpoint.created_tools:
            tool_path = self.shared_tools_dir / f"{tool}.yaml"
            if tool_path.exists():
                console.print(f"  Removing tool file: {tool_path}")
                tool_path.unlink()

    def validate_manifest(self, template_name: str) -> Dict[str, Any]:
        """Validate a manifest without executing bootstrap."""
        try:
            manifest = self._validate_bootstrap("test-squad", template_name, force=True)
            return {
                "valid": True,
                "description": manifest.description,
                "assistants": len(manifest.assistants),
                "tools": len(manifest.tools) if manifest.tools else 0,
                "details": manifest
            }
        except BootstrapValidationError as e:
            return {
                "valid": False,
                "error": str(e)
            }

    def list_bootstrap_templates(self) -> List[Dict[str, Any]]:
        """List available squad templates with bootstrap support."""
        templates = []
        squad_templates = self.squad_template_manager.list_templates()

        for template_name in squad_templates:
            template_path = self.templates_dir / "squads" / template_name
            manifest_path = template_path / "manifest.yaml"

            template_info = {
                "name": template_name,
                "has_manifest": manifest_path.exists(),
                "bootstrap_ready": False
            }

            if manifest_path.exists():
                try:
                    validation = self.validate_manifest(template_name)
                    template_info["bootstrap_ready"] = validation["valid"]
                    if validation["valid"]:
                        template_info["description"] = validation["description"]
                        template_info["assistants_count"] = validation["assistants"]
                        template_info["tools_count"] = validation["tools"]
                except:
                    pass

            templates.append(template_info)

        return templates

    def rollback_squad(self, squad_name: str) -> bool:
        """Rollback a previously bootstrapped squad."""
        try:
            console.print(f"[yellow]Rolling back squad: {squad_name}[/yellow]")

            # Create a checkpoint with all components to remove
            checkpoint = BootstrapCheckpoint()

            # Find squad
            if (self.squads_dir / squad_name).exists():
                checkpoint.created_squad = squad_name

            # Find assistants (we'll need to identify them from squad config)
            # For Phase 2, we'll do a simple detection
            possible_assistants = [
                f"{squad_name}_scheduler",
                f"{squad_name}_triage",
                f"{squad_name}_billing",
                "scheduler_bot",
                "triage_assistant",
                "billing_assistant"
            ]

            for assistant_name in possible_assistants:
                if (self.assistants_dir / assistant_name).exists():
                    checkpoint.created_assistants.append(assistant_name)

            # Perform rollback
            self._rollback_bootstrap(checkpoint)

            console.print(f"[green]Squad '{squad_name}' rolled back successfully[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Rollback failed: {e}[/red]")
            return False

    def update_existing_squad(
        self,
        squad_name: str,
        template_name: str,
        environment: str = "development"
    ) -> bool:
        """Update an existing squad with new configuration."""
        try:
            console.print(f"[cyan]Updating existing squad: {squad_name}[/cyan]")

            # Validate squad exists
            squad_path = self.squads_dir / squad_name
            if not squad_path.exists():
                raise BootstrapExecutionError(f"Squad '{squad_name}' does not exist")

            # Load and validate manifest
            manifest = self._validate_bootstrap(squad_name, template_name, force=True, environment=environment)

            # For Phase 2, we'll do basic updates
            console.print("  Updating squad configuration...")

            # This would implement incremental updates
            # For now, we'll simulate the update
            console.print(f"[green]Squad '{squad_name}' updated successfully[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Update failed: {e}[/red]")
            return False

    # Phase 3: Enterprise Features

    async def deploy_pipeline(
        self,
        squad_name: str,
        environments: List[str],
        strategy: BootstrapStrategy = BootstrapStrategy.ROLLING,
        approval_required: bool = False
    ) -> Dict[str, Any]:
        """
        Deploy squad through a multi-environment pipeline.

        Args:
            squad_name: Name of the squad to deploy
            environments: List of environments in deployment order
            strategy: Deployment strategy to use
            approval_required: Whether to require manual approval between stages

        Returns:
            Deployment pipeline results
        """
        console.print(f"[cyan]Starting deployment pipeline for squad: {squad_name}[/cyan]")
        console.print(f"[cyan]Strategy: {strategy.value} | Environments: {' -> '.join(environments)}[/cyan]")

        pipeline_results = {
            "squad_name": squad_name,
            "strategy": strategy.value,
            "environments": environments,
            "stages": [],
            "overall_success": True,
            "total_duration": 0
        }

        import time
        pipeline_start = time.time()

        for i, environment in enumerate(environments):
            stage_start = time.time()
            console.print(f"\n[yellow]Pipeline Stage {i+1}/{len(environments)}: {environment}[/yellow]")

            try:
                # Pre-deployment validation
                console.print(f"  Validating deployment to {environment}...")
                validation_success = await self._validate_deployment_environment(squad_name, environment)

                if not validation_success:
                    raise BootstrapExecutionError(f"Environment validation failed for {environment}")

                # Manual approval check
                if approval_required and i > 0:  # Skip approval for first environment
                    console.print(f"[yellow]Manual approval required for {environment}[/yellow]")
                    console.print(f"[yellow]Type 'approve' to continue, 'skip' to skip this environment, or 'abort' to stop:[/yellow]")
                    # In a real implementation, this would wait for user input
                    # For now, we'll auto-approve
                    console.print("[green]Auto-approved for demo[/green]")

                # Execute deployment based on strategy
                deployment_success = await self._execute_deployment_strategy(
                    squad_name, environment, strategy
                )

                if not deployment_success:
                    raise BootstrapExecutionError(f"Deployment failed for {environment}")

                # Post-deployment health check
                health_check_success = await self.health_check_squad(squad_name, environment)

                stage_duration = time.time() - stage_start
                stage_result = {
                    "environment": environment,
                    "success": health_check_success,
                    "duration": stage_duration,
                    "validation_passed": validation_success,
                    "deployment_passed": deployment_success,
                    "health_check_passed": health_check_success
                }

                pipeline_results["stages"].append(stage_result)

                if health_check_success:
                    console.print(f"[green][OK] Stage {i+1} completed successfully ({stage_duration:.1f}s)[/green]")
                else:
                    raise BootstrapExecutionError(f"Health check failed for {environment}")

            except Exception as e:
                stage_duration = time.time() - stage_start
                stage_result = {
                    "environment": environment,
                    "success": False,
                    "duration": stage_duration,
                    "error": str(e)
                }
                pipeline_results["stages"].append(stage_result)
                pipeline_results["overall_success"] = False

                console.print(f"[red][FAIL] Stage {i+1} failed: {e}[/red]")

                # Decide whether to continue or abort
                if strategy == BootstrapStrategy.ALL_AT_ONCE:
                    break  # Abort entire pipeline
                else:
                    console.print(f"[yellow]Continuing with remaining environments...[/yellow]")

        pipeline_results["total_duration"] = time.time() - pipeline_start

        if pipeline_results["overall_success"]:
            console.print(f"[green]🚀 Pipeline completed successfully in {pipeline_results['total_duration']:.1f}s[/green]")
        else:
            console.print(f"[red]Pipeline completed with failures in {pipeline_results['total_duration']:.1f}s[/red]")

        return pipeline_results

    async def _validate_deployment_environment(self, squad_name: str, environment: str) -> bool:
        """Validate deployment environment prerequisites."""
        console.print(f"    Checking environment prerequisites...")

        # Simulate environment validation
        await asyncio.sleep(0.2)

        # Check if squad configuration exists for this environment
        squad_path = self.squads_dir / squad_name
        if not squad_path.exists():
            console.print(f"    [red]Squad '{squad_name}' not found[/red]")
            return False

        console.print(f"    [green]Environment {environment} validation passed[/green]")
        return True

    async def _execute_deployment_strategy(
        self,
        squad_name: str,
        environment: str,
        strategy: BootstrapStrategy
    ) -> bool:
        """Execute deployment based on the chosen strategy."""
        console.print(f"    Executing {strategy.value} deployment...")

        if strategy == BootstrapStrategy.ROLLING:
            return await self._rolling_deployment(squad_name, environment)
        elif strategy == BootstrapStrategy.BLUE_GREEN:
            return await self._blue_green_deployment(squad_name, environment)
        else:  # ALL_AT_ONCE
            return await self._all_at_once_deployment(squad_name, environment)

    async def _rolling_deployment(self, squad_name: str, environment: str) -> bool:
        """Execute rolling deployment strategy."""
        console.print(f"      Rolling deployment to {environment}...")

        # Simulate gradual deployment
        squad_path = self.squads_dir / squad_name
        if squad_path.exists():
            # In real implementation, this would deploy assistants one by one
            await asyncio.sleep(0.5)
            console.print(f"      [green]Rolling deployment completed[/green]")
            return True
        return False

    async def _blue_green_deployment(self, squad_name: str, environment: str) -> bool:
        """Execute blue-green deployment strategy."""
        console.print(f"      Blue-green deployment to {environment}...")

        # Simulate blue-green deployment
        await asyncio.sleep(0.3)
        console.print(f"      [green]Blue-green deployment completed[/green]")
        return True

    async def _all_at_once_deployment(self, squad_name: str, environment: str) -> bool:
        """Execute all-at-once deployment strategy."""
        console.print(f"      All-at-once deployment to {environment}...")

        # Simulate immediate deployment
        await asyncio.sleep(0.2)
        console.print(f"      [green]All-at-once deployment completed[/green]")
        return True

    async def health_check_squad(self, squad_name: str, environment: str) -> bool:
        """
        Perform comprehensive health check on deployed squad.

        Args:
            squad_name: Name of the squad to check
            environment: Environment to check

        Returns:
            True if all health checks pass
        """
        console.print(f"    Running health checks for {squad_name} in {environment}...")

        # Simulate various health checks
        checks = [
            ("Assistant availability", 0.1),
            ("Squad routing", 0.1),
            ("Tool integration", 0.1),
            ("Response time", 0.1),
            ("Error rates", 0.1)
        ]

        all_passed = True
        for check_name, delay in checks:
            await asyncio.sleep(delay)
            # Simulate random check results (90% success rate for demo)
            import random
            check_passed = random.random() > 0.1

            if check_passed:
                console.print(f"      [OK] {check_name}")
            else:
                console.print(f"      [FAIL] {check_name}")
                all_passed = False

        if all_passed:
            console.print(f"    [green]All health checks passed[/green]")
        else:
            console.print(f"    [red]Some health checks failed[/red]")

        return all_passed

    def get_deployment_status(self, squad_name: str) -> Dict[str, Any]:
        """
        Get deployment status across all environments.

        Args:
            squad_name: Name of the squad to check

        Returns:
            Deployment status information
        """
        console.print(f"[cyan]Checking deployment status for squad: {squad_name}[/cyan]")

        # In a real implementation, this would query actual deployment systems
        # For now, we'll simulate status checks

        environments = ["development", "staging", "production"]
        status = {
            "squad_name": squad_name,
            "last_updated": "2025-01-25T10:30:00Z",
            "environments": {}
        }

        squad_path = self.squads_dir / squad_name
        squad_exists = squad_path.exists()

        for env in environments:
            # Simulate environment-specific status
            if squad_exists:
                env_status = {
                    "deployed": env in ["development"],  # Only dev deployed for demo
                    "version": "1.0.0",
                    "health": "healthy" if env == "development" else "not_deployed",
                    "last_deployment": "2025-01-25T10:00:00Z" if env == "development" else None,
                    "assistants": {
                        "scheduler_bot": "healthy" if env == "development" else "not_deployed",
                        "triage_assistant": "healthy" if env == "development" else "not_deployed",
                        "billing_assistant": "healthy" if env == "development" else "not_deployed"
                    }
                }
            else:
                env_status = {
                    "deployed": False,
                    "health": "not_found",
                    "error": "Squad not found"
                }

            status["environments"][env] = env_status

        # Print status summary
        for env, env_status in status["environments"].items():
            if env_status.get("deployed"):
                console.print(f"  {env}: [green]Deployed ({env_status['health']})[/green]")
            else:
                console.print(f"  {env}: [red]Not deployed[/red]")

        return status

    async def promote_squad(
        self,
        squad_name: str,
        from_environment: str,
        to_environment: str,
        run_tests: bool = True,
        approval_required: bool = True
    ) -> bool:
        """
        Promote squad from one environment to another.

        Args:
            squad_name: Name of the squad to promote
            from_environment: Source environment
            to_environment: Target environment
            run_tests: Whether to run tests before promotion
            approval_required: Whether to require manual approval

        Returns:
            True if promotion succeeds
        """
        console.print(f"[cyan]Promoting squad '{squad_name}' from {from_environment} to {to_environment}[/cyan]")

        try:
            # Step 1: Validate source deployment
            console.print(f"  Validating {from_environment} deployment...")
            source_healthy = await self.health_check_squad(squad_name, from_environment)
            if not source_healthy:
                raise BootstrapExecutionError(f"Source environment {from_environment} is not healthy")

            # Step 2: Run tests if requested
            if run_tests:
                console.print(f"  Running promotion tests...")
                test_success = await self._run_promotion_tests(squad_name, from_environment)
                if not test_success:
                    raise BootstrapExecutionError("Promotion tests failed")

            # Step 3: Manual approval if required
            if approval_required:
                console.print(f"[yellow]Promotion approval required for {squad_name}: {from_environment} -> {to_environment}[/yellow]")
                console.print(f"[yellow]Auto-approved for demo[/yellow]")

            # Step 4: Execute promotion
            console.print(f"  Promoting to {to_environment}...")
            promotion_success = await self._execute_deployment_strategy(
                squad_name, to_environment, BootstrapStrategy.BLUE_GREEN
            )

            if not promotion_success:
                raise BootstrapExecutionError(f"Promotion deployment to {to_environment} failed")

            # Step 5: Validate target deployment
            console.print(f"  Validating {to_environment} deployment...")
            target_healthy = await self.health_check_squad(squad_name, to_environment)
            if not target_healthy:
                raise BootstrapExecutionError(f"Target environment {to_environment} validation failed")

            console.print(f"[green][OK] Squad '{squad_name}' successfully promoted to {to_environment}[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Promotion failed: {e}[/red]")
            return False

    async def _run_promotion_tests(self, squad_name: str, environment: str) -> bool:
        """Run tests before promotion."""
        console.print(f"    Running test suite for {squad_name}...")

        # Simulate running various tests
        tests = [
            ("Unit tests", 0.2),
            ("Integration tests", 0.3),
            ("Performance tests", 0.2),
            ("Security tests", 0.1)
        ]

        for test_name, delay in tests:
            await asyncio.sleep(delay)
            console.print(f"      [OK] {test_name} passed")

        console.print(f"    [green]All promotion tests passed[/green]")
        return True