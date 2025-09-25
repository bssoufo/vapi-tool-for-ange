"""
Comprehensive unit tests for SquadTemplateCreator

Tests the builder pattern implementation for creating squad templates with manifests.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from vapi_manager.core.squad_template_creator import (
    SquadTemplateCreator,
    SquadTemplateCreatorError
)
from vapi_manager.core.bootstrap_manager import BootstrapAssistant, BootstrapTool


class TestSquadTemplateCreator:
    """Test cases for SquadTemplateCreator builder pattern."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def creator(self, temp_output_dir):
        """Create a SquadTemplateCreator instance for testing."""
        creator = SquadTemplateCreator("test_template")
        creator.set_output_directory(str(temp_output_dir))
        return creator

    def test_creator_initialization(self):
        """Test SquadTemplateCreator initialization."""
        creator = SquadTemplateCreator("test_template")

        assert creator.template_name == "test_template"
        assert creator.manifest.description == ""
        assert creator.manifest.assistants == []
        assert creator.manifest.tools is None
        assert creator._output_dir == Path("templates/squads")

    def test_with_description(self, creator):
        """Test setting template description."""
        result = creator.with_description("A test template")

        assert result is creator  # Test fluent interface
        assert creator.manifest.description == "A test template"

    def test_with_metadata(self, creator):
        """Test adding metadata."""
        result = creator.with_metadata(version="1.0", author="Test")

        assert result is creator
        assert creator.manifest.metadata == {"version": "1.0", "author": "Test"}

        # Test adding more metadata
        creator.with_metadata(category="test")
        assert creator.manifest.metadata == {
            "version": "1.0",
            "author": "Test",
            "category": "test"
        }

    def test_add_assistant_basic(self, creator):
        """Test adding a basic assistant."""
        result = creator.add_assistant("test_assistant", "test_template")

        assert result is creator
        assert len(creator.manifest.assistants) == 1

        assistant = creator.manifest.assistants[0]
        assert assistant.name == "test_assistant"
        assert assistant.template == "test_template"
        assert assistant.role is None
        assert assistant.required_tools is None

        # Check members config
        assert len(creator.members_config["members"]) == 1
        member = creator.members_config["members"][0]
        assert member["assistant_name"] == "test_assistant"
        assert member["priority"] == 2

    def test_add_assistant_with_options(self, creator):
        """Test adding assistant with all options."""
        tools = ["shared/tools/tool1.yaml", "shared/tools/tool2.yaml"]
        config_overrides = {"model": {"temperature": 0.5}}

        creator.add_assistant(
            name="advanced_assistant",
            template="advanced_template",
            role="Advanced AI assistant",
            priority=1,
            required_tools=tools,
            config_overrides=config_overrides
        )

        assistant = creator.manifest.assistants[0]
        assert assistant.name == "advanced_assistant"
        assert assistant.template == "advanced_template"
        assert assistant.role == "Advanced AI assistant"
        assert assistant.required_tools == tools
        assert assistant.config_overrides == config_overrides

        member = creator.members_config["members"][0]
        assert member["priority"] == 1
        assert member["role"] == "Advanced AI assistant"

    def test_add_multiple_assistants(self, creator):
        """Test adding multiple assistants."""
        creator.add_assistant("assistant1", "template1", "Role 1")
        creator.add_assistant("assistant2", "template2", "Role 2")

        assert len(creator.manifest.assistants) == 2
        assert len(creator.members_config["members"]) == 2

        assert creator.manifest.assistants[0].name == "assistant1"
        assert creator.manifest.assistants[1].name == "assistant2"

    def test_add_tool_basic(self, creator):
        """Test adding a basic tool."""
        result = creator.add_tool("test_tool", "webhook_template")

        assert result is creator
        assert len(creator.manifest.tools) == 1

        tool = creator.manifest.tools[0]
        assert tool.name == "test_tool"
        assert tool.template == "webhook_template"
        assert tool.variables == {}
        assert tool.description is None

    def test_add_tool_with_variables(self, creator):
        """Test adding tool with variables and description."""
        variables = {"url": "https://api.example.com", "api_key": "test_key"}

        creator.add_tool(
            name="api_tool",
            template="api_template",
            description="API integration tool",
            **variables
        )

        tool = creator.manifest.tools[0]
        assert tool.name == "api_tool"
        assert tool.template == "api_template"
        assert tool.variables == variables
        assert tool.description == "API integration tool"

    def test_add_multiple_tools(self, creator):
        """Test adding multiple tools."""
        creator.add_tool("tool1", "template1", url="http://api1.com")
        creator.add_tool("tool2", "template2", url="http://api2.com")

        assert len(creator.manifest.tools) == 2
        assert creator.manifest.tools[0].name == "tool1"
        assert creator.manifest.tools[1].name == "tool2"

    def test_with_deployment_config(self, creator):
        """Test setting deployment configuration."""
        validation_steps = ["check_api", "validate_config"]

        result = creator.with_deployment_config(
            strategy="blue_green",
            rollback_on_failure=False,
            health_checks=True,
            validation_steps=validation_steps
        )

        assert result is creator
        assert creator.manifest.deployment == {
            "strategy": "blue_green",
            "rollback_on_failure": False,
            "health_checks": True,
            "validation_steps": validation_steps
        }

    def test_add_environment(self, creator):
        """Test adding environment configuration."""
        assistant_overrides = [{"name": "test_assistant", "config": {"model": "gpt-4"}}]
        tool_overrides = [{"name": "test_tool", "variables": {"url": "https://prod.api.com"}}]

        result = creator.add_environment(
            "production",
            assistant_overrides=assistant_overrides,
            tool_overrides=tool_overrides
        )

        assert result is creator
        assert "production" in creator.manifest.environments
        env_config = creator.manifest.environments["production"]
        assert env_config["assistants"] == assistant_overrides
        assert env_config["tools"] == tool_overrides

    def test_add_multiple_environments(self, creator):
        """Test adding multiple environments."""
        creator.add_environment("development")
        creator.add_environment("staging")
        creator.add_environment("production")

        assert len(creator.manifest.environments) == 3
        assert "development" in creator.manifest.environments
        assert "staging" in creator.manifest.environments
        assert "production" in creator.manifest.environments

    def test_add_routing_rule(self, creator):
        """Test adding routing rules."""
        triggers = [{"type": "intent", "intents": ["greeting", "help"]}]

        result = creator.add_routing_rule(
            rule_name="greeting_rule",
            rule_type="intent",
            priority=1,
            triggers=triggers,
            destination="greeting_assistant",
            description="Route greetings to greeting assistant"
        )

        assert result is creator
        assert "intent_rules" in creator.routing_rules
        assert len(creator.routing_rules["intent_rules"]) == 1

        rule = creator.routing_rules["intent_rules"][0]
        assert rule["name"] == "greeting_rule"
        assert rule["priority"] == 1
        assert rule["triggers"] == triggers
        assert rule["action"]["destination"] == "greeting_assistant"
        assert rule["description"] == "Route greetings to greeting assistant"

    def test_with_squad_config(self, creator):
        """Test adding squad configuration."""
        config = {"timeout": 30, "max_members": 5}

        result = creator.with_squad_config(**config)

        assert result is creator
        assert creator.squad_config == config

    def test_set_output_directory(self, creator):
        """Test setting custom output directory."""
        custom_dir = "/custom/templates"

        result = creator.set_output_directory(custom_dir)

        assert result is creator
        assert creator._output_dir == Path(custom_dir)

    def test_validate_empty_template(self, creator):
        """Test validation fails for empty template."""
        errors = creator.validate()

        assert len(errors) >= 2
        assert "Template description is required" in errors
        assert "At least one assistant is required" in errors

    def test_validate_missing_description(self, creator):
        """Test validation fails for missing description."""
        creator.add_assistant("test", "template")

        errors = creator.validate()

        assert "Template description is required" in errors

    def test_validate_missing_assistants(self, creator):
        """Test validation fails for missing assistants."""
        creator.with_description("Test template")

        errors = creator.validate()

        assert "At least one assistant is required" in errors

    def test_validate_tool_reference_mismatch(self, creator):
        """Test validation fails for missing tool references."""
        creator.with_description("Test template")
        creator.add_assistant(
            "test_assistant",
            "template",
            required_tools=["shared/tools/missing_tool.yaml"]
        )

        errors = creator.validate()

        assert any("references unknown tool 'missing_tool'" in error for error in errors)

    def test_validate_success(self, creator):
        """Test successful validation."""
        creator.with_description("Test template")
        creator.add_assistant("test_assistant", "template")
        creator.add_tool("test_tool", "template")

        errors = creator.validate()

        assert errors == []

    def test_validate_with_matching_tools(self, creator):
        """Test validation passes when tools match references."""
        creator.with_description("Test template")
        creator.add_tool("api_tool", "webhook")
        creator.add_assistant(
            "test_assistant",
            "template",
            required_tools=["shared/tools/api_tool.yaml"]
        )

        errors = creator.validate()

        assert errors == []

    def test_create_validation_failure(self, creator):
        """Test create fails with validation errors."""
        with pytest.raises(SquadTemplateCreatorError, match="Validation failed"):
            creator.create()

    def test_create_existing_template_no_force(self, creator, temp_output_dir):
        """Test create fails when template exists without force."""
        # Create directory to simulate existing template
        template_dir = temp_output_dir / "test_template"
        template_dir.mkdir()

        creator.with_description("Test").add_assistant("test", "template")

        with pytest.raises(SquadTemplateCreatorError, match="already exists"):
            creator.create()

    def test_create_success(self, creator, temp_output_dir):
        """Test successful template creation."""
        creator.with_description("Test template for unit testing")
        creator.with_metadata(version="1.0", author="Test Suite")
        creator.add_assistant("test_assistant", "test_template", "Test role")
        creator.add_tool("test_tool", "webhook", url="https://test.com")
        creator.with_deployment_config(strategy="rolling")
        creator.add_environment("development")
        creator.add_routing_rule(
            "test_rule", "intent", 1,
            [{"type": "intent", "intents": ["test"]}],
            "test_assistant"
        )

        template_path = creator.create()

        # Verify template was created
        assert template_path.exists()
        assert template_path.name == "test_template"

        # Verify files were created
        assert (template_path / "manifest.yaml").exists()
        assert (template_path / "squad.yaml").exists()
        assert (template_path / "members.yaml").exists()
        assert (template_path / "routing" / "destinations.yaml").exists()

    def test_create_force_overwrite(self, creator, temp_output_dir):
        """Test force overwrite of existing template."""
        # Create existing template
        template_dir = temp_output_dir / "test_template"
        template_dir.mkdir()
        (template_dir / "old_file.txt").write_text("old content")

        creator.with_description("Test").add_assistant("test", "template")

        template_path = creator.create(force=True)

        assert template_path.exists()
        assert not (template_path / "old_file.txt").exists()  # Old file should be gone
        assert (template_path / "manifest.yaml").exists()  # New files should exist

    def test_created_manifest_content(self, creator, temp_output_dir):
        """Test the content of created manifest.yaml file."""
        creator.with_description("Test template")
        creator.with_metadata(version="1.0")
        creator.add_assistant("test_assistant", "test_template", "Test role")
        creator.add_tool("test_tool", "webhook", url="https://test.com")
        creator.with_deployment_config(strategy="rolling")
        creator.add_environment("development")

        template_path = creator.create()
        manifest_file = template_path / "manifest.yaml"

        with open(manifest_file, 'r') as f:
            manifest_data = yaml.safe_load(f)

        assert manifest_data["description"] == "Test template"
        assert manifest_data["metadata"]["version"] == "1.0"
        assert len(manifest_data["assistants"]) == 1
        assert len(manifest_data["tools"]) == 1
        assert manifest_data["deployment"]["strategy"] == "rolling"
        assert "development" in manifest_data["environments"]

    def test_created_squad_config_content(self, creator, temp_output_dir):
        """Test the content of created squad.yaml file."""
        creator.with_description("Test template")
        creator.add_assistant("test", "template")
        creator.with_squad_config(timeout=30, max_retries=3)

        template_path = creator.create()
        squad_file = template_path / "squad.yaml"

        with open(squad_file, 'r') as f:
            squad_data = yaml.safe_load(f)

        assert squad_data["name"] == "{{squad_name}}"
        assert "{{description|Test template}}" in squad_data["description"]
        assert squad_data["timeout"] == 30
        assert squad_data["max_retries"] == 3

    def test_created_members_config_content(self, creator, temp_output_dir):
        """Test the content of created members.yaml file."""
        creator.with_description("Test template")
        creator.add_assistant("assistant1", "template1", "Role 1", priority=1)
        creator.add_assistant("assistant2", "template2", "Role 2", priority=2)

        template_path = creator.create()
        members_file = template_path / "members.yaml"

        with open(members_file, 'r') as f:
            members_data = yaml.safe_load(f)

        assert len(members_data["members"]) == 2
        assert members_data["members"][0]["assistant_name"] == "assistant1"
        assert members_data["members"][0]["priority"] == 1
        assert members_data["members"][1]["assistant_name"] == "assistant2"
        assert members_data["members"][1]["priority"] == 2

    def test_preview_functionality(self, creator):
        """Test template preview functionality."""
        creator.with_description("Test template for preview")
        creator.add_assistant("assistant1", "template1", "Role 1")
        creator.add_assistant("assistant2", "template2", "Role 2")
        creator.add_tool("tool1", "webhook")
        creator.add_environment("development")
        creator.add_environment("production")
        creator.add_routing_rule("rule1", "intent", 1, [], "destination")

        preview = creator.preview()

        assert "Squad Template: test_template" in preview
        assert "Test template for preview" in preview
        assert "Tools (1):" in preview
        assert "Assistants (2):" in preview
        assert "assistant1 (template: template1)" in preview
        assert "Role: Role 1" in preview
        assert "Environments: development, production" in preview
        assert "Routing Rules: 1" in preview

    def test_fluent_interface_chaining(self, creator):
        """Test that all methods support fluent interface chaining."""
        result = (creator
                 .with_description("Chained template")
                 .with_metadata(version="1.0")
                 .add_assistant("assistant1", "template1")
                 .add_tool("tool1", "webhook")
                 .with_deployment_config()
                 .add_environment("development")
                 .add_routing_rule("rule1", "intent", 1, [], "dest")
                 .with_squad_config(timeout=30)
                 .set_output_directory("/tmp"))

        assert result is creator
        assert creator.manifest.description == "Chained template"
        assert len(creator.manifest.assistants) == 1
        assert len(creator.manifest.tools) == 1


class TestSquadTemplateCreatorIntegration:
    """Integration tests for SquadTemplateCreator with real file system."""

    def test_end_to_end_real_estate_template(self):
        """Test creating a complete real estate squad template."""
        with tempfile.TemporaryDirectory() as temp_dir:
            creator = SquadTemplateCreator("real_estate_squad")
            creator.set_output_directory(temp_dir)

            # Build a complete real estate template
            template_path = (creator
                .with_description("Complete real estate reception system with lead qualification, property info, and scheduling")
                .with_metadata(
                    version="1.0",
                    author="VAPI Manager",
                    category="real_estate",
                    industry="real_estate"
                )
                .add_tool("crm-lookup", "data_lookup",
                         url="https://api.realestatecrm.com/clients",
                         api_key="${CRM_API_KEY}")
                .add_tool("property-search", "data_lookup",
                         url="https://api.mls.com/properties",
                         api_key="${MLS_API_KEY}")
                .add_tool("calendar-booking", "appointment_booking",
                         calendar_url="https://api.calendar.com/book",
                         time_zone="America/New_York")
                .add_assistant("lead_qualifier", "real_estate_lead_qualifier",
                              "Handles initial lead qualification and routing",
                              priority=1,
                              required_tools=["shared/tools/crm-lookup.yaml"])
                .add_assistant("property_info", "real_estate_property_info",
                              "Provides detailed property information and answers",
                              priority=2,
                              required_tools=["shared/tools/property-search.yaml"])
                .add_assistant("scheduling_assistant", "real_estate_scheduler",
                              "Coordinates and books property viewings",
                              priority=2,
                              required_tools=["shared/tools/calendar-booking.yaml"])
                .with_deployment_config(
                    strategy="rolling",
                    rollback_on_failure=True,
                    health_checks=True,
                    validation_steps=["crm_connectivity", "mls_sync", "calendar_access"]
                )
                .add_environment("development",
                    tool_overrides=[
                        {"name": "crm-lookup", "variables": {"url": "https://dev-api.realestatecrm.com/clients"}},
                        {"name": "property-search", "variables": {"url": "https://dev-api.mls.com/properties"}}
                    ])
                .add_environment("production",
                    assistant_overrides=[
                        {"name": "lead_qualifier", "config_overrides": {"model": {"model": "gpt-4", "temperature": 0.5}}}
                    ])
                .add_routing_rule("hot_leads", "priority", 1,
                    [{"type": "keyword", "keywords": ["urgent", "sell now", "buy immediately"]}],
                    "human_agent",
                    "Route high-priority leads to human agents")
                .add_routing_rule("property_inquiries", "intent", 2,
                    [{"type": "intent", "intents": ["property_details", "listing_info"]}],
                    "property_info")
                .add_routing_rule("scheduling_requests", "intent", 2,
                    [{"type": "intent", "intents": ["schedule_showing", "book_viewing"]}],
                    "scheduling_assistant")
                .with_squad_config(
                    business_hours="9:00-18:00",
                    time_zone="America/New_York",
                    escalation_timeout=300
                )
                .create())

            # Verify the complete template was created
            assert template_path.exists()
            assert (template_path / "manifest.yaml").exists()
            assert (template_path / "squad.yaml").exists()
            assert (template_path / "members.yaml").exists()
            assert (template_path / "routing" / "destinations.yaml").exists()

            # Verify manifest content
            with open(template_path / "manifest.yaml", 'r') as f:
                manifest = yaml.safe_load(f)

            assert len(manifest["tools"]) == 3
            assert len(manifest["assistants"]) == 3
            assert len(manifest["environments"]) == 2
            assert manifest["deployment"]["validation_steps"] == ["crm_connectivity", "mls_sync", "calendar_access"]



if __name__ == '__main__':
    pytest.main([__file__, "-v"])