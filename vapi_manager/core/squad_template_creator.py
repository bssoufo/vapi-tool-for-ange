"""
Squad Template Creator with Builder Pattern

This module provides a fluent API for creating squad templates with manifests.
Leverages existing bootstrap infrastructure for consistency and validation.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import asdict
from rich.console import Console

from .bootstrap_manager import BootstrapManifest, BootstrapAssistant, BootstrapTool
from .squad_template_manager import SquadTemplateManager
from .assistant_template_validator import AssistantTemplateValidator, ValidationResult

console = Console()


class SquadTemplateCreatorError(Exception):
    """Base exception for SquadTemplateCreator errors."""
    pass


class SquadTemplateCreator:
    """
    Builder pattern implementation for creating squad templates with manifests.

    Provides a fluent API for constructing complex squad templates while leveraging
    existing bootstrap infrastructure for validation and consistency.
    """

    def __init__(
        self,
        template_name: str,
        auto_create_assistants: bool = True,
        assistants_dir: str = "templates/assistants"
    ):
        """
        Initialize the template creator.

        Args:
            template_name: Name of the template to create
            auto_create_assistants: Whether to auto-create missing assistant templates
            assistants_dir: Directory containing assistant templates
        """
        self.template_name = template_name
        self.auto_create_assistants = auto_create_assistants
        self.assistant_validator = AssistantTemplateValidator(assistants_dir)
        self.manifest = BootstrapManifest(
            description="",
            assistants=[],
            tools=None,
            metadata=None,
            deployment=None,
            environments=None
        )
        self.squad_config = {}
        self.members_config = {"members": []}
        self.routing_rules = {}
        self.routing_destinations = {}
        self._output_dir = Path("templates/squads")
        self._validation_result = None
        self._assistant_roles = {}  # Track assistant roles for intelligent routing

    def with_description(self, description: str) -> 'SquadTemplateCreator':
        """
        Set the template description.

        Args:
            description: Human-readable description of the squad template

        Returns:
            Self for method chaining
        """
        self.manifest.description = description
        return self

    def with_metadata(self, **metadata) -> 'SquadTemplateCreator':
        """
        Add metadata to the template.

        Args:
            **metadata: Key-value pairs for template metadata

        Returns:
            Self for method chaining
        """
        if self.manifest.metadata is None:
            self.manifest.metadata = {}
        self.manifest.metadata.update(metadata)
        return self

    def add_assistant(
        self,
        name: str,
        template: str,
        role: Optional[str] = None,
        priority: int = 2,
        required_tools: Optional[List[str]] = None,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> 'SquadTemplateCreator':
        """
        Add an assistant to the squad template.

        Args:
            name: Assistant instance name
            template: Assistant template to use
            role: Description of the assistant's role
            priority: Routing priority (1 = highest)
            required_tools: List of tool references this assistant needs
            config_overrides: Configuration overrides for the assistant

        Returns:
            Self for method chaining

        Raises:
            SquadTemplateCreatorError: If assistant validation fails and auto-creation is disabled
        """
        # Validate assistant template exists or create if needed
        if self.auto_create_assistants:
            self._ensure_assistant_exists(name, config_overrides)
        elif not self.assistant_validator.exists(name):
            raise SquadTemplateCreatorError(
                f"Assistant template '{name}' not found and auto-creation is disabled. "
                f"Enable auto-creation or create the assistant template manually."
            )

        # Add to manifest
        bootstrap_assistant = BootstrapAssistant(
            name=name,
            template=template,
            role=role,
            config_overrides=config_overrides,
            required_tools=required_tools
        )
        self.manifest.assistants.append(bootstrap_assistant)

        # Track assistant role for routing
        self._assistant_roles[name] = role or self._infer_role_from_name(name)

        # Add to members config with destinations
        member_config = {
            "assistant_name": name,
            "role": role or f"{name} assistant",
            "priority": priority,
            "description": self._generate_assistant_description(name, role),
            "destinations": []  # Will be populated by _generate_intelligent_routing
        }
        self.members_config["members"].append(member_config)

        return self

    def add_tool(
        self,
        name: str,
        template: str,
        description: Optional[str] = None,
        **variables
    ) -> 'SquadTemplateCreator':
        """
        Add a shared tool to the squad template.

        Args:
            name: Tool name
            template: Tool template to use
            description: Tool description
            **variables: Template variables for the tool

        Returns:
            Self for method chaining
        """
        if self.manifest.tools is None:
            self.manifest.tools = []

        tool = BootstrapTool(
            name=name,
            template=template,
            variables=variables,
            description=description
        )
        self.manifest.tools.append(tool)
        return self

    def with_deployment_config(
        self,
        strategy: str = "rolling",
        rollback_on_failure: bool = True,
        health_checks: bool = True,
        validation_steps: Optional[List[str]] = None
    ) -> 'SquadTemplateCreator':
        """
        Configure deployment settings for the template.

        Args:
            strategy: Deployment strategy ("rolling", "blue_green", "all_at_once")
            rollback_on_failure: Whether to rollback on deployment failure
            health_checks: Whether to perform health checks
            validation_steps: List of validation steps to perform

        Returns:
            Self for method chaining
        """
        self.manifest.deployment = {
            "strategy": strategy,
            "rollback_on_failure": rollback_on_failure,
            "health_checks": health_checks
        }

        if validation_steps:
            self.manifest.deployment["validation_steps"] = validation_steps

        return self

    def add_environment(
        self,
        environment: str,
        assistant_overrides: Optional[List[Dict[str, Any]]] = None,
        tool_overrides: Optional[List[Dict[str, Any]]] = None
    ) -> 'SquadTemplateCreator':
        """
        Add environment-specific configuration.

        Args:
            environment: Environment name (e.g., "development", "production")
            assistant_overrides: Assistant configuration overrides for this environment
            tool_overrides: Tool configuration overrides for this environment

        Returns:
            Self for method chaining
        """
        if self.manifest.environments is None:
            self.manifest.environments = {}

        env_config = {}
        if assistant_overrides:
            env_config["assistants"] = assistant_overrides
        if tool_overrides:
            env_config["tools"] = tool_overrides

        self.manifest.environments[environment] = env_config
        return self

    def add_routing_rule(
        self,
        rule_name: str,
        rule_type: str,
        priority: int,
        triggers: List[Dict[str, Any]],
        destination: str,
        description: Optional[str] = None
    ) -> 'SquadTemplateCreator':
        """
        Add a routing rule to the template.

        Args:
            rule_name: Name of the routing rule
            rule_type: Type of rule ("priority", "intent", "keyword")
            priority: Rule priority
            triggers: List of trigger conditions
            destination: Routing destination
            description: Rule description

        Returns:
            Self for method chaining
        """
        if f"{rule_type}_rules" not in self.routing_rules:
            self.routing_rules[f"{rule_type}_rules"] = []

        rule = {
            "name": rule_name,
            "priority": priority,
            "triggers": triggers,
            "action": {"destination": destination}
        }

        if description:
            rule["description"] = description

        self.routing_rules[f"{rule_type}_rules"].append(rule)
        return self

    def with_squad_config(self, **config) -> 'SquadTemplateCreator':
        """
        Add squad-level configuration.

        Args:
            **config: Squad configuration parameters

        Returns:
            Self for method chaining
        """
        self.squad_config.update(config)
        return self

    def set_output_directory(self, output_dir: str) -> 'SquadTemplateCreator':
        """
        Set the output directory for the template.

        Args:
            output_dir: Directory where template will be created

        Returns:
            Self for method chaining
        """
        self._output_dir = Path(output_dir)
        return self

    def validate(self) -> List[str]:
        """
        Validate the current template configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check required fields
        if not self.manifest.description:
            errors.append("Template description is required")

        if not self.manifest.assistants:
            errors.append("At least one assistant is required")

        # Validate assistant templates exist
        for assistant in self.manifest.assistants:
            # This would normally check against actual templates
            # For now, we'll do basic validation
            if not assistant.name or not assistant.template:
                errors.append(f"Assistant missing name or template: {assistant}")

        # Validate tool references
        tool_names = set()
        if self.manifest.tools:
            tool_names = {tool.name for tool in self.manifest.tools}

        for assistant in self.manifest.assistants:
            if assistant.required_tools:
                for tool_ref in assistant.required_tools:
                    tool_name = Path(tool_ref).stem
                    if tool_name not in tool_names:
                        errors.append(
                            f"Assistant '{assistant.name}' references unknown tool '{tool_name}'"
                        )

        return errors

    def create(self, force: bool = False) -> Path:
        """
        Create the squad template with all configuration files.

        Args:
            force: Overwrite existing template if it exists

        Returns:
            Path to the created template directory

        Raises:
            SquadTemplateCreatorError: If validation fails or template exists without force
        """
        # Validate configuration
        errors = self.validate()
        if errors:
            raise SquadTemplateCreatorError(f"Validation failed: {'; '.join(errors)}")

        # Check if template already exists
        template_path = self._output_dir / self.template_name
        if template_path.exists() and not force:
            raise SquadTemplateCreatorError(
                f"Template '{self.template_name}' already exists. Use force=True to overwrite."
            )

        # Remove existing template if force is enabled
        if template_path.exists() and force:
            import shutil
            shutil.rmtree(template_path)

        # Create template directory
        template_path.mkdir(parents=True, exist_ok=True)

        # Generate intelligent routing before creating files
        self._generate_intelligent_routing()

        # Create manifest.yaml
        self._create_manifest_file(template_path)

        # Create squad.yaml
        self._create_squad_config_file(template_path)

        # Create members.yaml (now with populated destinations)
        self._create_members_config_file(template_path)

        # Create routing directory and files
        self._create_routing_files(template_path)

        console.print(f"[green]+[/green] Squad template '{self.template_name}' created successfully!")
        console.print(f"[cyan]Location:[/cyan] {template_path}")
        console.print(f"[cyan]Files created:[/cyan]")
        console.print(f"  - manifest.yaml")
        console.print(f"  - squad.yaml")
        console.print(f"  - members.yaml")
        console.print(f"  - routing/destinations.yaml")

        return template_path

    def _create_manifest_file(self, template_path: Path):
        """Create the manifest.yaml file."""
        manifest_data = {
            "description": self.manifest.description,
            "metadata": self.manifest.metadata,
            "tools": [asdict(tool) for tool in self.manifest.tools] if self.manifest.tools else None,
            "assistants": [asdict(assistant) for assistant in self.manifest.assistants],
            "deployment": self.manifest.deployment,
            "environments": self.manifest.environments
        }

        # Remove None values for cleaner YAML
        manifest_data = {k: v for k, v in manifest_data.items() if v is not None}

        manifest_file = template_path / "manifest.yaml"
        with open(manifest_file, 'w', encoding='utf-8') as f:
            yaml.dump(manifest_data, f, default_flow_style=False, sort_keys=False)

    def _create_squad_config_file(self, template_path: Path):
        """Create the squad.yaml file."""
        squad_data = {
            "name": self.template_name,  # Use actual template name instead of placeholder
            "description": self.manifest.description,
            **self.squad_config
        }

        squad_file = template_path / "squad.yaml"
        with open(squad_file, 'w', encoding='utf-8') as f:
            yaml.dump(squad_data, f, default_flow_style=False, sort_keys=False)

    def _create_members_config_file(self, template_path: Path):
        """Create the members.yaml file."""
        members_file = template_path / "members.yaml"
        with open(members_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.members_config, f, default_flow_style=False, sort_keys=False)


    def preview(self) -> str:
        """
        Generate a preview of what will be created.

        Returns:
            String representation of the template structure
        """
        preview_text = []
        preview_text.append(f"Squad Template: {self.template_name}")
        preview_text.append(f"Description: {self.manifest.description}")

        if self.manifest.tools:
            preview_text.append(f"\nTools ({len(self.manifest.tools)}):")
            for tool in self.manifest.tools:
                preview_text.append(f"  • {tool.name} (template: {tool.template})")

        preview_text.append(f"\nAssistants ({len(self.manifest.assistants)}):")
        for assistant in self.manifest.assistants:
            preview_text.append(f"  • {assistant.name} (template: {assistant.template})")
            if assistant.role:
                preview_text.append(f"    Role: {assistant.role}")

        if self.manifest.environments:
            preview_text.append(f"\nEnvironments: {', '.join(self.manifest.environments.keys())}")

        if self.routing_rules:
            total_rules = sum(len(rules) for rules in self.routing_rules.values())
            preview_text.append(f"\nRouting Rules: {total_rules}")

        return "\n".join(preview_text)

    def _ensure_assistant_exists(self, assistant_name: str, config_overrides: Optional[Dict[str, Any]] = None):
        """
        Ensure assistant template exists, creating it if necessary.

        Args:
            assistant_name: Name of the assistant to check/create
            config_overrides: Custom configuration for the assistant

        Raises:
            SquadTemplateCreatorError: If assistant creation fails
        """
        if not self.assistant_validator.exists(assistant_name):
            try:
                self.assistant_validator.create_template(assistant_name, config_overrides)
                console.print(f"[green]Created assistant template: {assistant_name}[/green]")
            except Exception as e:
                raise SquadTemplateCreatorError(f"Failed to create assistant template '{assistant_name}': {str(e)}")

    def validate_assistant_dependencies(self) -> ValidationResult:
        """
        Validate all assistant dependencies for the squad.

        Returns:
            ValidationResult with detailed information about missing/created assistants
        """
        assistant_names = [assistant.name for assistant in self.manifest.assistants]

        if not assistant_names:
            return ValidationResult(
                is_valid=True,
                missing_assistants=[],
                created_assistants=[],
                errors=[],
                warnings=[]
            )

        result = self.assistant_validator.validate_all_assistants(
            assistant_names,
            auto_create=self.auto_create_assistants
        )

        self._validation_result = result
        return result

    def get_validation_summary(self) -> str:
        """
        Get a human-readable summary of the last validation result.

        Returns:
            Formatted validation summary
        """
        if not self._validation_result:
            return "No validation performed yet"

        result = self._validation_result
        summary = []

        if result.is_valid:
            summary.append("[green]All assistant dependencies validated successfully[/green]")
        else:
            summary.append("[red]Assistant dependency validation failed[/red]")

        if result.created_assistants:
            summary.append(f"[cyan]Created {len(result.created_assistants)} assistant templates:[/cyan]")
            for assistant in result.created_assistants:
                summary.append(f"   - {assistant}")

        if result.missing_assistants:
            summary.append(f"[red]Missing {len(result.missing_assistants)} assistant templates:[/red]")
            for assistant in result.missing_assistants:
                summary.append(f"   - {assistant}")

        if result.errors:
            summary.append(f"[red]{len(result.errors)} errors:[/red]")
            for error in result.errors:
                summary.append(f"   - {error}")

        if result.warnings:
            summary.append(f"[yellow]{len(result.warnings)} warnings:[/yellow]")
            for warning in result.warnings:
                summary.append(f"   - {warning}")

        return "\n".join(summary)

    def _infer_role_from_name(self, assistant_name: str) -> str:
        """Infer assistant role from name."""
        name_lower = assistant_name.lower()

        if any(word in name_lower for word in ['triage', 'reception', 'front', 'main']):
            return 'primary_contact'
        elif any(word in name_lower for word in ['book', 'schedule', 'appointment', 'calendar']):
            return 'booking_specialist'
        elif any(word in name_lower for word in ['info', 'information', 'research', 'data']):
            return 'information_specialist'
        elif any(word in name_lower for word in ['support', 'help', 'assist']):
            return 'support_specialist'
        elif any(word in name_lower for word in ['sales', 'sell', 'consult']):
            return 'sales_specialist'
        elif any(word in name_lower for word in ['manager', 'supervisor', 'escalation']):
            return 'manager'
        else:
            return 'specialist'

    def _generate_assistant_description(self, name: str, role: str) -> str:
        """Generate description for assistant based on name and role."""
        role_descriptions = {
            'primary_contact': 'First point of contact - greets clients, assesses needs, and routes to appropriate specialist',
            'booking_specialist': 'Handles all scheduling - appointments, consultations, and booking coordination',
            'information_specialist': 'Provides detailed information, research, and data analysis',
            'support_specialist': 'Handles customer support inquiries and troubleshooting',
            'sales_specialist': 'Manages sales inquiries, consultations, and client conversion',
            'manager': 'Handles escalations, complex issues, and supervisory tasks'
        }

        inferred_role = self._infer_role_from_name(name)
        return role_descriptions.get(role or inferred_role, f'Specialized assistant for {name} related tasks')

    def _generate_intelligent_routing(self):
        """Generate intelligent routing rules and destinations based on assistant roles."""
        assistants = [member["assistant_name"] for member in self.members_config["members"]]

        if len(assistants) < 2:
            return  # No routing needed for single assistant

        # Find primary contact (triage) assistant
        primary_assistant = self._find_primary_assistant()

        # Generate destinations for each assistant
        for member in self.members_config["members"]:
            assistant_name = member["assistant_name"]
            role = self._assistant_roles.get(assistant_name, 'specialist')

            # Generate destinations based on role
            destinations = self._generate_destinations_for_role(assistant_name, role, assistants)
            member["destinations"] = destinations

        # Generate routing rules
        self._generate_routing_rules()

        # Generate routing destinations config
        self._generate_routing_destinations()

    def _find_primary_assistant(self) -> Optional[str]:
        """Find the primary contact assistant."""
        for name, role in self._assistant_roles.items():
            if role == 'primary_contact' or 'triage' in role.lower():
                return name

        # Fallback to first assistant with highest priority
        primary_members = [m for m in self.members_config["members"] if m.get("priority", 2) == 1]
        if primary_members:
            return primary_members[0]["assistant_name"]

        # Fallback to first assistant
        if self.members_config["members"]:
            return self.members_config["members"][0]["assistant_name"]

        return None

    def _generate_destinations_for_role(self, assistant_name: str, role: str, all_assistants: List[str]) -> List[Dict[str, Any]]:
        """Generate destinations for an assistant based on its role."""
        destinations = []
        other_assistants = [name for name in all_assistants if name != assistant_name]

        # Check role categories more flexibly
        is_primary = role in ['primary_contact', 'receptionist', 'triage'] or 'triage' in assistant_name.lower()
        is_booking = role == 'booking_specialist' or 'booking' in assistant_name.lower() or 'schedule' in assistant_name.lower()
        is_info = role == 'information_specialist' or 'info' in assistant_name.lower() or 'information' in assistant_name.lower()

        if is_primary:
            # Primary contact/receptionist can transfer to all other assistants
            for other in other_assistants:
                destinations.extend(self._get_destinations_to_role(other, self._assistant_roles.get(other, 'specialist')))

        elif is_booking or is_info:
            # Booking and info specialists can transfer to all other assistants for complete connectivity
            for other in other_assistants:
                destinations.extend(self._get_destinations_to_role(other, self._assistant_roles.get(other, 'specialist')))

        else:
            # Other specialists can transfer to all assistants for complete connectivity
            for other in other_assistants:
                destinations.extend(self._get_destinations_to_role(other, self._assistant_roles.get(other, 'specialist')))

        return destinations

    def _get_destinations_to_role(self, assistant_name: str, role: str) -> List[Dict[str, Any]]:
        """Get destination configurations for transferring to a specific role."""
        role_configs = {
            'booking_specialist': [
                {
                    'type': 'assistant',
                    'assistant_name': assistant_name,
                    'message': '',
                    'conditions': [
                        {'intent': 'booking'},
                        {'keywords': ['schedule', 'appointment', 'booking', 'reservation', 'meet', 'visit', 'consultation']}
                    ]
                }
            ],
            'information_specialist': [
                {
                    'type': 'assistant',
                    'assistant_name': assistant_name,
                    'message': '',
                    'conditions': [
                        {'intent': 'information'},
                        {'keywords': ['information', 'details', 'research', 'data', 'analysis', 'report', 'study']}
                    ]
                }
            ],
            'support_specialist': [
                {
                    'type': 'assistant',
                    'assistant_name': assistant_name,
                    'message': '',
                    'conditions': [
                        {'intent': 'support'},
                        {'keywords': ['help', 'support', 'problem', 'issue', 'troubleshoot', 'fix']}
                    ]
                }
            ],
            'sales_specialist': [
                {
                    'type': 'assistant',
                    'assistant_name': assistant_name,
                    'message': '',
                    'conditions': [
                        {'intent': 'sales'},
                        {'keywords': ['buy', 'purchase', 'sell', 'sales', 'consultation', 'quote', 'price']}
                    ]
                }
            ],
            'primary_contact': [
                {
                    'type': 'assistant',
                    'assistant_name': assistant_name,
                    'message': '',
                    'conditions': [
                        {'intent': 'general_help'},
                        {'keywords': ['other questions', 'different help', 'main menu', 'receptionist', 'general']}
                    ]
                }
            ]
        }

        return role_configs.get(role, [
            {
                'type': 'assistant',
                'assistant_name': assistant_name,
                'message': '',
                'conditions': [
                    {'intent': 'general_help'},
                    {'keywords': ['help', 'assistance', 'support']}
                ]
            }
        ])

    def _generate_routing_rules(self):
        """Generate comprehensive routing rules."""
        assistants = list(self._assistant_roles.keys())
        primary_assistant = self._find_primary_assistant()

        self.routing_rules = {
            'priority_rules': {},
            'time_based_rules': {},
            'intent_rules': {},
            'load_balancing': {},
            'escalation_rules': {}
        }

        # Priority-based rules
        self.routing_rules['priority_rules']['urgent_inquiries'] = {
            'priority': 1,
            'description': 'Handle urgent inquiries with high priority',
            'triggers': [
                {'type': 'keyword', 'keywords': ['urgent', 'emergency', 'immediate', 'ASAP', 'critical']},
                {'type': 'sentiment', 'threshold': -0.7}
            ],
            'action': {
                'destination': primary_assistant or assistants[0],
                'bypass_queue': True,
                'immediate_transfer': True
            }
        }

        # Time-based rules
        self.routing_rules['time_based_rules']['business_hours'] = {
            'description': 'Normal business hours routing',
            'schedule': {
                'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
                'hours': '09:00-18:00',
                'timezone': 'America/New_York'
            },
            'routing': {
                'default': primary_assistant or assistants[0]
            }
        }

        # Intent-based rules for each assistant type
        for assistant_name, role in self._assistant_roles.items():
            if role == 'booking_specialist':
                self.routing_rules['intent_rules']['booking_requests'] = {
                    'description': 'Route booking requests to booking specialist',
                    'triggers': [
                        {'type': 'intent', 'intents': ['schedule_appointment', 'booking', 'reservation']},
                        {'type': 'keyword', 'keywords': ['schedule', 'book', 'appointment', 'reservation', 'meet']}
                    ],
                    'action': {
                        'destination': assistant_name,
                        'context_required': ['preferred_time', 'contact_info']
                    }
                }
            elif role == 'information_specialist':
                self.routing_rules['intent_rules']['information_requests'] = {
                    'description': 'Route information requests to information specialist',
                    'triggers': [
                        {'type': 'intent', 'intents': ['information_request', 'research', 'data_analysis']},
                        {'type': 'keyword', 'keywords': ['information', 'details', 'research', 'data', 'analysis']}
                    ],
                    'action': {
                        'destination': assistant_name,
                        'context_required': ['inquiry_topic', 'detail_level']
                    }
                }

        # Load balancing
        self.routing_rules['load_balancing'] = {
            'strategy': 'skill_based',
            'skill_based_routing': {},
            'fallback_strategy': {
                'primary': 'skill_based',
                'secondary': 'least_busy',
                'ultimate': primary_assistant or assistants[0]
            }
        }

        # Add capacity settings for each assistant
        for assistant_name, role in self._assistant_roles.items():
            capacity = self._get_capacity_for_role(role)
            skills = self._get_skills_for_role(role)

            self.routing_rules['load_balancing']['skill_based_routing'][assistant_name] = {
                'skills': skills,
                'capacity': capacity
            }

        # Escalation rules
        self.routing_rules['escalation_rules'] = {
            'client_dissatisfaction': {
                'triggers': [
                    {'type': 'sentiment', 'threshold': -0.6},
                    {'type': 'keyword', 'keywords': ['angry', 'frustrated', 'manager', 'complaint', 'unhappy']},
                    {'type': 'call_duration', 'threshold': 900}
                ],
                'action': {
                    'destination': 'manager',
                    'context_transfer': True,
                    'priority_boost': True
                }
            },
            'technical_difficulties': {
                'triggers': [
                    {'type': 'system_error', 'error_types': ['connection_failure', 'assistant_unavailable']},
                    {'type': 'retry_limit', 'max_retries': 3}
                ],
                'action': {
                    'destination': primary_assistant or assistants[0],
                    'message': 'I apologize for the technical difficulties. Let me connect you with our manager.'
                }
            }
        }

    def _get_capacity_for_role(self, role: str) -> int:
        """Get appropriate capacity for assistant role."""
        capacities = {
            'primary_contact': 8,
            'booking_specialist': 5,
            'information_specialist': 6,
            'support_specialist': 7,
            'sales_specialist': 4,
            'manager': 3
        }
        return capacities.get(role, 5)

    def _get_skills_for_role(self, role: str) -> List[str]:
        """Get skills for assistant role."""
        skills_map = {
            'primary_contact': ['customer_service', 'needs_assessment', 'call_routing', 'general_inquiry'],
            'booking_specialist': ['appointment_scheduling', 'calendar_management', 'consultation_booking'],
            'information_specialist': ['research', 'data_analysis', 'information_delivery', 'report_generation'],
            'support_specialist': ['customer_support', 'troubleshooting', 'problem_solving', 'technical_assistance'],
            'sales_specialist': ['sales_consultation', 'client_conversion', 'product_knowledge', 'negotiation'],
            'manager': ['escalation_handling', 'complex_issues', 'supervisory_tasks', 'client_relations']
        }
        return skills_map.get(role, ['general_assistance'])

    def _generate_routing_destinations(self):
        """Generate routing destinations configuration."""
        assistants = list(self._assistant_roles.keys())

        self.routing_destinations = {
            'assistant_destinations': {},
            'external_destinations': {},
            'after_hours_destinations': {}
        }

        # Generate assistant-to-assistant transfers
        for i, (source_name, source_role) in enumerate(self._assistant_roles.items()):
            for j, (target_name, target_role) in enumerate(self._assistant_roles.items()):
                if i != j:  # Don't create self-transfers
                    transfer_key = f"{source_name}_to_{target_name}"

                    self.routing_destinations['assistant_destinations'][transfer_key] = {
                        'type': 'assistant',
                        'source': source_name,
                        'target': target_name,
                        'conditions': self._get_transfer_conditions(source_role, target_role),
                        'message': ''
                    }

        # External destinations (placeholders)
        self.routing_destinations['external_destinations'] = {
            'manager': {
                'type': 'number',
                'number': '${MANAGER_PHONE}',
                'sources': assistants,
                'conditions': [
                    {'keywords': ['manager', 'supervisor', 'complaint', 'escalate']},
                    {'intent': 'escalation'}
                ],
                'message': ''
            },
            'emergency_line': {
                'type': 'number',
                'number': '${EMERGENCY_CONTACT}',
                'sources': [self._find_primary_assistant()] if self._find_primary_assistant() else assistants[:1],
                'conditions': [
                    {'keywords': ['emergency', 'urgent', 'immediate help']},
                    {'urgency': 'critical'}
                ],
                'message': ''
            }
        }

        # After-hours destinations
        self.routing_destinations['after_hours_destinations'] = {
            'after_hours_voicemail': {
                'type': 'voicemail',
                'number': '${MAIN_VOICEMAIL}',
                'active_hours': '18:01-08:59',
                'message': ''
            },
            'weekend_routing': {
                'type': 'assistant',
                'target': self._find_primary_assistant() or assistants[0],
                'active_days': ['saturday', 'sunday'],
                'conditions': [
                    {'keywords': ['urgent', 'emergency']}
                ],
                'message': ''
            }
        }

    def _get_transfer_conditions(self, source_role: str, target_role: str) -> List[Dict[str, Any]]:
        """Get transfer conditions between roles."""
        if source_role == 'primary_contact':
            if target_role == 'booking_specialist':
                return [
                    {'keywords': ['schedule', 'appointment', 'booking', 'reservation', 'meet']},
                    {'intent': 'booking_request'}
                ]
            elif target_role == 'information_specialist':
                return [
                    {'keywords': ['information', 'details', 'research', 'data', 'analysis']},
                    {'intent': 'information_request'}
                ]
            elif target_role == 'support_specialist':
                return [
                    {'keywords': ['help', 'support', 'problem', 'issue', 'troubleshoot']},
                    {'intent': 'support_request'}
                ]
            elif target_role == 'sales_specialist':
                return [
                    {'keywords': ['buy', 'purchase', 'sell', 'sales', 'consultation', 'quote']},
                    {'intent': 'sales_inquiry'}
                ]

        # Default conditions for transfers back to primary contact
        if target_role == 'primary_contact':
            return [
                {'keywords': ['other questions', 'different help', 'main menu', 'general']},
                {'intent': 'general_help'}
            ]

        # Default conditions
        return [
            {'keywords': ['help', 'assistance']},
            {'intent': 'general_help'}
        ]

    def _create_routing_files(self, template_path: Path):
        """Create routing directory and files."""
        routing_dir = template_path / "routing"
        routing_dir.mkdir(exist_ok=True)

        # Create destinations.yaml
        destinations_file = routing_dir / "destinations.yaml"
        with open(destinations_file, 'w', encoding='utf-8') as f:
            f.write("# Routing Destinations Configuration\n")
            f.write("# Define how assistants can transfer to each other or external systems\n\n")
            yaml.dump(self.routing_destinations, f, default_flow_style=False, sort_keys=False)