"""
Unit tests for TemplateManager
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from vapi_manager.core.template_manager import TemplateManager


class TestTemplateManager(unittest.TestCase):
    """Test cases for TemplateManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = Path(self.temp_dir) / "templates" / "assistants"
        self.assistants_dir = Path(self.temp_dir) / "assistants"

        # Create directories
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.assistants_dir.mkdir(parents=True, exist_ok=True)

        # Create test template
        self.test_template_dir = self.templates_dir / "test_template"
        self.test_template_dir.mkdir(parents=True, exist_ok=True)

        # Create template files
        (self.test_template_dir / "assistant.yaml").write_text(
            "name: {{assistant_name}}\nmodel: gpt-4"
        )
        prompts_dir = self.test_template_dir / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "system.md").write_text("You are {{assistant_name}}.")

        self.manager = TemplateManager(
            templates_dir=str(self.templates_dir),
            assistants_dir=str(self.assistants_dir)
        )

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_templates_dir_is_templates_assistants(self):
        """Test that default templates_dir is templates/assistants."""
        manager = TemplateManager()
        self.assertEqual(manager.templates_dir, Path("templates/assistants"))

    def test_list_templates(self):
        """Test listing available templates."""
        templates = self.manager.list_templates()
        self.assertEqual(templates, ["test_template"])

    def test_template_exists(self):
        """Test checking if template exists."""
        self.assertTrue(self.manager.template_exists("test_template"))
        self.assertFalse(self.manager.template_exists("nonexistent"))

    def test_assistant_exists(self):
        """Test checking if assistant exists."""
        # Create a test assistant
        test_assistant = self.assistants_dir / "test_assistant"
        test_assistant.mkdir()

        self.assertTrue(self.manager.assistant_exists("test_assistant"))
        self.assertFalse(self.manager.assistant_exists("nonexistent"))

    def test_init_assistant_success(self):
        """Test successful assistant initialization."""
        result = self.manager.init_assistant(
            assistant_name="new_assistant",
            template_name="test_template"
        )

        self.assertTrue(result)

        # Check assistant was created
        assistant_path = self.assistants_dir / "new_assistant"
        self.assertTrue(assistant_path.exists())

        # Check files were created with variable substitution
        assistant_yaml = assistant_path / "assistant.yaml"
        self.assertTrue(assistant_yaml.exists())
        self.assertIn("name: new_assistant", assistant_yaml.read_text())

        prompts_system = assistant_path / "prompts" / "system.md"
        self.assertTrue(prompts_system.exists())
        self.assertIn("You are new_assistant", prompts_system.read_text())

    def test_init_assistant_invalid_name(self):
        """Test assistant initialization with invalid name."""
        result = self.manager.init_assistant(
            assistant_name="invalid name!",
            template_name="test_template"
        )
        self.assertFalse(result)

    def test_init_assistant_template_not_found(self):
        """Test assistant initialization with non-existent template."""
        result = self.manager.init_assistant(
            assistant_name="new_assistant",
            template_name="nonexistent_template"
        )
        self.assertFalse(result)

    def test_init_assistant_already_exists(self):
        """Test assistant initialization when assistant already exists."""
        # Create assistant first time
        self.manager.init_assistant(
            assistant_name="existing_assistant",
            template_name="test_template"
        )

        # Try to create again without force
        result = self.manager.init_assistant(
            assistant_name="existing_assistant",
            template_name="test_template",
            force=False
        )
        self.assertFalse(result)

        # Try with force
        result = self.manager.init_assistant(
            assistant_name="existing_assistant",
            template_name="test_template",
            force=True
        )
        self.assertTrue(result)

    def test_init_assistant_with_custom_variables(self):
        """Test assistant initialization with custom variables."""
        result = self.manager.init_assistant(
            assistant_name="custom_assistant",
            template_name="test_template",
            variables={"model": "gpt-3.5-turbo"}
        )

        self.assertTrue(result)
        assistant_path = self.assistants_dir / "custom_assistant"
        self.assertTrue(assistant_path.exists())

    def test_get_template_info(self):
        """Test getting template information."""
        info = self.manager.get_template_info("test_template")

        self.assertEqual(info["name"], "test_template")
        self.assertTrue(info["files"]["assistant.yaml"])
        self.assertTrue(info["files"]["prompts/system.md"])
        self.assertIn("prompts", info["directories"])

    def test_validate_assistant_name(self):
        """Test assistant name validation."""
        valid_names = [
            "assistant1",
            "my_assistant",
            "my-assistant",
            "Assistant_123"
        ]

        invalid_names = [
            "",
            "assistant name",
            "assistant!",
            "assistant@123",
            "assistant.bot"
        ]

        for name in valid_names:
            self.assertTrue(
                self.manager._validate_assistant_name(name),
                f"'{name}' should be valid"
            )

        for name in invalid_names:
            self.assertFalse(
                self.manager._validate_assistant_name(name),
                f"'{name}' should be invalid"
            )

    def test_substitute_variables(self):
        """Test variable substitution."""
        content = "Hello {{name}}, your model is {{model}}"
        variables = {"name": "Assistant", "model": "GPT-4"}

        result = self.manager._substitute_variables(content, variables)
        self.assertEqual(result, "Hello Assistant, your model is GPT-4")

    @patch.dict('os.environ', {'TEST_VAR': 'test_value'})
    def test_substitute_environment_variables(self):
        """Test environment variable substitution."""
        content = "API Key: ${TEST_VAR}"
        result = self.manager._substitute_variables(content, {})
        self.assertEqual(result, "API Key: test_value")

        # Test with non-existent env var
        content = "Missing: ${NONEXISTENT_VAR}"
        result = self.manager._substitute_variables(content, {})
        self.assertEqual(result, "Missing: ${NONEXISTENT_VAR}")


if __name__ == '__main__':
    unittest.main()