"""Unit tests for shared tools functionality."""

import unittest
import tempfile
import yaml
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from vapi_manager.core.assistant_config import (
    AssistantConfigLoader,
    CircularReferenceError,
    InvalidToolReferenceError
)


class TestSharedTools(unittest.TestCase):
    """Test cases for shared tools reference system."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        self.loader = AssistantConfigLoader()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_deep_merge_simple_dicts(self):
        """Test merging simple dictionaries."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = self.loader._deep_merge(base, override)

        self.assertEqual(result, {"a": 1, "b": 3, "c": 4})

    def test_deep_merge_nested_dicts(self):
        """Test merging nested dictionaries."""
        base = {
            "name": "test",
            "parameters": {
                "required": ["a", "b"],
                "properties": {
                    "a": {"type": "string"},
                    "b": {"type": "number"}
                }
            }
        }
        override = {
            "parameters": {
                "required": ["c"],
                "properties": {
                    "c": {"type": "boolean"}
                }
            }
        }

        result = self.loader._deep_merge(base, override)

        self.assertEqual(result["name"], "test")
        self.assertIn("a", result["parameters"]["required"])
        self.assertIn("b", result["parameters"]["required"])
        self.assertIn("c", result["parameters"]["required"])
        self.assertIn("a", result["parameters"]["properties"])
        self.assertIn("c", result["parameters"]["properties"])

    def test_deep_merge_lists(self):
        """Test merging lists with deduplication."""
        base = {"items": [1, 2, 3], "tags": ["foo", "bar"]}
        override = {"items": [3, 4, 5], "tags": ["bar", "baz"]}

        result = self.loader._deep_merge(base, override)

        self.assertEqual(result["items"], [1, 2, 3, 4, 5])
        self.assertEqual(result["tags"], ["foo", "bar", "baz"])

    def test_resolve_simple_reference(self):
        """Test resolving a simple tool reference."""
        # Create a base tool file
        base_tool = {
            "name": "testTool",
            "description": "A test tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                }
            }
        }

        tool_path = self.project_root / "shared" / "tools" / "test_tool.yaml"
        tool_path.parent.mkdir(parents=True, exist_ok=True)

        with open(tool_path, 'w') as f:
            yaml.dump(base_tool, f)

        # Create a reference
        tool_def = {"$ref": "shared/tools/test_tool.yaml"}

        with patch.object(Path, 'cwd', return_value=self.project_root):
            result = self.loader._resolve_tool_reference(tool_def, set())

        self.assertEqual(result["name"], "testTool")
        self.assertEqual(result["description"], "A test tool")

    def test_resolve_reference_with_overrides(self):
        """Test resolving a reference with overrides."""
        # Create base tool
        base_tool = {
            "name": "baseTool",
            "description": "Base description",
            "parameters": {
                "required": ["param1"],
                "properties": {
                    "param1": {"type": "string"}
                }
            }
        }

        tool_path = self.project_root / "shared" / "tools" / "base.yaml"
        tool_path.parent.mkdir(parents=True, exist_ok=True)

        with open(tool_path, 'w') as f:
            yaml.dump(base_tool, f)

        # Reference with overrides
        tool_def = {
            "$ref": "shared/tools/base.yaml",
            "overrides": {
                "description": "Overridden description",
                "parameters": {
                    "required": ["param2"],
                    "properties": {
                        "param2": {"type": "number"}
                    }
                }
            }
        }

        with patch.object(Path, 'cwd', return_value=self.project_root):
            result = self.loader._resolve_tool_reference(tool_def, set())

        self.assertEqual(result["name"], "baseTool")
        self.assertEqual(result["description"], "Overridden description")
        self.assertIn("param1", result["parameters"]["required"])
        self.assertIn("param2", result["parameters"]["required"])
        self.assertIn("param1", result["parameters"]["properties"])
        self.assertIn("param2", result["parameters"]["properties"])

    def test_nested_references(self):
        """Test resolving nested/chained references."""
        # Create base tool
        base_tool = {
            "name": "baseTool",
            "description": "Base tool",
            "server": {
                "url": "https://base.example.com"
            }
        }

        base_path = self.project_root / "shared" / "tools" / "base.yaml"
        base_path.parent.mkdir(parents=True, exist_ok=True)

        with open(base_path, 'w') as f:
            yaml.dump(base_tool, f)

        # Create intermediate tool that references base
        intermediate_tool = {
            "$ref": "shared/tools/base.yaml",
            "overrides": {
                "description": "Intermediate tool"
            }
        }

        intermediate_path = self.project_root / "shared" / "tools" / "intermediate.yaml"

        with open(intermediate_path, 'w') as f:
            yaml.dump(intermediate_tool, f)

        # Create final reference
        tool_def = {
            "$ref": "shared/tools/intermediate.yaml",
            "overrides": {
                "server": {
                    "url": "https://final.example.com"
                }
            }
        }

        with patch.object(Path, 'cwd', return_value=self.project_root):
            result = self.loader._resolve_tool_reference(tool_def, set())

        self.assertEqual(result["name"], "baseTool")
        self.assertEqual(result["description"], "Intermediate tool")
        self.assertEqual(result["server"]["url"], "https://final.example.com")

    def test_circular_reference_detection(self):
        """Test that circular references are detected and raise appropriate error."""
        # Create tool A that references B
        tool_a = {"$ref": "shared/tools/tool_b.yaml"}

        tool_a_path = self.project_root / "shared" / "tools" / "tool_a.yaml"
        tool_a_path.parent.mkdir(parents=True, exist_ok=True)

        with open(tool_a_path, 'w') as f:
            yaml.dump(tool_a, f)

        # Create tool B that references A (circular)
        tool_b = {"$ref": "shared/tools/tool_a.yaml"}

        tool_b_path = self.project_root / "shared" / "tools" / "tool_b.yaml"

        with open(tool_b_path, 'w') as f:
            yaml.dump(tool_b, f)

        # Try to resolve - should raise CircularReferenceError
        tool_def = {"$ref": "shared/tools/tool_a.yaml"}

        with patch.object(Path, 'cwd', return_value=self.project_root):
            with self.assertRaises(CircularReferenceError):
                self.loader._resolve_tool_reference(tool_def, set())

    def test_file_not_found_error(self):
        """Test that missing files raise FileNotFoundError."""
        tool_def = {"$ref": "shared/tools/nonexistent.yaml"}

        with patch.object(Path, 'cwd', return_value=self.project_root):
            with self.assertRaises(FileNotFoundError):
                self.loader._resolve_tool_reference(tool_def, set())

    def test_security_path_escape_detection(self):
        """Test that paths attempting to escape project root are rejected."""
        tool_def = {"$ref": "../../etc/passwd"}

        with patch.object(Path, 'cwd', return_value=self.project_root):
            with self.assertRaises(InvalidToolReferenceError):
                self.loader._resolve_tool_reference(tool_def, set())

    def test_load_tools_with_references(self):
        """Test the complete _load_tools method with shared references."""
        # Create shared tool
        shared_tool = {
            "name": "queryKnowledgeBase",
            "description": "Query the knowledge base",
            "server": {
                "url": "https://api.example.com/kb"
            }
        }

        shared_path = self.project_root / "shared" / "tools" / "kb.yaml"
        shared_path.parent.mkdir(parents=True, exist_ok=True)

        with open(shared_path, 'w') as f:
            yaml.dump(shared_tool, f)

        # Create assistant tools directory
        tools_dir = self.project_root / "assistants" / "test" / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)

        # Create functions.yaml with reference
        functions = {
            "functions": [
                {"$ref": "shared/tools/kb.yaml"},
                {
                    "name": "localTool",
                    "description": "A local tool"
                }
            ]
        }

        with open(tools_dir / "functions.yaml", 'w') as f:
            yaml.dump(functions, f)

        with patch.object(Path, 'cwd', return_value=self.project_root):
            result = self.loader._load_tools(tools_dir)

        self.assertIn("functions", result)
        self.assertEqual(len(result["functions"]["functions"]), 2)
        self.assertEqual(result["functions"]["functions"][0]["name"], "queryKnowledgeBase")
        self.assertEqual(result["functions"]["functions"][1]["name"], "localTool")


if __name__ == "__main__":
    unittest.main()