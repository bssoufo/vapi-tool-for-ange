"""
Comprehensive unit tests for the Bootstrap Manager.

Tests all three phases:
- Phase 1: Core Bootstrap functionality
- Phase 2: Enhanced features (validation, rollback)
- Phase 3: Enterprise features (pipelines, health checks, promotion)
"""

import asyncio
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import asdict

from vapi_manager.core.bootstrap_manager import (
    BootstrapManager,
    BootstrapManifest,
    BootstrapAssistant,
    BootstrapTool,
    BootstrapCheckpoint,
    BootstrapPhase,
    BootstrapStrategy,
    BootstrapValidator,
    BootstrapValidationError,
    BootstrapExecutionError
)


class TestBootstrapManifest:
    """Test Bootstrap Manifest data structures."""

    def test_bootstrap_assistant_creation(self):
        """Test BootstrapAssistant creation."""
        assistant = BootstrapAssistant(
            name="test_assistant",
            template="test_template",
            role="Test role",
            config_overrides={"key": "value"},
            required_tools=["tool1", "tool2"]
        )

        assert assistant.name == "test_assistant"
        assert assistant.template == "test_template"
        assert assistant.role == "Test role"
        assert assistant.config_overrides == {"key": "value"}
        assert assistant.required_tools == ["tool1", "tool2"]

    def test_bootstrap_tool_creation(self):
        """Test BootstrapTool creation."""
        tool = BootstrapTool(
            name="test_tool",
            template="tool_template",
            variables={"url": "https://example.com"},
            description="Test tool"
        )

        assert tool.name == "test_tool"
        assert tool.template == "tool_template"
        assert tool.variables == {"url": "https://example.com"}
        assert tool.description == "Test tool"

    def test_bootstrap_manifest_creation(self):
        """Test BootstrapManifest creation."""
        assistant = BootstrapAssistant(name="test_assistant", template="test_template")
        tool = BootstrapTool(name="test_tool", template="tool_template")

        manifest = BootstrapManifest(
            description="Test manifest",
            assistants=[assistant],
            tools=[tool],
            metadata={"version": "1.0"},
            deployment={"strategy": "rolling"},
            environments={"dev": {"config": "value"}}
        )

        assert manifest.description == "Test manifest"
        assert len(manifest.assistants) == 1
        assert len(manifest.tools) == 1
        assert manifest.metadata == {"version": "1.0"}
        assert manifest.deployment == {"strategy": "rolling"}
        assert manifest.environments == {"dev": {"config": "value"}}


class TestBootstrapCheckpoint:
    """Test Bootstrap Checkpoint functionality."""

    def test_checkpoint_initialization(self):
        """Test checkpoint starts with validation phase."""
        checkpoint = BootstrapCheckpoint()
        assert checkpoint.current_phase == BootstrapPhase.VALIDATION
        assert checkpoint.completed_steps == []
        assert checkpoint.created_assistants == []
        assert checkpoint.created_tools == []
        assert checkpoint.created_squad is None

    def test_checkpoint_mark_step(self):
        """Test marking steps as completed."""
        checkpoint = BootstrapCheckpoint()
        checkpoint.mark_step("test_step")
        assert "test_step" in checkpoint.completed_steps

    def test_checkpoint_mark_phase(self):
        """Test marking phases as completed."""
        checkpoint = BootstrapCheckpoint()
        checkpoint.mark_phase(BootstrapPhase.TOOLS_CREATION)
        assert checkpoint.current_phase == BootstrapPhase.TOOLS_CREATION


@pytest.fixture
def temp_directories():
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create directory structure
        assistants_dir = temp_path / "assistants"
        squads_dir = temp_path / "squads"
        templates_dir = temp_path / "templates"
        shared_tools_dir = temp_path / "shared" / "tools"

        for dir_path in [assistants_dir, squads_dir, templates_dir, shared_tools_dir]:
            dir_path.mkdir(parents=True)

        # Create squad templates directory
        squad_templates_dir = templates_dir / "squads"
        squad_templates_dir.mkdir()

        # Create tool templates directory
        tool_templates_dir = templates_dir / "tools"
        tool_templates_dir.mkdir()

        yield {
            "assistants": str(assistants_dir),
            "squads": str(squads_dir),
            "templates": str(templates_dir),
            "shared_tools": str(shared_tools_dir),
            "temp_path": temp_path
        }


@pytest.fixture
def sample_manifest():
    """Create a sample manifest for testing."""
    return {
        "description": "Test dental clinic squad",
        "metadata": {
            "version": "1.0",
            "author": "Test Author"
        },
        "tools": [
            {
                "name": "appointment-booking",
                "template": "appointment_booking",
                "description": "Book appointments",
                "variables": {
                    "url": "https://api.test.com/appointments"
                }
            }
        ],
        "assistants": [
            {
                "name": "scheduler_bot",
                "template": "test_template",
                "role": "Handles scheduling",
                "required_tools": ["shared/tools/appointment-booking.yaml"],
                "config_overrides": {
                    "name": "Scheduler Assistant"
                }
            },
            {
                "name": "triage_assistant",
                "template": "test_template",
                "role": "Handles triage"
            }
        ],
        "deployment": {
            "strategy": "rolling",
            "rollback_on_failure": True
        },
        "environments": {
            "development": {
                "assistants": [
                    {
                        "name": "scheduler_bot",
                        "config_overrides": {
                            "model": {"model": "gpt-3.5-turbo"}
                        }
                    }
                ]
            },
            "production": {
                "assistants": [
                    {
                        "name": "scheduler_bot",
                        "config_overrides": {
                            "model": {"model": "gpt-4"}
                        }
                    }
                ]
            }
        }
    }


class TestBootstrapValidator:
    """Test Bootstrap Validator functionality."""

    def test_validator_initialization(self, temp_directories):
        """Test validator initialization."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )
        validator = BootstrapValidator(manager)
        assert validator.manager == manager

    def test_validate_dependencies_missing_assistant_template(self, temp_directories, sample_manifest):
        """Test validation fails for missing assistant template."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        manifest = manager._parse_manifest(sample_manifest)
        validator = BootstrapValidator(manager)

        issues = validator.validate_dependencies(manifest)
        assert any("Assistant template 'test_template' not found" in issue for issue in issues)

    def test_validate_environment_config_unknown_assistant(self, temp_directories, sample_manifest):
        """Test validation fails for unknown assistant in environment config."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Add unknown assistant to environment config
        sample_manifest["environments"]["development"]["assistants"].append({
            "name": "unknown_assistant",
            "config_overrides": {}
        })

        manifest = manager._parse_manifest(sample_manifest)
        validator = BootstrapValidator(manager)

        issues = validator.validate_environment_config(manifest, "development")
        assert any("Environment override for unknown assistant 'unknown_assistant'" in issue for issue in issues)

    def test_check_resource_conflicts_existing_squad(self, temp_directories, sample_manifest):
        """Test validation fails for existing squad when force=False."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Create existing squad directory
        existing_squad = Path(temp_directories["squads"]) / "test_squad"
        existing_squad.mkdir()

        manifest = manager._parse_manifest(sample_manifest)
        validator = BootstrapValidator(manager)

        conflicts = validator.check_resource_conflicts("test_squad", manifest, force=False)
        assert any("Squad 'test_squad' already exists" in conflict for conflict in conflicts)

    def test_check_resource_conflicts_force_mode(self, temp_directories, sample_manifest):
        """Test validation passes for existing resources when force=True."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Create existing squad directory
        existing_squad = Path(temp_directories["squads"]) / "test_squad"
        existing_squad.mkdir()

        manifest = manager._parse_manifest(sample_manifest)
        validator = BootstrapValidator(manager)

        conflicts = validator.check_resource_conflicts("test_squad", manifest, force=True)
        assert len(conflicts) == 0


class TestBootstrapManagerPhase1:
    """Test Phase 1: Core Bootstrap functionality."""

    def test_manager_initialization(self, temp_directories):
        """Test bootstrap manager initialization."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        assert str(manager.assistants_dir) == temp_directories["assistants"]
        assert str(manager.squads_dir) == temp_directories["squads"]
        assert str(manager.templates_dir) == temp_directories["templates"]
        assert str(manager.shared_tools_dir) == temp_directories["shared_tools"]
        assert manager.template_manager is not None
        assert manager.squad_template_manager is not None
        assert manager.tool_template_manager is not None
        assert manager.validator is not None

    def test_parse_manifest_valid(self, temp_directories, sample_manifest):
        """Test parsing a valid manifest."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        manifest = manager._parse_manifest(sample_manifest)

        assert manifest.description == "Test dental clinic squad"
        assert len(manifest.assistants) == 2
        assert len(manifest.tools) == 1
        assert manifest.metadata["version"] == "1.0"
        assert manifest.deployment["strategy"] == "rolling"
        assert "development" in manifest.environments
        assert "production" in manifest.environments

    def test_parse_manifest_missing_description(self, temp_directories):
        """Test parsing manifest fails without description."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        invalid_manifest = {"assistants": []}

        with pytest.raises(BootstrapValidationError, match="Manifest must include a 'description' field"):
            manager._parse_manifest(invalid_manifest)

    def test_parse_manifest_missing_assistants(self, temp_directories):
        """Test parsing manifest fails without assistants."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        invalid_manifest = {"description": "Test"}

        with pytest.raises(BootstrapValidationError, match="Manifest must define at least one assistant"):
            manager._parse_manifest(invalid_manifest)

    def test_validate_bootstrap_missing_template(self, temp_directories):
        """Test validation fails for missing squad template."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        with pytest.raises(BootstrapValidationError, match="Squad template 'missing_template' not found"):
            manager._validate_bootstrap("test_squad", "missing_template", force=False)

    def test_validate_bootstrap_missing_manifest(self, temp_directories):
        """Test validation fails for missing manifest.yaml."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Create squad template directory without manifest
        template_dir = Path(temp_directories["templates"]) / "squads" / "test_template"
        template_dir.mkdir(parents=True)

        with pytest.raises(BootstrapValidationError, match="No manifest.yaml found"):
            manager._validate_bootstrap("test_squad", "test_template", force=False)

    def test_preview_bootstrap(self, temp_directories, sample_manifest, capsys):
        """Test preview functionality."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        manifest = manager._parse_manifest(sample_manifest)
        manager._preview_bootstrap("test_squad", manifest)

        captured = capsys.readouterr()
        assert "Bootstrap Preview for Squad: test_squad" in captured.out
        assert "Test dental clinic squad" in captured.out
        assert "Tools to create (1)" in captured.out
        assert "Assistants to create (2)" in captured.out


class TestBootstrapManagerPhase2:
    """Test Phase 2: Enhanced features (validation, rollback)."""

    def test_list_bootstrap_templates(self, temp_directories, sample_manifest):
        """Test listing bootstrap-ready templates."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Create a template with manifest
        template_dir = Path(temp_directories["templates"]) / "squads" / "test_template"
        template_dir.mkdir(parents=True)

        manifest_file = template_dir / "manifest.yaml"
        with open(manifest_file, 'w') as f:
            yaml.dump(sample_manifest, f)

        # Mock validate_manifest to return valid result
        with patch.object(manager, 'validate_manifest') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "description": "Test template",
                "assistants": 2,
                "tools": 1
            }

            templates = manager.list_bootstrap_templates()

        assert len(templates) == 1
        assert templates[0]["name"] == "test_template"
        assert templates[0]["has_manifest"] is True
        assert templates[0]["bootstrap_ready"] is True

    def test_validate_manifest_only(self, temp_directories, sample_manifest):
        """Test manifest validation without execution."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Create template with manifest
        template_dir = Path(temp_directories["templates"]) / "squads" / "test_template"
        template_dir.mkdir(parents=True)

        manifest_file = template_dir / "manifest.yaml"
        with open(manifest_file, 'w') as f:
            yaml.dump(sample_manifest, f)

        # Mock the _validate_bootstrap method to skip dependency checks
        with patch.object(manager, '_validate_bootstrap') as mock_validate:
            mock_validate.return_value = manager._parse_manifest(sample_manifest)

            result = manager.validate_manifest("test_template")

        assert result["valid"] is True
        assert result["description"] == "Test dental clinic squad"
        assert result["assistants"] == 2
        assert result["tools"] == 1

    @patch('vapi_manager.core.bootstrap_manager.console')
    def test_rollback_bootstrap(self, mock_console, temp_directories):
        """Test rollback functionality."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Create checkpoint with created resources
        checkpoint = BootstrapCheckpoint()
        checkpoint.created_squad = "test_squad"
        checkpoint.created_assistants = ["test_assistant"]
        checkpoint.created_tools = ["test_tool"]

        # Create the resources to be removed
        squad_dir = Path(temp_directories["squads"]) / "test_squad"
        squad_dir.mkdir()

        assistant_dir = Path(temp_directories["assistants"]) / "test_assistant"
        assistant_dir.mkdir()

        tool_file = Path(temp_directories["shared_tools"]) / "test_tool.yaml"
        tool_file.touch()

        # Perform rollback
        manager._rollback_bootstrap(checkpoint)

        # Verify resources were removed
        assert not squad_dir.exists()
        assert not assistant_dir.exists()
        assert not tool_file.exists()

    @patch('vapi_manager.core.bootstrap_manager.console')
    def test_rollback_squad_command(self, mock_console, temp_directories):
        """Test rollback squad command."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Create existing squad
        squad_dir = Path(temp_directories["squads"]) / "test_squad"
        squad_dir.mkdir()

        # Create assistants that might be related
        for assistant_name in ["scheduler_bot", "triage_assistant"]:
            assistant_dir = Path(temp_directories["assistants"]) / assistant_name
            assistant_dir.mkdir()

        result = manager.rollback_squad("test_squad")

        assert result is True
        assert not squad_dir.exists()

    @patch('vapi_manager.core.bootstrap_manager.console')
    def test_update_existing_squad(self, mock_console, temp_directories, sample_manifest):
        """Test updating existing squad."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Create existing squad
        squad_dir = Path(temp_directories["squads"]) / "test_squad"
        squad_dir.mkdir()

        # Create template with manifest
        template_dir = Path(temp_directories["templates"]) / "squads" / "test_template"
        template_dir.mkdir(parents=True)

        manifest_file = template_dir / "manifest.yaml"
        with open(manifest_file, 'w') as f:
            yaml.dump(sample_manifest, f)

        # Mock validation
        with patch.object(manager, '_validate_bootstrap') as mock_validate:
            mock_validate.return_value = manager._parse_manifest(sample_manifest)

            result = manager.update_existing_squad("test_squad", "test_template", "development")

        assert result is True


class TestBootstrapManagerPhase3:
    """Test Phase 3: Enterprise features (pipelines, health checks, promotion)."""

    @pytest.mark.asyncio
    async def test_deploy_pipeline_rolling_strategy(self, temp_directories):
        """Test deployment pipeline with rolling strategy."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Create squad for deployment
        squad_dir = Path(temp_directories["squads"]) / "test_squad"
        squad_dir.mkdir()

        environments = ["development", "staging", "production"]
        strategy = BootstrapStrategy.ROLLING

        # Mock random to always pass health checks
        with patch('random.random', return_value=0.2):  # > 0.1 threshold
            result = await manager.deploy_pipeline(
                squad_name="test_squad",
                environments=environments,
                strategy=strategy,
                approval_required=False
            )

        assert result["squad_name"] == "test_squad"
        assert result["strategy"] == "rolling"
        assert result["environments"] == environments
        assert len(result["stages"]) == 3
        assert result["overall_success"] is True

    @pytest.mark.asyncio
    async def test_deploy_pipeline_blue_green_strategy(self, temp_directories):
        """Test deployment pipeline with blue-green strategy."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Create squad for deployment
        squad_dir = Path(temp_directories["squads"]) / "test_squad"
        squad_dir.mkdir()

        environments = ["staging", "production"]
        strategy = BootstrapStrategy.BLUE_GREEN

        # Mock random to always pass health checks
        with patch('random.random', return_value=0.2):  # > 0.1 threshold
            result = await manager.deploy_pipeline(
                squad_name="test_squad",
                environments=environments,
                strategy=strategy,
                approval_required=False
            )

        assert result["strategy"] == "blue_green"
        assert result["overall_success"] is True

    @pytest.mark.asyncio
    async def test_health_check_squad(self, temp_directories):
        """Test squad health check functionality."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Mock random to always pass health checks
        with patch('random.random', return_value=0.2):  # > 0.1 threshold
            health_status = await manager.health_check_squad("test_squad", "development")

        assert health_status is True

    @pytest.mark.asyncio
    async def test_health_check_squad_failures(self, temp_directories):
        """Test squad health check with failures."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Mock random to always fail health checks
        with patch('random.random', return_value=0.05):  # < 0.1 threshold
            health_status = await manager.health_check_squad("test_squad", "development")

        assert health_status is False

    def test_get_deployment_status(self, temp_directories):
        """Test getting deployment status."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Create squad
        squad_dir = Path(temp_directories["squads"]) / "test_squad"
        squad_dir.mkdir()

        status = manager.get_deployment_status("test_squad")

        assert status["squad_name"] == "test_squad"
        assert "last_updated" in status
        assert "environments" in status
        assert len(status["environments"]) == 3  # dev, staging, prod

        # Check development environment is marked as deployed
        dev_status = status["environments"]["development"]
        assert dev_status["deployed"] is True
        assert dev_status["health"] == "healthy"
        assert "assistants" in dev_status

    def test_get_deployment_status_nonexistent_squad(self, temp_directories):
        """Test getting deployment status for nonexistent squad."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        status = manager.get_deployment_status("nonexistent_squad")

        assert status["squad_name"] == "nonexistent_squad"

        # All environments should show not found
        for env_status in status["environments"].values():
            assert env_status["deployed"] is False
            assert env_status["health"] == "not_found"

    @pytest.mark.asyncio
    async def test_promote_squad_success(self, temp_directories):
        """Test successful squad promotion."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Create squad
        squad_dir = Path(temp_directories["squads"]) / "test_squad"
        squad_dir.mkdir()

        # Mock health checks to always pass
        with patch('random.random', return_value=0.2):
            success = await manager.promote_squad(
                squad_name="test_squad",
                from_environment="development",
                to_environment="staging",
                run_tests=True,
                approval_required=False
            )

        assert success is True

    @pytest.mark.asyncio
    async def test_promote_squad_health_check_failure(self, temp_directories):
        """Test squad promotion fails on health check."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Create squad
        squad_dir = Path(temp_directories["squads"]) / "test_squad"
        squad_dir.mkdir()

        # Mock health checks to fail for source environment
        def mock_health_check(squad_name, environment):
            if environment == "development":
                return False  # Source environment unhealthy
            return True

        with patch.object(manager, 'health_check_squad', side_effect=mock_health_check):
            success = await manager.promote_squad(
                squad_name="test_squad",
                from_environment="development",
                to_environment="staging",
                run_tests=True,
                approval_required=False
            )

        assert success is False

    @pytest.mark.asyncio
    async def test_run_promotion_tests(self, temp_directories):
        """Test promotion test execution."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        test_success = await manager._run_promotion_tests("test_squad", "development")
        assert test_success is True


class TestBootstrapIntegration:
    """Integration tests for bootstrap functionality."""

    @pytest.mark.asyncio
    async def test_full_bootstrap_dry_run(self, temp_directories, sample_manifest):
        """Test complete bootstrap workflow in dry-run mode."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Create template with manifest
        template_dir = Path(temp_directories["templates"]) / "squads" / "test_template"
        template_dir.mkdir(parents=True)

        manifest_file = template_dir / "manifest.yaml"
        with open(manifest_file, 'w') as f:
            yaml.dump(sample_manifest, f)

        # Create assistant template
        assistants_templates_dir = Path(temp_directories["templates"]) / "assistants"
        assistants_templates_dir.mkdir(parents=True, exist_ok=True)
        assistant_template_dir = assistants_templates_dir / "test_template"
        assistant_template_dir.mkdir()

        # Create tool template
        tool_template_dir = Path(temp_directories["templates"]) / "tools" / "appointment_booking"
        tool_template_dir.mkdir(parents=True)
        template_file = tool_template_dir / "template.yaml"
        template_file.write_text("name: {{ name }}\ndescription: Test tool")

        # Mock managers to avoid actual file operations
        with patch.object(manager.template_manager, 'template_exists', return_value=True), \
             patch.object(manager.tool_template_manager, 'template_exists', return_value=True), \
             patch.object(manager.validator, 'validate_dependencies', return_value=[]), \
             patch.object(manager.validator, 'validate_environment_config', return_value=[]), \
             patch.object(manager.validator, 'check_resource_conflicts', return_value=[]):

            checkpoint = manager.bootstrap_squad(
                squad_name="test_squad",
                template_name="test_template",
                deploy=False,
                dry_run=True,
                force=False
            )

        assert checkpoint.current_phase == BootstrapPhase.VALIDATION

    @pytest.mark.asyncio
    async def test_bootstrap_with_rollback_on_failure(self, temp_directories, sample_manifest):
        """Test bootstrap with rollback on failure."""
        manager = BootstrapManager(
            assistants_dir=temp_directories["assistants"],
            squads_dir=temp_directories["squads"],
            templates_dir=temp_directories["templates"],
            shared_tools_dir=temp_directories["shared_tools"]
        )

        # Create template with manifest
        template_dir = Path(temp_directories["templates"]) / "squads" / "test_template"
        template_dir.mkdir(parents=True)

        manifest_file = template_dir / "manifest.yaml"
        with open(manifest_file, 'w') as f:
            yaml.dump(sample_manifest, f)

        # Mock validation to pass but tool creation to fail
        with patch.object(manager.validator, 'validate_dependencies', return_value=[]), \
             patch.object(manager.validator, 'validate_environment_config', return_value=[]), \
             patch.object(manager.validator, 'check_resource_conflicts', return_value=[]), \
             patch.object(manager, '_create_tools', side_effect=BootstrapExecutionError("Tool creation failed")), \
             patch.object(manager, '_rollback_bootstrap') as mock_rollback:

            with pytest.raises(BootstrapExecutionError):
                manager.bootstrap_squad(
                    squad_name="test_squad",
                    template_name="test_template",
                    deploy=False,
                    dry_run=False,
                    force=False,
                    rollback_on_failure=True
                )

        # Verify rollback was called
        mock_rollback.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])