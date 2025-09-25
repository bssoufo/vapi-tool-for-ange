"""
Assistant Template Validator

Validates assistant template existence and creates missing templates during
squad manifest creation for improved developer experience.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from rich.console import Console

console = Console()


@dataclass
class ValidationResult:
    """Result of assistant template validation."""
    is_valid: bool
    missing_assistants: List[str]
    created_assistants: List[str]
    errors: List[str]
    warnings: List[str]

    def __post_init__(self):
        if self.missing_assistants is None:
            self.missing_assistants = []
        if self.created_assistants is None:
            self.created_assistants = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class AssistantTemplateValidator:
    """
    Validates assistant template existence and can auto-create missing templates.

    Provides functionality to ensure all assistants referenced in squad manifests
    have corresponding template directories and configurations.
    """

    def __init__(
        self,
        assistants_dir: str = "templates/assistants",
        default_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the validator.

        Args:
            assistants_dir: Directory containing assistant templates
            default_config: Default configuration for auto-created assistants
        """
        self.assistants_dir = Path(assistants_dir)
        self.default_config = default_config or self._get_default_config()

    def exists(self, assistant_name: str) -> bool:
        """
        Check if an assistant template exists.

        Args:
            assistant_name: Name of the assistant to check

        Returns:
            True if assistant template exists, False otherwise
        """
        assistant_path = self.assistants_dir / assistant_name
        config_file = assistant_path / "assistant.yaml"
        return config_file.exists()

    def validate_all_assistants(
        self,
        assistant_names: List[str],
        auto_create: bool = True
    ) -> ValidationResult:
        """
        Validate all assistants in the list.

        Args:
            assistant_names: List of assistant names to validate
            auto_create: Whether to auto-create missing assistants

        Returns:
            ValidationResult with detailed validation information
        """
        result = ValidationResult(
            is_valid=True,
            missing_assistants=[],
            created_assistants=[],
            errors=[],
            warnings=[]
        )

        for assistant_name in assistant_names:
            if not self.exists(assistant_name):
                result.missing_assistants.append(assistant_name)

                if auto_create:
                    try:
                        self.create_template(assistant_name)
                        result.created_assistants.append(assistant_name)
                        console.print(f"[green]Created assistant template: {assistant_name}[/green]")
                    except Exception as e:
                        result.errors.append(f"Failed to create {assistant_name}: {str(e)}")
                        result.is_valid = False
                else:
                    result.errors.append(f"Assistant template not found: {assistant_name}")
                    result.is_valid = False

        # Final validation - check if all assistants now exist
        still_missing = [name for name in assistant_names if not self.exists(name)]
        if still_missing:
            result.is_valid = False
            result.errors.extend([f"Assistant still missing after creation: {name}" for name in still_missing])

        return result

    def create_template(
        self,
        assistant_name: str,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Create a new assistant template with default configuration.

        Args:
            assistant_name: Name of the assistant to create
            custom_config: Custom configuration to override defaults

        Returns:
            Path to the created template directory

        Raises:
            OSError: If template creation fails
        """
        assistant_path = self.assistants_dir / assistant_name

        # Create directory structure
        assistant_path.mkdir(parents=True, exist_ok=True)
        (assistant_path / "tools").mkdir(exist_ok=True)
        (assistant_path / "prompts").mkdir(exist_ok=True)

        # Prepare configuration
        config = self.default_config.copy()
        if custom_config:
            config.update(custom_config)

        # Set assistant name
        config["name"] = assistant_name

        # Create assistant.yaml
        config_file = assistant_path / "assistant.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        # Create default system prompt
        self._create_default_system_prompt(assistant_path, assistant_name)

        # Create empty tools configuration
        self._create_default_tools_config(assistant_path)

        console.print(f"[cyan]Created assistant template:[/cyan] {assistant_path}")
        return assistant_path

    def _create_default_system_prompt(self, assistant_path: Path, assistant_name: str):
        """Create a default system prompt file."""
        prompt_file = assistant_path / "prompts" / "system.md"

        # Generate role-based prompt based on assistant name
        role_description = self._generate_role_description(assistant_name)

        prompt_content = f"""# {assistant_name.replace('-', ' ').title()} Assistant

You are a {role_description} assistant designed to help users with their inquiries.

## Your Role
- Provide helpful and accurate information
- Maintain a professional and friendly tone
- Guide users through processes step by step
- Transfer calls when appropriate

## Guidelines
- Always greet users warmly
- Listen carefully to understand their needs
- Provide clear and concise responses
- Ask clarifying questions when needed
- Escalate complex issues to appropriate specialists

## Transfer Instructions
When you need to transfer a call, use the appropriate transfer function and explain to the user what you're doing.
"""

        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt_content)

    def _create_default_tools_config(self, assistant_path: Path):
        """Create default tools configuration."""
        tools_file = assistant_path / "tools" / "functions.yaml"

        tools_config = {
            "functions": [
                {
                    "name": "get_information",
                    "description": "Get general information to help users",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The information request from the user"
                            }
                        },
                        "required": ["query"]
                    }
                }
            ]
        }

        with open(tools_file, 'w', encoding='utf-8') as f:
            yaml.dump(tools_config, f, default_flow_style=False)

    def _generate_role_description(self, assistant_name: str) -> str:
        """Generate a role description based on assistant name."""
        name_lower = assistant_name.lower()

        if 'triage' in name_lower:
            return "reception and triage"
        elif 'booking' in name_lower or 'schedule' in name_lower:
            return "booking and scheduling"
        elif 'info' in name_lower or 'information' in name_lower:
            return "information and research"
        elif 'support' in name_lower:
            return "customer support"
        elif 'sales' in name_lower:
            return "sales and consultation"
        else:
            return "specialized service"

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default assistant configuration."""
        return {
            "_vapi": {
                "current_environment": "development",
                "environments": {
                    "development": {
                        "deployed_at": None,
                        "deployed_by": None,
                        "id": None,
                        "version": 0
                    },
                    "staging": {
                        "deployed_at": None,
                        "deployed_by": None,
                        "id": None,
                        "version": 0
                    },
                    "production": {
                        "deployed_at": None,
                        "deployed_by": None,
                        "id": None,
                        "version": 0
                    }
                },
                "last_sync": None
            },
            "description": "AI assistant for handling user inquiries",
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "temperature": 0.7
            },
            "voice": {
                "provider": "minimax",
                "voiceId": "business_female_1_v1"
            },
            "transcriber": {
                "provider": "deepgram",
                "model": "nova-2",
                "language": "en"
            },
            "firstMessageMode": "assistant-speaks-first-with-model-generated-message",
            "server": {
                "url": "https://n8n-2-u19609.vm.elestio.app/webhook/{{assistant_name}}",
                "timeoutSeconds": 20
            },
            "serverMessages": ["end-of-call-report"],
            "environments": {
                "development": {
                    "model": {
                        "model": "gpt-3.5-turbo",
                        "temperature": 0.8
                    },
                    "firstMessageMode": "assistant-speaks-first"
                },
                "staging": {
                    "firstMessageMode": "wait-for-user",
                    "voice": {
                        "voiceId": "business_female_1_v1"
                    }
                },
                "production": {
                    "model": {
                        "model": "gpt-4o-mini",
                        "temperature": 0.6
                    },
                    "firstMessageMode": "assistant-speaks-first-with-model-generated-message"
                }
            },
            "features": {
                "enableAnalytics": True,
                "enableRecording": True,
                "enableTranscription": True
            },
            "metadata": {
                "author": "Squad Template Creator",
                "tags": ["auto-generated"],
                "template": "auto_created",
                "version": "1.0.0"
            }
        }

    def list_missing_assistants(self, assistant_names: List[str]) -> List[str]:
        """
        Get list of missing assistant templates.

        Args:
            assistant_names: List of assistant names to check

        Returns:
            List of missing assistant names
        """
        return [name for name in assistant_names if not self.exists(name)]

    def get_existing_assistants(self) -> List[str]:
        """
        Get list of all existing assistant templates.

        Returns:
            List of existing assistant template names
        """
        if not self.assistants_dir.exists():
            return []

        existing = []
        for item in self.assistants_dir.iterdir():
            if item.is_dir() and (item / "assistant.yaml").exists():
                existing.append(item.name)

        return sorted(existing)