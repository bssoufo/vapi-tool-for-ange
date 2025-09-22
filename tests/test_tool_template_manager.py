"""Unit tests for ToolTemplateManager."""

import unittest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from vapi_manager.core.tool_template_manager import (
    ToolTemplateManager,
    ToolTemplateValidationError
)


class TestToolTemplateManager(unittest.TestCase):
    """Test cases for ToolTemplateManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = Path(self.temp_dir) / "templates" / "tools"
        self.output_dir = Path(self.temp_dir) / "shared" / "tools"

        # Create directories
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.manager = ToolTemplateManager(
            templates_dir=str(self.templates_dir),
            output_dir=str(self.output_dir)
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_list_templates_empty(self):
        """Test listing templates when none exist."""
        templates = self.manager.list_templates()
        self.assertEqual(templates, [])

    def test_list_templates_with_files(self):
        """Test listing templates with some files."""
        # Create test templates
        (self.templates_dir / "basic_webhook.yaml").write_text("name: test")
        (self.templates_dir / "data_lookup.yaml").write_text("name: test2")
        (self.templates_dir / "not_yaml.txt").write_text("not a yaml file")

        templates = self.manager.list_templates()
        self.assertEqual(sorted(templates), ['basic_webhook', 'data_lookup'])

    def test_template_exists(self):
        """Test checking if template exists."""
        self.assertFalse(self.manager.template_exists("nonexistent"))

        (self.templates_dir / "test_template.yaml").write_text("name: test")
        self.assertTrue(self.manager.template_exists("test_template"))

    def test_tool_exists(self):
        """Test checking if tool exists."""
        self.assertFalse(self.manager.tool_exists("nonexistent"))

        (self.output_dir / "test_tool.yaml").write_text("name: test")
        self.assertTrue(self.manager.tool_exists("test_tool"))

    def test_validate_tool_name(self):
        """Test tool name validation."""
        # Valid names
        self.assertTrue(self.manager._validate_tool_name("valid_name"))
        self.assertTrue(self.manager._validate_tool_name("valid-name"))
        self.assertTrue(self.manager._validate_tool_name("validName123"))

        # Invalid names
        self.assertFalse(self.manager._validate_tool_name(""))
        self.assertFalse(self.manager._validate_tool_name("invalid name"))
        self.assertFalse(self.manager._validate_tool_name("invalid@name"))
        self.assertFalse(self.manager._validate_tool_name("invalid.name"))

    def test_prepare_template_variables(self):
        """Test template variable preparation."""
        variables = self.manager._prepare_template_variables("test-tool", {
            "description": "Test description",
            "url": "https://example.com"
        })

        expected = {
            "tool_name": "test-tool",
            "tool_name_upper": "TEST_TOOL",
            "tool_name_camel": "testTool",
            "description": "Test description",
            "url": "https://example.com"
        }

        self.assertEqual(variables, expected)

    def test_to_camel_case(self):
        """Test camelCase conversion."""
        self.assertEqual(self.manager._to_camel_case("test_name"), "testName")
        self.assertEqual(self.manager._to_camel_case("test-name"), "testName")
        self.assertEqual(self.manager._to_camel_case("test_name_long"), "testNameLong")
        self.assertEqual(self.manager._to_camel_case("simple"), "simple")

    def test_validate_generated_tool_valid(self):
        """Test validation of a valid tool configuration."""
        valid_tool = """
name: "testTool"
description: "A test tool"
server:
  url: "https://example.com/webhook"
parameters:
  type: object
  required:
    - id
  properties:
    id:
      type: string
      description: "The ID"
"""
        # Should not raise an exception
        result = self.manager._validate_generated_tool(valid_tool, "testTool")
        self.assertIsInstance(result, dict)
        self.assertEqual(result['name'], 'testTool')

    def test_validate_generated_tool_missing_fields(self):
        """Test validation with missing required fields."""
        # Missing name
        invalid_tool = """
description: "A test tool"
parameters:
  type: object
"""
        with self.assertRaises(ToolTemplateValidationError) as cm:
            self.manager._validate_generated_tool(invalid_tool, "testTool")
        self.assertIn("Missing required field: name", str(cm.exception))

        # Missing description
        invalid_tool = """
name: "testTool"
parameters:
  type: object
"""
        with self.assertRaises(ToolTemplateValidationError) as cm:
            self.manager._validate_generated_tool(invalid_tool, "testTool")
        self.assertIn("Missing required field: description", str(cm.exception))

    def test_validate_generated_tool_invalid_url(self):
        """Test validation with invalid server URL."""
        invalid_tool = """
name: "testTool"
description: "A test tool"
server:
  url: "invalid-url"
parameters:
  type: object
  properties: {}
"""
        with self.assertRaises(ToolTemplateValidationError) as cm:
            self.manager._validate_generated_tool(invalid_tool, "testTool")
        self.assertIn("Server URL must start with", str(cm.exception))

    def test_validate_generated_tool_invalid_yaml(self):
        """Test validation with invalid YAML."""
        invalid_yaml = """
name: "testTool"
description: "A test tool"
parameters:
  - this is not a valid yaml structure
    missing colon
"""
        with self.assertRaises(ToolTemplateValidationError) as cm:
            self.manager._validate_generated_tool(invalid_yaml, "testTool")
        # The error message might vary depending on what validates first
        self.assertTrue("Invalid YAML" in str(cm.exception) or "Parameters must be an object" in str(cm.exception))

    def test_create_tool_success(self):
        """Test successful tool creation."""
        # Create a simple template
        template_content = """
name: "{{tool_name}}"
description: "{{description or 'A tool for ' + tool_name}}"
server:
  url: "{{url or 'https://example.com/webhook'}}"
parameters:
  type: object
  required:
    - id
  properties:
    id:
      type: string
      description: "The ID"
"""
        (self.templates_dir / "simple.yaml").write_text(template_content)

        # Create tool
        success = self.manager.create_tool(
            tool_name="my-test-tool",
            template_name="simple",
            variables={"description": "My test tool"}
        )

        self.assertTrue(success)

        # Check that file was created
        tool_file = self.output_dir / "my-test-tool.yaml"
        self.assertTrue(tool_file.exists())

        # Check content
        with open(tool_file, 'r') as f:
            content = yaml.safe_load(f)

        self.assertEqual(content['name'], 'my-test-tool')
        self.assertEqual(content['description'], 'My test tool')
        self.assertEqual(content['server']['url'], 'https://example.com/webhook')

    def test_create_tool_invalid_name(self):
        """Test tool creation with invalid name."""
        success = self.manager.create_tool(
            tool_name="invalid name",
            template_name="basic_webhook"
        )
        self.assertFalse(success)

    def test_create_tool_nonexistent_template(self):
        """Test tool creation with nonexistent template."""
        success = self.manager.create_tool(
            tool_name="valid-name",
            template_name="nonexistent"
        )
        self.assertFalse(success)

    def test_create_tool_already_exists(self):
        """Test tool creation when tool already exists."""
        # Create existing tool
        (self.output_dir / "existing-tool.yaml").write_text("name: existing")

        # Try to create without force
        success = self.manager.create_tool(
            tool_name="existing-tool",
            template_name="basic_webhook"
        )
        self.assertFalse(success)

    def test_create_tool_force_overwrite(self):
        """Test tool creation with force overwrite."""
        # Create template
        template_content = """
name: "{{tool_name}}"
description: "Test tool"
parameters:
  type: object
  properties: {}
"""
        (self.templates_dir / "simple.yaml").write_text(template_content)

        # Create existing tool
        (self.output_dir / "existing-tool.yaml").write_text("name: old")

        # Create with force
        success = self.manager.create_tool(
            tool_name="existing-tool",
            template_name="simple",
            force=True
        )
        self.assertTrue(success)

        # Check that file was overwritten
        with open(self.output_dir / "existing-tool.yaml", 'r') as f:
            content = yaml.safe_load(f)
        self.assertEqual(content['name'], 'existing-tool')

    def test_create_tool_dry_run(self):
        """Test tool creation in dry run mode."""
        # Create template
        template_content = """
name: "{{tool_name}}"
description: "Test tool"
parameters:
  type: object
  properties: {}
"""
        (self.templates_dir / "simple.yaml").write_text(template_content)

        # Create in dry run mode
        success = self.manager.create_tool(
            tool_name="dry-run-tool",
            template_name="simple",
            dry_run=True
        )
        self.assertTrue(success)

        # Check that file was NOT created
        tool_file = self.output_dir / "dry-run-tool.yaml"
        self.assertFalse(tool_file.exists())

    def test_get_template_info(self):
        """Test getting template information."""
        template_content = """# Description: A test template
name: "{{tool_name}}"
description: "{{description or 'Default description'}}"
server:
  url: "{{url}}"
parameters:
  type: object
"""
        (self.templates_dir / "test_template.yaml").write_text(template_content)

        info = self.manager.get_template_info("test_template")

        self.assertEqual(info['name'], 'test_template')
        self.assertIn('path', info)
        self.assertEqual(info['description'], ': A test template')
        self.assertIn('tool_name', info['variables'])
        self.assertIn('description', info['variables'])
        self.assertIn('url', info['variables'])

    def test_get_template_info_nonexistent(self):
        """Test getting info for nonexistent template."""
        with self.assertRaises(FileNotFoundError):
            self.manager.get_template_info("nonexistent")

    def test_preview_tool(self):
        """Test tool preview functionality."""
        template_content = """
name: "{{tool_name}}"
description: "{{description or 'A tool for ' + tool_name}}"
parameters:
  type: object
"""
        (self.templates_dir / "preview.yaml").write_text(template_content)

        preview = self.manager.preview_tool(
            "preview-tool",
            "preview",
            {"description": "Preview test"}
        )

        self.assertIn('name: "preview-tool"', preview)
        self.assertIn('description: "Preview test"', preview)


if __name__ == "__main__":
    unittest.main()