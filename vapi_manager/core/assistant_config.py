"""
File-based Assistant Configuration System

This module provides functionality to load assistant configurations from
a structured directory containing YAML/JSON files and markdown prompts.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass

from ..core.models import (
    Assistant,
    AssistantCreateRequest,
    Voice,
    ModelConfig,
    Tool,
    Transcriber,
    Server
)


class CircularReferenceError(Exception):
    """Raised when a circular reference is detected in tool definitions."""
    pass


class InvalidToolReferenceError(Exception):
    """Raised when a tool reference is invalid or malformed."""
    pass


@dataclass
class AssistantConfig:
    """Represents a complete assistant configuration loaded from files."""

    name: str
    base_path: Path
    config: Dict[str, Any]
    system_prompt: Optional[str] = None
    first_message: Optional[str] = None
    schemas: Dict[str, Any] = None
    tools: Dict[str, Any] = None
    events: Dict[str, str] = None

    def __post_init__(self):
        if self.schemas is None:
            self.schemas = {}
        if self.tools is None:
            self.tools = {}
        if self.events is None:
            self.events = {}


class AssistantConfigLoader:
    """Loads assistant configuration from file structure."""

    def __init__(self, base_dir: str = "assistants"):
        self.base_dir = Path(base_dir)

    def load_assistant(self, assistant_name: str, environment: str = "default") -> AssistantConfig:
        """
        Load an assistant configuration from its directory.

        Args:
            assistant_name: Name of the assistant directory
            environment: Environment to use for overrides (default, development, staging, production)

        Returns:
            AssistantConfig object with all loaded data
        """
        assistant_path = self.base_dir / assistant_name

        if not assistant_path.exists():
            raise FileNotFoundError(f"Assistant directory not found: {assistant_path}")

        # Load main configuration
        config = self._load_config_file(assistant_path / "assistant.yaml", environment)

        # Load prompts
        system_prompt = self._load_text_file(assistant_path / "prompts" / "system.md")
        first_message = self._load_text_file(assistant_path / "prompts" / "first_message.md")

        # Load schemas
        schemas = self._load_schemas(assistant_path / "schemas")

        # Load tools
        tools = self._load_tools(assistant_path / "tools")

        # Load events
        events = self._load_events(assistant_path / "events")

        return AssistantConfig(
            name=assistant_name,
            base_path=assistant_path,
            config=config,
            system_prompt=system_prompt,
            first_message=first_message,
            schemas=schemas,
            tools=tools,
            events=events
        )

    def _load_config_file(self, file_path: Path, environment: str) -> Dict[str, Any]:
        """Load and parse YAML/JSON configuration file with environment overrides."""
        if not file_path.exists():
            return {}

        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.suffix in ['.yaml', '.yml']:
                config = yaml.safe_load(f) or {}
            elif file_path.suffix == '.json':
                config = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")

        # Apply environment-specific overrides
        if environment != "default" and "environments" in config:
            env_config = config.get("environments", {}).get(environment, {})
            config = self._merge_configs(config, env_config)

        # Remove environments section from final config
        config.pop("environments", None)

        return config

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _load_text_file(self, file_path: Path) -> Optional[str]:
        """Load a text file (markdown, txt, etc.)."""
        if not file_path.exists():
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    def _load_schemas(self, schemas_dir: Path) -> Dict[str, Any]:
        """Load all schema files from the schemas directory."""
        schemas = {}

        if not schemas_dir.exists():
            return schemas

        for suffix in ['.yaml', '.yml', '.json']:
            for file_path in schemas_dir.glob(f"*{suffix}"):
                schema_name = file_path.stem
                with open(file_path, 'r', encoding='utf-8') as f:
                    if file_path.suffix in ['.yaml', '.yml']:
                        schemas[schema_name] = yaml.safe_load(f)
                    elif file_path.suffix == '.json':
                        schemas[schema_name] = json.load(f)

        return schemas

    def _load_tools(self, tools_dir: Path) -> Dict[str, Any]:
        """Load all tool configurations from the tools directory with support for shared tools."""
        tools = {}

        if not tools_dir.exists():
            return tools

        for suffix in ['.yaml', '.yml', '.json']:
            for file_path in tools_dir.glob(f"*{suffix}"):
                tool_name = file_path.stem
                with open(file_path, 'r', encoding='utf-8') as f:
                    if file_path.suffix in ['.yaml', '.yml']:
                        tool_config = yaml.safe_load(f)
                    elif file_path.suffix == '.json':
                        tool_config = json.load(f)
                    else:
                        continue

                    # Process shared tool references if functions exist
                    if tool_config and 'functions' in tool_config:
                        resolved_functions = []
                        for tool_def in tool_config.get('functions', []):
                            if isinstance(tool_def, dict) and '$ref' in tool_def:
                                # Resolve the tool reference
                                resolved_tool = self._resolve_tool_reference(tool_def, visited=set())
                                resolved_functions.append(resolved_tool)
                            else:
                                # Standard locally-defined tool
                                resolved_functions.append(tool_def)
                        tool_config['functions'] = resolved_functions

                    tools[tool_name] = tool_config

        return tools

    def _load_events(self, events_dir: Path) -> Dict[str, str]:
        """Load event handler scripts from the events directory."""
        events = {}

        if not events_dir.exists():
            return events

        for file_path in events_dir.glob("*.{js,py}"):
            event_name = file_path.stem
            with open(file_path, 'r', encoding='utf-8') as f:
                events[event_name] = f.read()

        return events

    def _resolve_tool_reference(self, tool_def: Dict, visited: Set[Path]) -> Dict:
        """
        Resolve a tool reference recursively, handling $ref and overrides.

        Args:
            tool_def: Tool definition potentially containing $ref
            visited: Set of already visited paths to detect circular references

        Returns:
            Resolved tool configuration

        Raises:
            CircularReferenceError: If circular reference detected
            InvalidToolReferenceError: If reference is invalid
            FileNotFoundError: If referenced file doesn't exist
        """
        ref_path_str = tool_def.get('$ref')
        if not ref_path_str:
            return tool_def

        # Find project root (look for pyproject.toml or fallback to current directory)
        project_root = Path.cwd()
        current = Path.cwd()
        while current != current.parent:
            if (current / 'pyproject.toml').exists() or (current / '.git').exists():
                project_root = current
                break
            current = current.parent

        # Resolve the reference path
        ref_path = project_root / ref_path_str

        # Security check: ensure path doesn't escape project
        try:
            ref_path = ref_path.resolve()
            if not str(ref_path).startswith(str(project_root)):
                raise InvalidToolReferenceError(f"Reference path escapes project boundary: {ref_path}")
        except Exception as e:
            raise InvalidToolReferenceError(f"Invalid reference path: {ref_path_str}")

        # Check for circular reference
        if ref_path in visited:
            raise CircularReferenceError(f"Circular reference detected: {ref_path}")

        visited.add(ref_path)

        # Load the referenced file
        if not ref_path.exists():
            raise FileNotFoundError(f"Shared tool reference not found: {ref_path}")

        with open(ref_path, 'r', encoding='utf-8') as f:
            if ref_path.suffix in ['.yaml', '.yml']:
                base_tool_config = yaml.safe_load(f)
            elif ref_path.suffix == '.json':
                base_tool_config = json.load(f)
            else:
                raise InvalidToolReferenceError(f"Unsupported file format: {ref_path.suffix}")

        # Recursively resolve if the base file also has a reference
        if isinstance(base_tool_config, dict) and '$ref' in base_tool_config:
            base_tool_config = self._resolve_tool_reference(base_tool_config, visited.copy())

        # Deep merge with overrides if present
        if 'overrides' in tool_def and tool_def['overrides']:
            base_tool_config = self._deep_merge(base_tool_config, tool_def['overrides'])

        return base_tool_config

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """
        Recursively merge two dictionaries. Arrays are combined and deduplicated.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        if not isinstance(base, dict) or not isinstance(override, dict):
            return override

        result = base.copy()

        for key, value in override.items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    # Recursively merge nested dictionaries
                    result[key] = self._deep_merge(result[key], value)
                elif isinstance(result[key], list) and isinstance(value, list):
                    # Combine lists and remove duplicates while preserving order
                    combined = result[key] + value
                    seen = set()
                    deduplicated = []
                    for item in combined:
                        # For hashable items
                        if isinstance(item, (str, int, float, bool, tuple)):
                            if item not in seen:
                                seen.add(item)
                                deduplicated.append(item)
                        else:
                            # For non-hashable items (dicts, lists), include all
                            deduplicated.append(item)
                    result[key] = deduplicated
                else:
                    # Override with new value
                    result[key] = value
            else:
                # Add new key
                result[key] = value

        return result

    def list_assistants(self) -> List[str]:
        """List all available assistant configurations."""
        if not self.base_dir.exists():
            return []

        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]

    def validate_config(self, config: AssistantConfig) -> bool:
        """Validate that an assistant configuration has required fields."""
        required_fields = ['name', 'model', 'voice']

        for field in required_fields:
            if field not in config.config:
                return False

        return True


class AssistantBuilder:
    """Builds VAPI Assistant objects from configuration."""

    @staticmethod
    def build_from_config(config: AssistantConfig) -> AssistantCreateRequest:
        """
        Build a VAPI AssistantCreateRequest from an AssistantConfig.

        Args:
            config: AssistantConfig object with loaded configuration

        Returns:
            AssistantCreateRequest ready to send to VAPI API
        """
        assistant_config = config.config

        # Build Voice configuration
        voice_config = assistant_config.get('voice', {})

        # Map provider names from config to VAPI API names
        provider = voice_config.get('provider')
        if provider:
            provider_mapping = {
                'elevenlabs': '11labs',
                'rime': 'rime-ai',
                # Other providers remain the same
            }
            provider = provider_mapping.get(provider, provider)

        # Create voice dict for direct VAPI API
        voice_data = {
            'provider': provider
        }
        if voice_config.get('voiceId'):
            voice_data['voiceId'] = voice_config['voiceId']
        if voice_config.get('model'):
            voice_data['model'] = voice_config['model']

        voice = voice_data

        # Build Model configuration
        model_config = assistant_config.get('model', {})

        # Build tools from configuration files
        tools = AssistantBuilder._build_tools(config.tools)

        model = ModelConfig(
            model=model_config.get('model'),
            provider=model_config.get('provider'),
            temperature=model_config.get('temperature'),
            tools=tools
        )

        # Add system prompt to model messages if available
        if config.system_prompt:
            model.messages = [
                {"role": "system", "content": config.system_prompt}
            ]

        # Build Transcriber configuration
        transcriber = None
        if 'transcriber' in assistant_config:
            trans_config = assistant_config['transcriber']
            transcriber = Transcriber(
                model=trans_config.get('model'),
                provider=trans_config.get('provider'),
                language=trans_config.get('language')
            )

        # Build Server configuration with environment variable support
        server = None
        if 'server' in assistant_config:
            server_config = assistant_config['server']
            server_url = AssistantBuilder._replace_env_vars(server_config.get('url', ''))

            # Only create server if URL is valid (not empty and not containing unresolved variables)
            if server_url and not '${' in server_url:
                server = Server(
                    url=server_url,
                    timeout_seconds=server_config.get('timeoutSeconds')
                )

        # Get firstMessageMode value
        first_message_mode_value = assistant_config.get('firstMessageMode')

        # Get serverMessages value
        server_messages = assistant_config.get('serverMessages')

        # Build AnalysisPlan if present in configuration
        analysis_plan = None
        if 'analysisPlan' in assistant_config:
            analysis_plan = AssistantBuilder._build_analysis_plan(assistant_config['analysisPlan'], config.schemas, config.base_path)

        # Create the assistant request
        # Build the request data as a dictionary first to use aliases properly
        request_data = {
            'name': assistant_config.get('name'),
            'voice': voice,
            'model': model,
            'transcriber': transcriber,
            'firstMessage': config.first_message or assistant_config.get('firstMessage'),
            'firstMessageMode': first_message_mode_value,  # Use the original string value with alias
            'serverMessages': server_messages,  # Add server messages support
            'analysisPlan': analysis_plan,  # Add analysis plan support
            'server': server
        }

        # Remove None values
        request_data = {k: v for k, v in request_data.items() if v is not None}

        # Create request using model_validate
        request = AssistantCreateRequest.model_validate(request_data)

        return request

    @staticmethod
    def _build_tools(tools_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build tools list from tools configuration for direct VAPI API."""
        tools = []

        # Process functions
        if 'functions' in tools_config:
            functions = tools_config['functions'].get('functions', [])
            for func in functions:
                # Create function tool for VAPI API
                tool = {
                    "type": "function",
                    "function": {
                        "name": func.get("name"),
                        "description": func.get("description"),
                        "parameters": func.get("parameters", {})
                    }
                }

                # Add server configuration if present
                if 'server' in func and func['server']:
                    tool['server'] = func['server']

                tools.append(tool)

        # Process transfers
        if 'transfers' in tools_config:
            transfers_data = tools_config['transfers']

            # Look for transfers list in the config
            transfer_list = transfers_data.get('transfers', [])

            # Group transfers by type for better organization
            phone_destinations = []
            assistant_transfers = []

            for transfer in transfer_list:
                if transfer.get('type') == 'number':
                    phone_destinations.append({
                        "type": "number",
                        "number": transfer.get('number'),
                        "description": transfer.get('description', '')
                    })
                elif transfer.get('type') == 'assistant':
                    # For assistant transfers, we'll need to handle them differently
                    # For now, skip assistant transfers as they need valid assistant IDs
                    pass

            # Add transfer tool if we have phone destinations
            if phone_destinations:
                # Only add valid phone numbers (skip environment variables for now)
                valid_destinations = [
                    dest for dest in phone_destinations
                    if dest['number'] and not dest['number'].startswith('${')
                ]

                if valid_destinations:
                    tool = {
                        "type": "transferCall",
                        "destinations": valid_destinations
                    }
                    tools.append(tool)

        # Process VAPI built-in tools from tool configs
        for tool_name, tool_config in tools_config.items():
            if isinstance(tool_config, dict) and tool_config.get('type') == 'vapi-builtin-collection':
                vapi_tool_configs = tool_config.get('vapi_tools', {})
                for vapi_tool_name, vapi_tool_config in vapi_tool_configs.items():
                    if not vapi_tool_config.get('enabled', False):
                        continue

                    # Skip endCall and transferCall as they're handled elsewhere
                    if vapi_tool_name in ['endCall', 'transferCall']:
                        continue

                    vapi_tool = {"type": vapi_tool_config.get('type', vapi_tool_name)}

                    if vapi_tool_name == 'voicemail' and 'message' in vapi_tool_config:
                        vapi_tool['message'] = vapi_tool_config['message']

                    tools.append(vapi_tool)

        # Add standard tools
        tools.append({"type": "endCall"})

        return tools

    @staticmethod
    def _replace_env_vars(value: str) -> str:
        """Replace environment variable placeholders in strings."""
        if not isinstance(value, str):
            return value

        import re
        pattern = r'\$\{([^}]+)\}'

        def replacer(match):
            env_var = match.group(1)
            return os.environ.get(env_var, match.group(0))

        return re.sub(pattern, replacer, value)

    @staticmethod
    def _load_prompt_template(assistant_path: Path, prompt_name: str) -> Optional[str]:
        """
        Load a prompt template from the assistant's prompts directory.

        Args:
            assistant_path: Path to the assistant directory
            prompt_name: Name of the prompt file (e.g., 'summary-system-prompt.md')

        Returns:
            Prompt content or None if not found
        """
        prompts_dir = assistant_path / "prompts"

        if not prompts_dir.exists():
            return None

        prompt_path = prompts_dir / prompt_name

        if not prompt_path.exists():
            return None

        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"Warning: Failed to load prompt template '{prompt_name}': {str(e)}")
            return None

    @staticmethod
    def _build_analysis_plan(analysis_config: Dict[str, Any], schemas: Dict[str, Any], assistant_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Build AnalysisPlan from configuration and schemas.

        Args:
            analysis_config: analysisPlan section from YAML config
            schemas: Loaded schemas from schemas/ directory
            assistant_path: Path to assistant directory for loading prompt files

        Returns:
            Dictionary representing the AnalysisPlan for VAPI API
        """
        from ..core.models.assistant import AnalysisPlan, SummaryPlan, StructuredDataPlan

        analysis_plan_data = {}

        # Add minMessagesThreshold
        if 'minMessagesThreshold' in analysis_config:
            analysis_plan_data['minMessagesThreshold'] = analysis_config['minMessagesThreshold']

        # Build SummaryPlan
        if 'summaryPlan' in analysis_config:
            summary_config = analysis_config['summaryPlan']
            summary_plan_data = {
                'enabled': summary_config.get('enabled', False)
            }

            if 'timeoutSeconds' in summary_config:
                summary_plan_data['timeoutSeconds'] = summary_config['timeoutSeconds']

            # Check for prompt files first, fall back to config messages
            if assistant_path:
                system_prompt = AssistantBuilder._load_prompt_template(assistant_path, 'summary-system-prompt.md')
                user_prompt = AssistantBuilder._load_prompt_template(assistant_path, 'summary-user-prompt.md')

                if system_prompt and user_prompt:
                    summary_plan_data['messages'] = [
                        {
                            'role': 'system',
                            'content': system_prompt
                        },
                        {
                            'role': 'user',
                            'content': user_prompt
                        }
                    ]
                elif 'messages' in summary_config:
                    summary_plan_data['messages'] = summary_config['messages']
            elif 'messages' in summary_config:
                summary_plan_data['messages'] = summary_config['messages']

            # Only include summaryPlan if it has messages when enabled
            if summary_plan_data.get('enabled', False):
                if 'messages' not in summary_plan_data or not summary_plan_data['messages']:
                    # If enabled but no messages, log warning and skip adding it
                    # This preserves existing summaryPlan in VAPI if prompt files fail to load
                    print(f"Warning: summaryPlan is enabled but no messages found. Skipping summaryPlan update to preserve existing configuration.")
                else:
                    # Only add if we have valid messages
                    analysis_plan_data['summaryPlan'] = summary_plan_data
            elif not summary_plan_data.get('enabled', False) and 'messages' in summary_plan_data:
                # If explicitly disabled but has messages, include it
                analysis_plan_data['summaryPlan'] = summary_plan_data

        # Build StructuredDataPlan
        if 'structuredDataPlan' in analysis_config:
            structured_config = analysis_config['structuredDataPlan']
            structured_plan_data = {
                'enabled': structured_config.get('enabled', False)
            }

            if 'timeoutSeconds' in structured_config:
                structured_plan_data['timeoutSeconds'] = structured_config['timeoutSeconds']

            # Check for prompt files first, fall back to config messages
            if assistant_path:
                system_prompt = AssistantBuilder._load_prompt_template(assistant_path, 'extraction-system-prompt.md')
                user_prompt = AssistantBuilder._load_prompt_template(assistant_path, 'extraction-user-prompt.md')

                if system_prompt and user_prompt:
                    structured_plan_data['messages'] = [
                        {
                            'role': 'system',
                            'content': system_prompt
                        },
                        {
                            'role': 'user',
                            'content': user_prompt
                        }
                    ]
                elif 'messages' in structured_config:
                    structured_plan_data['messages'] = structured_config['messages']
            elif 'messages' in structured_config:
                structured_plan_data['messages'] = structured_config['messages']

            # Include schema from schemas/structured_data.yaml if available
            if 'structured_data' in schemas:
                structured_plan_data['schema'] = schemas['structured_data']

            # Only include structuredDataPlan if it has messages when enabled
            if structured_plan_data.get('enabled', False):
                if 'messages' not in structured_plan_data or not structured_plan_data['messages']:
                    # If enabled but no messages, log warning and skip adding it
                    # This preserves existing structuredDataPlan in VAPI if prompt files fail to load
                    print(f"Warning: structuredDataPlan is enabled but no messages found. Skipping structuredDataPlan update to preserve existing configuration.")
                else:
                    # Only add if we have valid messages
                    analysis_plan_data['structuredDataPlan'] = structured_plan_data
            elif not structured_plan_data.get('enabled', False) and 'messages' in structured_plan_data:
                # If explicitly disabled but has messages, include it
                analysis_plan_data['structuredDataPlan'] = structured_plan_data

        return analysis_plan_data if analysis_plan_data else None