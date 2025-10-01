"""Receptionist deployment service for template-based clinic setup."""

import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re

from ..core.client import VapiClient
from ..core.config import ConfigManager
from ..core.exceptions import VapiToolsError
from ..core.logging import get_logger
from .organization import OrganizationService
from .backup import BackupService
from .config_adapter import ConfigAdapter
from ..utils.template_processor import load_emergency_transfer_template


class ReceptionistDeploymentError(VapiToolsError):
    """Exception raised during receptionist deployment."""
    pass


class ReceptionistDeploymentService:
    """Service for deploying receptionist systems from templates."""
    
    def __init__(self, client: VapiClient = None, config_manager: ConfigManager = None, organization_id: Optional[str] = None):
        """Initialize the deployment service.
        
        Args:
            client: VAPI client instance
            config_manager: Configuration manager instance
            organization_id: Organization ID override
        """
        self.config_manager = config_manager or ConfigManager()
        self.client = client or VapiClient(self.config_manager, organization_id)
        self.organization_service = OrganizationService(self.client, self.config_manager)
        self.backup_service = BackupService(self.client, self.config_manager, organization_id)
        self.logger = get_logger(__name__)
        
        # Get project root for template paths
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.templates_dir = self.project_root / "templates"
    
    def load_template(self, template_name: str = "receptionist_template.yaml") -> Dict[str, Any]:
        """Load a receptionist template.
        
        Args:
            template_name: Name of the template file
            
        Returns:
            Template configuration dictionary
        """
        template_path = self.templates_dir / template_name
        
        if not template_path.exists():
            raise ReceptionistDeploymentError(f"Template not found: {template_path}")
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = yaml.safe_load(f)
            
            self.logger.info(f"Loaded template: {template_name}")
            return template
        except Exception as e:
            raise ReceptionistDeploymentError(f"Failed to load template {template_name}: {e}")
    
    def load_config(self, config_name: str = "dental_clinic_default.yaml") -> Dict[str, Any]:
        """Load deployment configuration.
        
        Args:
            config_name: Name of the config file
            
        Returns:
            Configuration dictionary
        """
        config_path = self.templates_dir / "configs" / config_name
        
        if not config_path.exists():
            raise ReceptionistDeploymentError(f"Config not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.logger.info(f"Loaded config: {config_name}")
            return config
        except Exception as e:
            raise ReceptionistDeploymentError(f"Failed to load config {config_name}: {e}")
    
    def load_prompt_template(self, prompt_name: str, prompts_folder: Optional[str] = None) -> str:
        """Load a prompt template.
        
        Args:
            prompt_name: Name of the prompt file
            prompts_folder: Custom prompts folder - can be:
                         - Legacy: folder name under templates/prompts/ (e.g., "smith_clinic_prompts")
                         - New: clinic name for clinic/{name}/prompts/ structure (e.g., "martin_clinic")
            
        Returns:
            Prompt template content
        """
        # Try custom prompts folder first if specified
        if prompts_folder:
            # Try new clinic structure first: clinics/{name}/prompts/
            clinic_prompt_path = self.project_root / "clinics" / prompts_folder / "prompts" / prompt_name
            if clinic_prompt_path.exists():
                try:
                    with open(clinic_prompt_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    self.logger.info(f"Loaded clinic prompt template: clinics/{prompts_folder}/prompts/{prompt_name}")
                    return content
                except Exception as e:
                    self.logger.warning(f"Failed to load clinic prompt {clinic_prompt_path}: {e}")
            
            # Fall back to legacy structure: templates/prompts/{folder}/
            legacy_prompt_path = self.templates_dir / "prompts" / prompts_folder / prompt_name
            if legacy_prompt_path.exists():
                try:
                    with open(legacy_prompt_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    self.logger.info(f"Loaded custom prompt template: {prompts_folder}/{prompt_name}")
                    return content
                except Exception as e:
                    self.logger.warning(f"Failed to load custom prompt {legacy_prompt_path}: {e}")
                    # Fall through to default prompts
        
        # Fall back to default prompts folder
        prompt_path = self.templates_dir / "prompts" / prompt_name
        
        if not prompt_path.exists():
            raise ReceptionistDeploymentError(f"Prompt template not found: {prompt_path}")
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.logger.debug(f"Loaded default prompt template: {prompt_name}")
            return content
        except Exception as e:
            raise ReceptionistDeploymentError(f"Failed to load prompt template {prompt_name}: {e}")
    
    def substitute_variables(self, content: str, variables: Dict[str, Any]) -> str:
        """Substitute template variables in content.
        
        Args:
            content: Content with template variables
            variables: Dictionary of variable values
            
        Returns:
            Content with variables substituted
        """
        import re
        
        result = content
        
        # Flatten nested dictionaries for dot notation
        flattened = self._flatten_dict(variables)
        
        # First pass: replace known variables
        for key, value in flattened.items():
            # Replace both {{KEY}} and {{key}} with value for flexibility
            pattern_upper = f"{{{{{key.upper()}}}}}"
            pattern_lower = f"{{{{{key.lower()}}}}}"
            result = result.replace(pattern_upper, str(value))
            result = result.replace(pattern_lower, str(value))
        
        # Second pass: find any remaining template variables and handle gracefully
        remaining_vars = re.findall(r'\{\{([^}]+)\}\}', result)
        if remaining_vars:
            self.logger.warning(f"Unresolved template variables found: {remaining_vars}")
            # Replace unresolved variables with sensible defaults
            for var in remaining_vars:
                if 'WEBSITE' in var.upper() and 'SPELL' in var.upper():
                    result = result.replace(f"{{{{{var}}}}}", "[site web non configuré]")
                elif 'WEBSITE' in var.upper():
                    result = result.replace(f"{{{{{var}}}}}", "non configuré")
                else:
                    # Remove unresolved variables or replace with placeholder
                    result = result.replace(f"{{{{{var}}}}}", "[information non disponible]")
        
        return result
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary for dot notation access.
        
        Args:
            d: Dictionary to flatten
            parent_key: Parent key for recursion
            sep: Separator for nested keys
            
        Returns:
            Flattened dictionary
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def generate_versioned_names(self, base_config: Dict[str, Any]) -> Dict[str, str]:
        """Generate version-based names for assistants and squad.
        
        Args:
            base_config: Base configuration with names and version
            
        Returns:
            Dictionary with versioned names
        """
        # Support both new nested structure and old flat structure
        if 'variables' in base_config:
            # New structure: values are in variables section
            clinic_name = base_config.get('variables', {}).get('clinic_name', 'Clinic')
            receptionist_name = base_config.get('variables', {}).get('receptionist_name', 'Assistant')
            version = base_config.get('variables', {}).get('version', '1.0')
        else:
            # Old structure: values are at root level
            clinic_name = base_config.get('clinic_name', 'Clinic')
            receptionist_name = base_config.get('receptionist_name', 'Assistant')
            version = base_config.get('version', '1.0')
        
        # Sanitize names for VAPI (function names cannot contain dots)
        clinic_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', clinic_name)
        receptionist_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', receptionist_name)
        version_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', version)
        
        return {
            'squad_name': f"{clinic_safe}_receptionist_v{version_safe}",
            'greeter_name': f"{receptionist_safe}_Greeter_v{version_safe}",
            'emergency_name': f"{receptionist_safe}_Emergency_v{version_safe}",
            'note_taker_name': f"{receptionist_safe}_NoteTaker_v{version_safe}",
            'faq_name': f"{receptionist_safe}_FAQ_v{version_safe}",
            'emergency_tool_name': f"{receptionist_safe}_EmergencyTransfer_v{version_safe}"
        }
    
    def find_existing_resources(self, versioned_names: Dict[str, str]) -> Dict[str, Optional[str]]:
        """Find existing resources by name to determine if we should update or create.
        
        Args:
            versioned_names: Dictionary of resource names to search for
            
        Returns:
            Dictionary mapping resource type to existing ID (None if not found)
        """
        existing_resources = {}
        
        try:
            # Check for existing assistants
            assistants = self.client.get_assistants()
            existing_resources['assistants'] = {}
            
            for role in ['greeter', 'emergency', 'note_taker', 'faq']:
                name_key = f'{role}_name'
                target_name = versioned_names.get(name_key)
                if target_name:
                    for assistant in assistants:
                        if assistant.get('name') == target_name:
                            existing_resources['assistants'][role] = assistant.get('id')
                            self.logger.info(f"Found existing {role} assistant: {target_name} ({assistant.get('id')})")
                            break
                    else:
                        existing_resources['assistants'][role] = None
            
            # Check for existing squad
            squads = self.client.get_squads()
            existing_resources['squad'] = None
            target_squad_name = versioned_names.get('squad_name')
            if target_squad_name:
                for squad in squads:
                    if squad.get('name') == target_squad_name:
                        existing_resources['squad'] = squad.get('id')
                        self.logger.info(f"Found existing squad: {target_squad_name} ({squad.get('id')})")
                        break
            
            # Check for existing emergency transfer tool
            response = self.client._client.get("/tool")
            tools = self.client._handle_response(response, "get tools for version check")
            existing_resources['emergency_tool'] = None
            target_tool_name = versioned_names.get('emergency_tool_name')
            if target_tool_name:
                for tool in tools:
                    # Check if function name matches the versioned name
                    tool_function_name = tool.get('function', {}).get('name', '')
                    if tool_function_name == target_tool_name:
                        existing_resources['emergency_tool'] = tool.get('id')
                        self.logger.info(f"Found existing emergency tool: {target_tool_name} ({tool.get('id')})")
                        break
            
            return existing_resources
            
        except Exception as e:
            self.logger.error(f"Failed to check for existing resources: {e}")
            # Return empty dict to force creation of new resources
            return {
                'assistants': {},
                'squad': None,
                'emergency_tool': None
            }
    
    def create_or_update_emergency_transfer_tool(self, variables: Dict[str, Any], existing_tool_id: Optional[str] = None) -> str:
        """Create or update a transferCall tool for emergency transfers using clinic configuration.
        
        Args:
            variables: Template variables including receptionist_name, emergency_phone, and emergency_transfer_tool config
            existing_tool_id: ID of existing tool to update (None to create new)
            
        Returns:
            Tool ID (created or updated)
        """
        receptionist_name = variables.get('receptionist_name', 'Assistant')
        clinic_name = variables.get('clinic_name', 'Dental Clinic')
        versioned_names = variables.get('versioned_names', {})
        
        # Get emergency transfer tool configuration from YAML (if provided)
        emergency_tool_config = variables.get('emergency_transfer_tool', {})
        
        # Get emergency phone from within the emergency_transfer_tool section, fallback to root level
        emergency_phone = emergency_tool_config.get('emergency_phone') or variables.get('emergency_phone', '+12262414527')
        
        try:
            # Load the emergency transfer template as a fallback for structure
            template = load_emergency_transfer_template()
            
            # Prepare template variables with YAML overrides and versioned names
            # Use versioned function name if no custom function_name is provided
            default_function_name = versioned_names.get('emergency_tool_name', f"{receptionist_name.lower()}_emergency_transfer")
            
            template_variables = {
                'emergency_phone': emergency_phone,
                'function_name': emergency_tool_config.get('function_name', default_function_name),
                'function_description': emergency_tool_config.get(
                    'function_description',
                    f"Use this tool to transfer emergency calls for {receptionist_name} at {clinic_name} v{variables.get('version', '1.0')}"
                ),
                'emergency_message_french': emergency_tool_config.get(
                    'emergency_message_french',
                    "Je comprends parfaitement. Pour une urgence, la meilleure chose à faire est de vous mettre en contact directement avec notre équipe. Je vous transfère tout de suite. Veuillez rester en ligne."
                ),
                'transfer_mode': emergency_tool_config.get('transfer_mode', 'blind-transfer'),
                'sip_verb': emergency_tool_config.get('sip_verb', 'refer')
            }
            
            # Validate template variables
            validation_errors = template.validate_variables(template_variables)
            if validation_errors:
                error_msgs = [f"{var}: {error}" for var, error in validation_errors.items()]
                raise ReceptionistDeploymentError(f"Emergency tool template validation failed: {'; '.join(error_msgs)}")
            
            # Process template to get tool configuration
            tool_config = template.process(template_variables)
            
            # Apply additional YAML-specific overrides to the final config
            if 'destinations' in tool_config and len(tool_config['destinations']) > 0:
                destination = tool_config['destinations'][0]
                
                # Override destination description if specified in YAML
                if emergency_tool_config.get('destination_description'):
                    destination['description'] = emergency_tool_config['destination_description']
                
                # Override numberE164CheckEnabled if specified in YAML
                if 'number_e164_check_enabled' in emergency_tool_config:
                    destination['numberE164CheckEnabled'] = emergency_tool_config['number_e164_check_enabled']
            
            # Create or update the tool using VAPI client
            if existing_tool_id:
                # Update existing tool - remove type property for PATCH
                update_config = tool_config.copy()
                if 'type' in update_config:
                    del update_config['type']
                
                response = self.client._client.patch(f"/tool/{existing_tool_id}", json=update_config)
                result = self.client._handle_response(response, f"update emergency transfer tool {existing_tool_id}")
                tool_id = existing_tool_id
                action = "Updated"
            else:
                # Create new tool
                response = self.client._client.post("/tool", json=tool_config)
                result = self.client._handle_response(response, "create emergency transfer tool")
                tool_id = result.get('id')
                if not tool_id:
                    raise ReceptionistDeploymentError("Failed to create emergency transfer tool: no ID returned")
                action = "Created"
            
            self.logger.info(f"{action} emergency transfer tool: {template_variables['function_name']} ({tool_id})")
            self.logger.info(f"Emergency transfer configured for: {emergency_phone}")
            return tool_id
            
        except Exception as e:
            raise ReceptionistDeploymentError(f"Failed to create emergency transfer tool: {e}")

    def create_or_update_assistant_from_template(self, assistant_config: Dict[str, Any], variables: Dict[str, Any], existing_assistant_id: Optional[str] = None) -> str:
        """Create or update a single assistant from template configuration.
        
        Args:
            assistant_config: Assistant configuration from template
            variables: Template variables
            existing_assistant_id: ID of existing assistant to update (None to create new)
            
        Returns:
            Assistant ID (created or updated)
        """
        # Load and substitute prompt template
        prompt_template_name = assistant_config.get('prompt_template', 'greeter_prompt.txt')
        prompts_folder = variables.get('prompts_folder')
        prompt_content = self.load_prompt_template(prompt_template_name, prompts_folder)
        final_prompt = self.substitute_variables(prompt_content, variables)
        
        # Build assistant data
        assistant_data = {
            "name": variables.get('assistant_name', 'Assistant'),
            "model": {
                "model": variables.get('llm_model', 'gpt-4o-mini'),
                "provider": variables.get('llm_provider', 'openai'),
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": final_prompt
                    }
                ]
            },
            "voice": self._build_voice_config(variables),
            "transcriber": {
                "provider": variables.get('transcriber_provider', 'azure'),
                "language": variables.get('transcriber_language', 'fr-CA')
            },
            "firstMessage": "",
            "voicemailMessage": "Please call back when you're available.",
            "endCallFunctionEnabled": True,
            "endCallMessage": variables.get('end_call_message', "Merci de votre appel. Au revoir et bonne journée!"),
            "firstMessageMode": "assistant-speaks-first-with-model-generated-message",
            "serverMessages": ["end-of-call-report", "tool-calls"]
        }
        
        # Add analysis plans if configured (only for greeter assistant)
        assistant_role = assistant_config.get('role', '')
        if variables.get('enable_analysis_plans', False) and assistant_role == 'greeter':
            assistant_data["analysisPlan"] = {}
            
            # Add summary plan for greeter assistant
            assistant_data["analysisPlan"]["summaryPlan"] = self._build_summary_plan(variables)
            
            # Add structured data plan for greeter assistant
            if variables.get('structured_data_plan', {}).get('enabled', False):
                assistant_data["analysisPlan"]["structuredDataPlan"] = self._build_structured_data_plan(variables)
        
        # Add tools based on assistant type - skip for now to focus on basic deployment
        # TODO: Implement tool creation and attachment
        
        # Add webhook if configured
        # Support both old flat structure and new nested webhooks structure
        webhooks = variables.get('webhooks', {})
        webhook_url = webhooks.get('server_url') or variables.get('webhook_url')
        
        if webhook_url and webhook_url != "https://example.com/webhook":
            # Build headers - merge both sources
            headers = {}
            
            # Add headers from webhooks.headers
            if webhooks.get('headers'):
                headers.update(webhooks['headers'])
            
            # Legacy support - add individual fields if not in webhooks.headers
            if 'name' not in headers:
                headers['name'] = variables.get('receptionist_name', 'Assistant')
            if 'X-zenicall-auth' not in headers:
                headers['X-zenicall-auth'] = variables.get('webhook_auth_key', 'MaClefPriveSto3!')
                
            assistant_data["server"] = {
                "url": webhook_url,
                "timeoutSeconds": webhooks.get('timeout_seconds', 20),
                "headers": headers
            }
        
        try:
            # Log assistant data for debugging (without sensitive info)
            debug_data = {k: v for k, v in assistant_data.items() if k not in ['model']}
            if 'analysisPlan' in assistant_data:
                debug_data['analysisPlan'] = {
                    'summaryPlan': 'configured' if 'summaryPlan' in assistant_data.get('analysisPlan', {}) else 'not configured',
                    'structuredDataPlan': 'configured' if 'structuredDataPlan' in assistant_data.get('analysisPlan', {}) else 'not configured'
                }
                # Log that structured data plan is configured
                if 'structuredDataPlan' in assistant_data.get('analysisPlan', {}):
                    self.logger.info("Structured data plan configured for assistant")
            self.logger.debug(f"Assistant configuration: {debug_data}")
            
            # Create or update assistant
            if existing_assistant_id:
                # Update existing assistant
                response = self.client._client.patch(f"/assistant/{existing_assistant_id}", json=assistant_data)
                result = self.client._handle_response(response, f"update assistant {assistant_data['name']}")
                assistant_id = existing_assistant_id
                action = "Updated"
            else:
                # Create new assistant
                response = self.client._client.post("/assistant", json=assistant_data)
                result = self.client._handle_response(response, f"create assistant {assistant_data['name']}")
                
                assistant_id = result.get('id')
                if not assistant_id:
                    raise ReceptionistDeploymentError(f"Failed to create assistant: no ID returned")
                action = "Created"
            
            self.logger.info(f"{action} assistant: {assistant_data['name']} ({assistant_id})")
            return assistant_id
            
        except Exception as e:
            raise ReceptionistDeploymentError(f"Failed to create/update assistant {assistant_data['name']}: {e}")
    
    def attach_tool_to_assistant(self, assistant_id: str, tool_id: str) -> None:
        """Attach a tool to an assistant.
        
        Args:
            assistant_id: ID of the assistant to attach the tool to
            tool_id: ID of the tool to attach
        """
        try:
            self.logger.info(f"Attaching tool {tool_id} to assistant {assistant_id}")
            
            # Get current assistant data with retry in case assistant was just updated
            max_retries = 3
            current_assistant = None
            
            for attempt in range(max_retries):
                try:
                    response = self.client._client.get(f"/assistant/{assistant_id}")
                    current_assistant = self.client._handle_response(response, f"get assistant {assistant_id}")
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        self.logger.warning(f"Attempt {attempt + 1} failed to get assistant {assistant_id}: {e}. Retrying...")
                        import time
                        time.sleep(1)  # Wait 1 second before retry
                    else:
                        raise e
            
            if not current_assistant:
                raise ReceptionistDeploymentError(f"Could not retrieve assistant {assistant_id} after {max_retries} attempts")
            
            # Add the tool to the model's toolIds
            if 'model' not in current_assistant:
                current_assistant['model'] = {}
            if 'toolIds' not in current_assistant['model']:
                current_assistant['model']['toolIds'] = []
            
            # Add tool if not already present
            if tool_id not in current_assistant['model']['toolIds']:
                current_assistant['model']['toolIds'].append(tool_id)
                
                # Update the assistant
                update_response = self.client._client.patch(f"/assistant/{assistant_id}", json={
                    'model': current_assistant['model']
                })
                
                if update_response.status_code == 200:
                    self.logger.info(f"Successfully attached tool {tool_id} to assistant {assistant_id}")
                else:
                    error_msg = update_response.text
                    raise ReceptionistDeploymentError(f"Failed to attach tool to assistant: {error_msg}")
            else:
                self.logger.info(f"Tool {tool_id} already attached to assistant {assistant_id}")
            
        except Exception as e:
            raise ReceptionistDeploymentError(f"Failed to attach tool {tool_id} to assistant {assistant_id}: {e}")
    
    def create_or_update_squad_from_template(self, template: Dict[str, Any], variables: Dict[str, Any], assistant_ids: Dict[str, str], existing_squad_id: Optional[str] = None) -> str:
        """Create or update a squad from template configuration.
        
        Args:
            template: Squad template configuration
            variables: Template variables
            assistant_ids: Mapping of assistant roles to their IDs
            existing_squad_id: ID of existing squad to update (None to create new)
            
        Returns:
            Squad ID (created or updated)
        """
        # Use the versioned squad name instead of template name
        versioned_names = variables.get('versioned_names', {})
        squad_name = versioned_names.get('squad_name', f"{variables.get('clinic_name', 'Clinic')}_receptionist_v{variables.get('version', '1.0')}")
        
        # Build squad members from assistant IDs
        members = []
        for member_template in template.get('squad', {}).get('members', []):
            role = member_template.get('assistant_template')
            if role in assistant_ids:
                # Build proper assistant overrides to prevent VAPI backend from overriding with empty values
                assistant_overrides = self._build_assistant_overrides(variables)
                
                member_data = {
                    "assistantId": assistant_ids[role],
                    "assistantOverrides": assistant_overrides,
                    "assistantDestinations": []
                }
                
                # Create transfer destinations to other squad members
                for other_role, other_assistant_id in assistant_ids.items():
                    if other_role != role:  # Don't add self as destination
                        # Get the assistant name for this role from versioned_names
                        name_key = f'{other_role}_name'
                        other_assistant_name = versioned_names.get(name_key, f"{variables.get('receptionist_name', 'Assistant')}-{other_role.title()}")
                        member_data["assistantDestinations"].append({
                            "type": "assistant",
                            "assistantName": other_assistant_name,
                            "message": "Patientez un instant s'il vous plaît..."
                        })
                
                members.append(member_data)
        
        # Build squad data
        squad_data = {
            "name": squad_name,
            "members": members
        }
        
        try:
            # Create or update squad
            if existing_squad_id:
                # Update existing squad
                response = self.client._client.patch(f"/squad/{existing_squad_id}", json=squad_data)
                result = self.client._handle_response(response, f"update squad {squad_name}")
                squad_id = existing_squad_id
                action = "Updated"
            else:
                # Create new squad
                response = self.client.create_squad(squad_data)
                squad_id = response.get('id')
                if not squad_id:
                    raise ReceptionistDeploymentError(f"Failed to create squad: no ID returned")
                action = "Created"
            
            self.logger.info(f"{action} squad: {squad_name} ({squad_id})")
            return squad_id
            
        except Exception as e:
            raise ReceptionistDeploymentError(f"Failed to create/update squad {squad_name}: {e}")
    
    def deploy_receptionist(self, clinic_config: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """Deploy a complete receptionist system from template.
        
        Args:
            clinic_config: Clinic-specific configuration (supports both old and new formats)
            dry_run: If True, don't actually create resources
            
        Returns:
            Deployment result with created resource IDs
        """
        # Normalize configuration to handle both old and new formats
        normalized_config = ConfigAdapter.normalize_config(clinic_config)
        
        # Get clinic name for display
        clinic_display_name = (
            normalized_config.get('clinic_name') or
            normalized_config.get('variables', {}).get('clinic_name') or
            normalized_config.get('clinic', {}).get('name', 'Unknown Clinic')
        )
            
        self.logger.info(f"Starting receptionist deployment for {clinic_display_name}")
        
        if dry_run:
            self.logger.info("DRY RUN MODE - No resources will be created")
        
        try:
            # Load template and default config
            template = self.load_template()
            default_config = self.load_config()
            
            # Deep merge configurations to handle nested structures
            def deep_merge(base: dict, override: dict) -> dict:
                """Recursively merge override into base."""
                result = base.copy()
                for key, value in override.items():
                    if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                        result[key] = deep_merge(result[key], value)
                    else:
                        result[key] = value
                return result
            
            # Merge configurations (normalized_config overrides defaults)
            final_config = deep_merge(default_config, normalized_config)
            
            # Flatten variables for backward compatibility
            # If new structure with variables exists, also put them at root for old code
            if 'variables' in final_config:
                for key, value in final_config['variables'].items():
                    if key not in final_config:  # Don't override existing root-level values
                        final_config[key] = value
            
            # Resolve environment variables and secrets
            final_config = self._resolve_secrets(final_config)
            
            # Generate version-based names
            versioned_names = self.generate_versioned_names(final_config)
            final_config.update(versioned_names)
            final_config['versioned_names'] = versioned_names
            
            # Check for existing resources if not in dry run
            existing_resources = {}
            if not dry_run:
                existing_resources = self.find_existing_resources(versioned_names)
                
                # Log what will be updated vs created
                update_count = 0
                create_count = 0
                
                for role in ['greeter', 'emergency', 'note_taker', 'faq']:
                    if existing_resources.get('assistants', {}).get(role):
                        update_count += 1
                    else:
                        create_count += 1
                
                if existing_resources.get('squad'):
                    update_count += 1
                else:
                    create_count += 1
                    
                if existing_resources.get('emergency_tool'):
                    update_count += 1
                else:
                    create_count += 1
                
                self.logger.info(f"Version {final_config.get('version', '1.0')} deployment: {update_count} updates, {create_count} new resources")
            
            # Create backup before deployment
            if not dry_run and final_config.get('backup_config', {}).get('auto_backup_before_deployment', True):
                self.logger.info("Creating backup before deployment...")
                try:
                    # Try receptionist-specific backup first
                    self.backup_receptionist(final_config, dry_run=False)
                except Exception as e:
                    # Fall back to general backup if receptionist backup fails
                    self.logger.warning(f"Receptionist backup failed ({e}), falling back to general backup...")
                    self.backup_service.backup_all()
            
            deployment_result = {
                'clinic_name': final_config.get('clinic_name', 'Unknown Clinic'),
                'receptionist_name': final_config.get('receptionist_name', 'Assistant'),
                'deployment_time': datetime.now().isoformat(),
                'organization': self.organization_service.get_organization_name_directly(),
                'assistants': {},
                'squad_id': None,
                'phone_number_id': None,
                'emergency_transfer_tool_id': None,
                'dry_run': dry_run
            }
            
            if dry_run:
                deployment_result['message'] = "Dry run completed - no resources created"
                deployment_result['planned_names'] = versioned_names
                deployment_result['version'] = final_config.get('version', '1.0')
                return deployment_result
            
            # Step 1: Create or update emergency transfer tool first
            existing_tool_id = existing_resources.get('emergency_tool')
            action = "Updating" if existing_tool_id else "Creating"
            self.logger.info(f"{action} emergency transfer tool...")
            emergency_tool_id = self.create_or_update_emergency_transfer_tool(final_config, existing_tool_id)
            deployment_result['emergency_transfer_tool_id'] = emergency_tool_id
            
            # Step 2: Create or update all assistants
            self.logger.info("Creating/updating assistants...")
            assistant_ids = {}
            
            # Process each assistant role
            for role, assistant_template in template['assistants'].items():
                name_key = f'{role}_name'
                existing_assistant_id = existing_resources.get('assistants', {}).get(role)
                action = "Updating" if existing_assistant_id else "Creating"
                
                self.logger.info(f"{action} {role} assistant...")
                
                role_config = final_config.copy()
                role_config['assistant_name'] = versioned_names[name_key]
                
                # Add versioned assistant names for transfer calls in prompts
                role_config['EMERGENCY_ASSISTANT_NAME'] = versioned_names.get('emergency_name', 'Assistant_Emergency_v1_0')
                role_config['NOTE_TAKER_ASSISTANT_NAME'] = versioned_names.get('note_taker_name', 'Assistant_NoteTaker_v1_0')
                role_config['FAQ_ASSISTANT_NAME'] = versioned_names.get('faq_name', 'Assistant_FAQ_v1_0')
                role_config['GREETER_ASSISTANT_NAME'] = versioned_names.get('greeter_name', 'Assistant_Greeter_v1_0')
                
                # Add role to assistant template so we know which assistant type this is
                assistant_template_with_role = assistant_template.copy()
                assistant_template_with_role['role'] = role
                
                assistant_id = self.create_or_update_assistant_from_template(
                    assistant_template_with_role,
                    role_config,
                    existing_assistant_id
                )
                
                assistant_ids[role] = assistant_id
                deployment_result['assistants'][role] = {
                    'id': assistant_id,
                    'name': versioned_names[name_key],
                    'action': action.lower()
                }
                
                # Attach emergency transfer tool to emergency assistant
                if role == 'emergency':
                    self.logger.info("Attaching emergency transfer tool to emergency assistant...")
                    self.attach_tool_to_assistant(assistant_id, emergency_tool_id)
            
            # Step 3: Create or update squad with all assistants
            existing_squad_id = existing_resources.get('squad')
            squad_action = "updating" if existing_squad_id else "creating"
            self.logger.info(f"{squad_action.title()} squad...")
            squad_id = self.create_or_update_squad_from_template(template, final_config, assistant_ids, existing_squad_id)
            deployment_result['squad_id'] = squad_id
            deployment_result['squad_info'] = {
                'id': squad_id,
                'name': versioned_names.get('squad_name', 'Unknown Squad'),
                'action': squad_action
            }
            
            # Step 4: Log completion
            self.logger.info(f"Successfully created 1 emergency transfer tool, {len(assistant_ids)} assistants, and 1 squad")
            self.logger.info("Receptionist deployment completed successfully")
            deployment_result['status'] = 'completed'
            deployment_result['message'] = f"Created emergency transfer tool, {len(assistant_ids)} assistants, and 1 squad successfully"
            
            return deployment_result
            
        except Exception as e:
            self.logger.error(f"Receptionist deployment failed: {e}")
            raise ReceptionistDeploymentError(f"Deployment failed: {e}")
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List available receptionist templates.
        
        Returns:
            List of template information
        """
        templates = []
        
        if not self.templates_dir.exists():
            return templates
        
        for template_file in self.templates_dir.glob("*.yaml"):
            try:
                template = self.load_template(template_file.name)
                templates.append({
                    'name': template_file.name,
                    'template_name': template.get('template', {}).get('name', 'Unknown'),
                    'version': template.get('template', {}).get('version', '1.0'),
                    'description': template.get('template', {}).get('description', 'No description'),
                    'path': str(template_file)
                })
            except Exception as e:
                self.logger.warning(f"Failed to load template {template_file.name}: {e}")
        
        return templates
    
    def delete_clinic_deployment(self, clinic_config: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """Delete all resources for a clinic deployment based on version.
        
        Args:
            clinic_config: Clinic configuration containing name and version
            dry_run: If True, don't actually delete resources, just show what would be deleted
            
        Returns:
            Deletion result with details of deleted resources
        """
        self.logger.info(f"Starting receptionist deletion for {clinic_config.get('clinic_name', 'Unknown Clinic')} version {clinic_config.get('version', '1.0')}")
        
        if dry_run:
            self.logger.info("DRY RUN MODE - No resources will be deleted")
        
        try:
            # Generate version-based names to find resources
            versioned_names = self.generate_versioned_names(clinic_config)
            
            # Find existing resources
            existing_resources = self.find_existing_resources(versioned_names)
            
            deletion_result = {
                'clinic_name': clinic_config['clinic_name'],
                'version': clinic_config.get('version', '1.0'),
                'deletion_time': datetime.now().isoformat(),
                'organization': self.organization_service.get_organization_name_directly(),
                'deleted_assistants': {},
                'deleted_squad': None,
                'deleted_emergency_tool': None,
                'dry_run': dry_run,
                'found_resources': {}
            }
            
            # Count found resources
            found_assistants = {k: v for k, v in existing_resources.get('assistants', {}).items() if v}
            found_squad = existing_resources.get('squad')
            found_tool = existing_resources.get('emergency_tool')
            
            deletion_result['found_resources'] = {
                'assistants': len(found_assistants),
                'squad': 1 if found_squad else 0,
                'emergency_tool': 1 if found_tool else 0,
                'total': len(found_assistants) + (1 if found_squad else 0) + (1 if found_tool else 0)
            }
            
            if deletion_result['found_resources']['total'] == 0:
                self.logger.info(f"No resources found for {clinic_config['clinic_name']} version {clinic_config.get('version', '1.0')}")
                deletion_result['message'] = "No resources found to delete"
                return deletion_result
            
            if dry_run:
                deletion_result['message'] = f"Would delete {deletion_result['found_resources']['total']} resources"
                deletion_result['planned_deletions'] = {
                    'assistants': found_assistants,
                    'squad': found_squad,
                    'emergency_tool': found_tool
                }
                return deletion_result
            
            # Create backup before deletion
            if clinic_config.get('backup_config', {}).get('auto_backup_before_deletion', True):
                self.logger.info("Creating backup before deletion...")
                self.backup_service.backup_all()
            
            deleted_count = 0
            
            # Step 1: Detach tools from assistants (to avoid dependency issues)
            emergency_assistant_id = found_assistants.get('emergency')
            if emergency_assistant_id and found_tool:
                self.logger.info("Detaching emergency transfer tool from emergency assistant...")
                try:
                    self._detach_tool_from_assistant(emergency_assistant_id, found_tool)
                except Exception as e:
                    self.logger.warning(f"Failed to detach tool from assistant: {e}")
            
            # Step 2: Delete squad (removes assistant references)
            if found_squad:
                self.logger.info(f"Deleting squad {versioned_names.get('squad_name')}...")
                try:
                    response = self.client._client.delete(f"/squad/{found_squad}")
                    if response.status_code == 200:
                        deletion_result['deleted_squad'] = {
                            'id': found_squad,
                            'name': versioned_names.get('squad_name')
                        }
                        deleted_count += 1
                        self.logger.info(f"Deleted squad: {versioned_names.get('squad_name')} ({found_squad})")
                    else:
                        error_msg = response.text
                        self.logger.error(f"Failed to delete squad {found_squad}: {error_msg}")
                except Exception as e:
                    self.logger.error(f"Failed to delete squad {found_squad}: {e}")
            
            # Step 3: Delete assistants
            for role, assistant_id in found_assistants.items():
                assistant_name = versioned_names.get(f'{role}_name', f'Unknown-{role}')
                self.logger.info(f"Deleting {role} assistant {assistant_name}...")
                try:
                    response = self.client._client.delete(f"/assistant/{assistant_id}")
                    if response.status_code == 200:
                        deletion_result['deleted_assistants'][role] = {
                            'id': assistant_id,
                            'name': assistant_name
                        }
                        deleted_count += 1
                        self.logger.info(f"Deleted {role} assistant: {assistant_name} ({assistant_id})")
                    else:
                        error_msg = response.text
                        self.logger.error(f"Failed to delete assistant {assistant_id}: {error_msg}")
                except Exception as e:
                    self.logger.error(f"Failed to delete assistant {assistant_id}: {e}")
            
            # Step 4: Delete emergency transfer tool
            if found_tool:
                tool_name = versioned_names.get('emergency_tool_name')
                self.logger.info(f"Deleting emergency transfer tool {tool_name}...")
                try:
                    response = self.client._client.delete(f"/tool/{found_tool}")
                    if response.status_code == 200:
                        deletion_result['deleted_emergency_tool'] = {
                            'id': found_tool,
                            'name': tool_name
                        }
                        deleted_count += 1
                        self.logger.info(f"Deleted emergency transfer tool: {tool_name} ({found_tool})")
                    else:
                        error_msg = response.text
                        self.logger.error(f"Failed to delete tool {found_tool}: {error_msg}")
                except Exception as e:
                    self.logger.error(f"Failed to delete tool {found_tool}: {e}")
            
            self.logger.info(f"Successfully deleted {deleted_count} resources for {clinic_config['clinic_name']} version {clinic_config.get('version', '1.0')}")
            deletion_result['message'] = f"Successfully deleted {deleted_count} resources"
            deletion_result['deleted_count'] = deleted_count
            
            return deletion_result
            
        except Exception as e:
            self.logger.error(f"Receptionist deletion failed: {e}")
            raise ReceptionistDeploymentError(f"Deletion failed: {e}")
    
    def _detach_tool_from_assistant(self, assistant_id: str, tool_id: str) -> None:
        """Detach a tool from an assistant.
        
        Args:
            assistant_id: ID of the assistant to detach the tool from
            tool_id: ID of the tool to detach
        """
        try:
            # Get current assistant data
            response = self.client._client.get(f"/assistant/{assistant_id}")
            current_assistant = self.client._handle_response(response, f"get assistant {assistant_id}")
            
            # Remove the tool from the model's toolIds
            if 'model' in current_assistant and 'toolIds' in current_assistant['model']:
                if tool_id in current_assistant['model']['toolIds']:
                    current_assistant['model']['toolIds'].remove(tool_id)
                    
                    # Update the assistant
                    update_response = self.client._client.patch(f"/assistant/{assistant_id}", json={
                        'model': current_assistant['model']
                    })
                    
                    if update_response.status_code == 200:
                        self.logger.info(f"Successfully detached tool {tool_id} from assistant {assistant_id}")
                    else:
                        error_msg = update_response.text
                        raise ReceptionistDeploymentError(f"Failed to detach tool from assistant: {error_msg}")
                else:
                    self.logger.info(f"Tool {tool_id} not attached to assistant {assistant_id}")
            
        except Exception as e:
            raise ReceptionistDeploymentError(f"Failed to detach tool {tool_id} from assistant {assistant_id}: {e}")
    
    def _build_summary_plan(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Build summary plan configuration from variables.
        
        Args:
            variables: Template variables including summary plan configuration
            
        Returns:
            Summary plan dictionary for VAPI
        """
        messages = []
        
        # Load system prompt from file
        prompts_folder = variables.get('prompts_folder')
        system_prompt_content = self.load_prompt_template('summary_system_prompt.txt', prompts_folder)
        system_prompt_content = self.substitute_variables(system_prompt_content, variables)
        
        messages.append({
            "role": "system",
            "content": system_prompt_content
        })
        
        # Load user prompt from file
        user_prompt_content = self.load_prompt_template('summary_user_prompt.txt', prompts_folder)
        # Note: User prompt has template variables like {{transcript}} that VAPI will substitute
        
        messages.append({
            "role": "user", 
            "content": user_prompt_content
        })
        
        return {
            "messages": messages
        }
    
    def _build_structured_data_plan(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Build structured data plan configuration from variables.
        
        Args:
            variables: Template variables including structured data plan configuration
            
        Returns:
            Structured data plan dictionary for VAPI
        """
        # Load default schema from template if not provided in config  
        # Get project root (go up 4 levels: receptionist_deployment.py -> services -> vapi_tools -> src -> project_root)
        template_path = Path(__file__).parent.parent.parent.parent / "templates" / "analysis_plans" / "structured_data_plan_template.json"
        schema = {}
        
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                import json
                template_data = json.load(f)
                schema = template_data.get('schema', {})
                self.logger.info(f"Loaded schema from template: {len(schema)} keys")
        else:
            self.logger.error(f"Template not found: {template_path}")
        
        # Deep copy the schema to avoid modifying the original
        import copy
        schema = copy.deepcopy(schema)
        
        # Process schema - substitute doctor names if needed
        if 'properties' in schema and 'preferredDentist' in schema['properties']:
            # Build doctor options from clinic info
            doctors = variables.get('clinic_info', {}).get('doctors', '').split(', ')
            if not doctors or doctors == ['']:
                doctors = ['Dr. Drouin', 'Dr. Tremblay', 'Dr. Bourrassa']
            doctors.append('No Preference')
            
            # Update enum in schema
            schema['properties']['preferredDentist']['enum'] = doctors
        
        # Build messages from prompt files
        messages = []
        
        # Load system prompt from file
        prompts_folder = variables.get('prompts_folder')
        system_prompt_content = self.load_prompt_template('structured_data_system_prompt.txt', prompts_folder)
        
        # Keep {{schema}} placeholder - VAPI will substitute it with the actual schema
        # Do not replace {{schema}} here as VAPI expects this template variable
        
        # Substitute other variables
        system_prompt_content = self.substitute_variables(system_prompt_content, variables)
        
        messages.append({
            "role": "system",
            "content": system_prompt_content
        })
        
        # Load user prompt from file
        user_prompt_content = self.load_prompt_template('structured_data_user_prompt.txt', prompts_folder)
        # Note: User prompt has template variables like {{transcript}} that VAPI will substitute
        
        messages.append({
            "role": "user", 
            "content": user_prompt_content
        })
        
        result = {
            "enabled": True,
            "schema": schema,
            "messages": messages
        }
        
        self.logger.info(f"Final structured data plan schema has {len(schema)} keys")
        if len(schema) == 0:
            self.logger.error("Schema is empty! This will cause VAPI validation errors")
        
        return result

    def _build_voice_config(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Build voice configuration with provider-appropriate parameters.
        
        Args:
            variables: Template variables including voice configuration
            
        Returns:
            Voice configuration dictionary with only applicable parameters
        """
        provider = variables.get('voice_provider', '11labs')
        voice_id = variables.get('voice_id', '0Z7Lo7cYVyjM6WL0AP0n')
        
        # Start with mandatory parameters
        voice_config = {
            "provider": provider,
            "voiceId": voice_id
        }
        
        # Add provider-specific parameters
        if provider == '11labs':
            # ElevenLabs configuration
            voice_config.update({
                "model": variables.get('voice_model', 'eleven_multilingual_v2'),
            })
            # Only add optional parameters if they exist in variables
            if 'voice_stability' in variables:
                voice_config["stability"] = variables.get('voice_stability', 0.5)
            if 'voice_similarity_boost' in variables:
                voice_config["similarityBoost"] = variables.get('voice_similarity_boost', 0.75)
            if 'voice_style' in variables:
                voice_config["style"] = variables.get('voice_style')
            if 'voice_use_speaker_boost' in variables:
                voice_config["use_speaker_boost"] = variables.get('voice_use_speaker_boost')
            if 'voice_input_punctuation_boundaries' in variables:
                voice_config["inputPunctuationBoundaries"] = variables.get('voice_input_punctuation_boundaries', ["."])
                
        elif provider == 'cartesia':
            # Cartesia configuration with experimentalControls
            voice_config.update({
                "model": variables.get('voice_model', 'sonic-2'),
            })
            
            # Build experimentalControls from variables or pass through existing structure
            experimental_controls = {}
            
            # Check for individual voice parameters first (for backward compatibility)
            if 'voice_speed' in variables:
                experimental_controls["speed"] = variables.get('voice_speed', 'normal')
            if 'voice_emotion' in variables:
                experimental_controls["emotion"] = variables.get('voice_emotion')
            
            # Check if there's already an experimentalControls object in defaults
            defaults_experimental = variables.get('voice_experimental_controls', {})
            if defaults_experimental:
                experimental_controls.update(defaults_experimental)
            
            # Only add experimentalControls if there are parameters
            if experimental_controls:
                voice_config["experimentalControls"] = experimental_controls
                
        elif provider == 'openai':
            # OpenAI configuration
            voice_config.update({
                "model": variables.get('voice_model', 'tts-1'),
            })
            # Add OpenAI-specific optional parameters if they exist
            if 'voice_speed' in variables:
                voice_config["speed"] = variables.get('voice_speed', 1.0)
                
        elif provider == 'azure':
            # Azure configuration
            voice_config.update({
                "model": variables.get('voice_model', 'neural'),
            })
            if 'voice_style' in variables:
                voice_config["style"] = variables.get('voice_style')
            if 'voice_rate' in variables:
                voice_config["rate"] = variables.get('voice_rate')
                
        else:
            # For other providers, just add model if specified
            if 'voice_model' in variables:
                voice_config["model"] = variables.get('voice_model')
        
        self.logger.debug(f"Built voice config for {provider}: {voice_config}")
        return voice_config

    def _build_assistant_overrides(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Build assistant overrides to prevent VAPI backend from setting empty values.
        
        When VAPI backend processes squads in the editor, it overrides with defaults if 
        assistantOverrides is empty. This method ensures all squad members have consistent
        overrides based on configuration defaults.
        
        Args:
            variables: Template variables including voice/model configuration
            
        Returns:
            AssistantOverrides dictionary with model, voice, and transcriber
        """
        # Get defaults from config
        config = self.config_manager.get_config()
        defaults = config.defaults if hasattr(config, 'defaults') else None
        
        # Debug logging to see what variables we have
        self.logger.debug(f"Building assistant overrides with variables: {list(variables.keys())}")
        self.logger.debug(f"Transcriber provider from variables: {variables.get('transcriber_provider')}")
        self.logger.debug(f"Transcriber language from variables: {variables.get('transcriber_language')}")
        self.logger.debug(f"Config defaults transcriber: {defaults.transcriber if defaults else 'No defaults'}")
        
        # Also check specific variable keys
        transcriber_keys = [k for k in variables.keys() if 'transcriber' in k.lower()]
        self.logger.debug(f"All transcriber-related variables: {transcriber_keys}")
        for key in transcriber_keys:
            self.logger.debug(f"  {key}: {variables.get(key)}")
        
        # Build assistant overrides with same structure as defaults
        assistant_overrides = {}
        
        # Model override (use variables or fall back to config defaults)
        default_model = defaults.model if defaults else {}
        model_config = {
            "provider": variables.get('llm_provider', default_model.get('provider', 'openai')),
            "model": variables.get('llm_model', default_model.get('model', 'gpt-4o'))
        }
        # Add temperature if available
        if 'model_temperature' in variables:
            model_config["temperature"] = variables.get('model_temperature')
        elif default_model.get('temperature') is not None:
            model_config["temperature"] = default_model.get('temperature', 0)
        
        assistant_overrides["model"] = model_config
        
        # Voice override (use the same voice config built for assistants)
        assistant_overrides["voice"] = self._build_voice_config(variables)
        
        # Transcriber override (use variables or fall back to config defaults)
        default_transcriber = defaults.transcriber if defaults else {}
        transcriber_config = {
            "provider": variables.get('transcriber_provider', default_transcriber.get('provider', 'azure')),
            "language": variables.get('transcriber_language', default_transcriber.get('language', 'fr-CA'))
        }
        # Add model if available (for providers like Deepgram)
        if variables.get('transcriber_provider') == 'deepgram':
            transcriber_config["model"] = variables.get('transcriber_model', 'nova-2')
        
        assistant_overrides["transcriber"] = transcriber_config
        
        self.logger.debug(f"Built assistant overrides: {assistant_overrides}")
        return assistant_overrides

    def restore_from_backup(self, backup_path: str, dry_run: bool = False) -> Dict[str, Any]:
        """Restore a complete receptionist system from backup.
        
        Args:
            backup_path: Path to the backup directory or timestamp (e.g., "2025-08-05_22-25-27" or "assistants_2025-08-05_22-25-27")
            dry_run: If True, show what would be restored without making changes
            
        Returns:
            Restore result with restored resource IDs
        """
        from pathlib import Path
        import json
        
        self.logger.info(f"Starting receptionist restore from backup: {backup_path}")
        
        if dry_run:
            self.logger.info("DRY RUN MODE - No resources will be restored")
        
        # Resolve backup paths for all three types
        org_name = self.organization_service.get_organization_name_directly()
        org_backup_dir = Path("data") / "vapi_backups" / org_name.replace(' ', '_')
        
        # Extract timestamp from backup_path if it contains a prefix
        timestamp_match = None
        if '_' in backup_path:
            # Check if it's already prefixed (e.g., "assistants_2025-08-05_22-25-27")
            parts = backup_path.split('_', 1)
            if parts[0] in ['assistants', 'squads', 'tools']:
                timestamp_match = parts[1]
            else:
                timestamp_match = backup_path
        else:
            timestamp_match = backup_path
        
        # Find all three backup directories with matching timestamp
        backup_dirs = {}
        
        if Path(backup_path).is_absolute() and Path(backup_path).exists():
            # Single absolute path provided
            backup_dir = Path(backup_path)
            if 'assistants' in backup_dir.name:
                backup_dirs['assistants'] = backup_dir
            elif 'squads' in backup_dir.name:
                backup_dirs['squads'] = backup_dir
            elif 'tools' in backup_dir.name:
                backup_dirs['tools'] = backup_dir
        else:
            # Find all backup types with matching timestamp
            for backup_type in ['assistants', 'squads', 'tools']:
                possible_paths = [
                    org_backup_dir / f"{backup_type}_{timestamp_match}",
                    org_backup_dir / f"{backup_type}_{timestamp_match.replace('-', '_')}",
                    org_backup_dir / f"{backup_type}_{timestamp_match.replace('_', '-')}"
                ]
                
                for path in possible_paths:
                    if path.exists():
                        backup_dirs[backup_type] = path
                        break
        
        if not backup_dirs:
            raise ReceptionistDeploymentError(f"No backups found for timestamp: {backup_path}")
        
        self.logger.info(f"Found backups: {', '.join(f'{k}={v.name}' for k, v in backup_dirs.items())}")
        
        # Analyze what's in each backup
        restore_plan = {
            'assistants': [],
            'squads': [],
            'tools': []
        }
        
        backup_timestamps = {}
        
        # Process assistants backup
        if 'assistants' in backup_dirs:
            summary_file = backup_dirs['assistants'] / "backup_summary.json"
            if summary_file.exists():
                with open(summary_file, 'r', encoding='utf-8') as f:
                    backup_summary = json.load(f)
                
                backup_timestamps['assistants'] = backup_summary.get('backup_timestamp')
                
                # Identify receptionist components
                for assistant in backup_summary.get('assistants', []):
                    assistant_name = assistant['name']
                    # Check if this is a receptionist component (has version suffix and role pattern)
                    if any(role in assistant_name for role in ['_Greeter_', '_Emergency_', '_NoteTaker_', '_FAQ_']):
                        restore_plan['assistants'].append(assistant)
        
        # Process squads backup
        if 'squads' in backup_dirs:
            summary_file = backup_dirs['squads'] / "backup_summary.json"
            if summary_file.exists():
                with open(summary_file, 'r', encoding='utf-8') as f:
                    backup_summary = json.load(f)
                
                backup_timestamps['squads'] = backup_summary.get('backup_timestamp')
                
                # Identify receptionist squads
                for squad in backup_summary.get('squads', []):
                    squad_name = squad['name']
                    # Check if this is a receptionist squad
                    if 'receptionist' in squad_name.lower():
                        restore_plan['squads'].append(squad)
        
        # Process tools backup
        if 'tools' in backup_dirs:
            summary_file = backup_dirs['tools'] / "backup_summary.json"
            if summary_file.exists():
                with open(summary_file, 'r', encoding='utf-8') as f:
                    backup_summary = json.load(f)
                
                backup_timestamps['tools'] = backup_summary.get('backup_timestamp')
                
                # Identify receptionist-related tools (emergency transfer)
                for tool in backup_summary.get('tools', []):
                    if not isinstance(tool, dict):
                        self.logger.warning(f"Invalid tool format in backup: {tool}")
                        continue
                    
                    tool_name = tool.get('name', '')
                    tool_type = tool.get('type', '')
                    filename = tool.get('filename', '')
                    tool_id = tool.get('id', '')
                    
                    # For transferCall tools, we need to check the actual file content for function.name
                    if tool_type == 'transferCall':
                        # Load the tool file to check the function name
                        try:
                            tool_file = backup_dirs['tools'] / filename
                            if tool_file.exists():
                                with open(tool_file, 'r', encoding='utf-8') as f:
                                    tool_data = json.load(f)
                                
                                function_name = tool_data.get('function', {}).get('name', '')
                                if 'emergency_transfer' in function_name.lower():
                                    restore_plan['tools'].append(tool)
                                    continue
                        except Exception as e:
                            self.logger.warning(f"Could not read tool file {filename}: {e}")
                    
                    # For other tools, check by name  
                    if tool_name and 'emergency_transfer' in tool_name.lower():
                        restore_plan['tools'].append(tool)
        
        # Build tool names for display (need to read actual tool data for names)
        tool_names = []
        for tool in restore_plan['tools']:
            tool_name = tool.get('name')
            if not tool_name and tool.get('type') == 'transferCall':
                # Try to get function name from the backup file
                filename = tool.get('filename', '')
                if filename and 'tools' in backup_dirs:
                    try:
                        tool_file = backup_dirs['tools'] / filename
                        if tool_file.exists():
                            with open(tool_file, 'r', encoding='utf-8') as f:
                                tool_data = json.load(f)
                            tool_name = tool_data.get('function', {}).get('name', f"Tool ({tool.get('type', 'unknown')})")
                    except Exception:
                        tool_name = f"Tool ({tool.get('type', 'unknown')})"
            tool_names.append(tool_name or f"Tool ({tool.get('type', 'unknown')})")

        # Log what was found
        total_items = sum(len(items) for items in restore_plan.values())
        self.logger.info(f"Found {len(restore_plan['assistants'])} assistants, {len(restore_plan['squads'])} squads, {len(restore_plan['tools'])} tools to restore")
        
        if total_items == 0:
            raise ReceptionistDeploymentError("No receptionist components found in backup")
        
        if dry_run:
            # Show what would be restored
            result = {
                'dry_run': True,
                'backup_paths': {k: str(v) for k, v in backup_dirs.items()},
                'backup_timestamps': backup_timestamps,
                'would_restore': {
                    'assistants': len(restore_plan['assistants']),
                    'assistant_names': [a['name'] for a in restore_plan['assistants']],
                    'squads': len(restore_plan['squads']),
                    'squad_names': [s['name'] for s in restore_plan['squads']],
                    'tools': len(restore_plan['tools']),
                    'tool_names': tool_names
                }
            }
            
            # Log details
            if restore_plan['assistants']:
                self.logger.info(f"Would restore {len(restore_plan['assistants'])} assistants:")
                for assistant in restore_plan['assistants']:
                    self.logger.info(f"  - {assistant['name']} ({assistant['id']})")
            
            if restore_plan['squads']:
                self.logger.info(f"Would restore {len(restore_plan['squads'])} squads:")
                for squad in restore_plan['squads']:
                    self.logger.info(f"  - {squad['name']} ({squad['id']})")
            
            if restore_plan['tools']:
                self.logger.info(f"Would restore {len(restore_plan['tools'])} tools:")
                for i, tool in enumerate(restore_plan['tools']):
                    display_name = tool_names[i] if i < len(tool_names) else f"Tool ({tool.get('type', 'unknown')})"
                    self.logger.info(f"  - {display_name} ({tool['id']})")
            
            return result
        
        # Perform actual restore
        restored_resources = {
            'assistants': {},
            'squads': {},
            'tools': {}
        }
        
        # Create backup before restore
        self.logger.info("Creating backup before restore...")
        self.backup_service.backup_all()
        
        try:
            # First restore tools (they might be referenced by assistants)
            if restore_plan['tools'] and 'tools' in backup_dirs:
                self.logger.info("Restoring tools...")
                for tool_info in restore_plan['tools']:
                    tool_file = backup_dirs['tools'] / tool_info['filename']
                    if not tool_file.exists():
                        self.logger.warning(f"Tool file not found: {tool_file}")
                        continue
                    
                    # Load tool data from backup
                    with open(tool_file, 'r', encoding='utf-8') as f:
                        tool_data = json.load(f)
                    
                    original_id = tool_data['id']
                    # Get tool name - for transferCall tools, it's in function.name
                    tool_name = tool_data.get('name') 
                    if not tool_name and tool_data.get('function', {}).get('name'):
                        tool_name = tool_data['function']['name']
                    if not tool_name:
                        tool_name = f"Tool_{tool_data.get('type', 'unknown')}_{original_id[:8]}"
                    
                    # Remove fields that shouldn't be restored
                    fields_to_remove = ['id', 'orgId', 'createdAt', 'updatedAt']
                    for field in fields_to_remove:
                        tool_data.pop(field, None)
                    
                    self.logger.info(f"Restoring tool: {tool_name}")
                    
                    try:
                        # Check if tool with same name already exists
                        existing_tools = self.client.list_tools()
                        existing_tool = next((t for t in existing_tools if t.get('name') == tool_name), None)
                        
                        if existing_tool:
                            # Update existing tool
                            response = self.client._client.patch(f"/tool/{existing_tool['id']}", json=tool_data)
                            result = self.client._handle_response(response, f"update tool {tool_name}")
                            new_id = existing_tool['id']
                            action = "Updated"
                        else:
                            # Create new tool
                            response = self.client._client.post("/tool", json=tool_data)
                            result = self.client._handle_response(response, f"create tool {tool_name}")
                            new_id = result.get('id')
                            action = "Created"
                        
                        if not new_id:
                            raise ReceptionistDeploymentError(f"Failed to restore tool {tool_name}: no ID returned")
                        
                        restored_resources['tools'][tool_name] = {
                            'id': new_id,
                            'original_id': original_id,
                            'action': action
                        }
                        
                        self.logger.info(f"{action} tool: {tool_name} ({new_id})")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to restore tool {tool_name}: {e}")
                        raise ReceptionistDeploymentError(f"Failed to restore tool {tool_name}: {e}")
            
            # Then restore assistants
            if restore_plan['assistants'] and 'assistants' in backup_dirs:
                self.logger.info("Restoring assistants...")
                for assistant_info in restore_plan['assistants']:
                    assistant_file = backup_dirs['assistants'] / assistant_info['filename']
                    if not assistant_file.exists():
                        self.logger.warning(f"Assistant file not found: {assistant_file}")
                        continue
                    
                    # Load assistant data from backup
                    with open(assistant_file, 'r', encoding='utf-8') as f:
                        assistant_data = json.load(f)
                    
                    original_id = assistant_data['id']
                    assistant_name = assistant_data['name']
                    
                    # Remove fields that shouldn't be restored
                    fields_to_remove = ['id', 'orgId', 'createdAt', 'updatedAt']
                    for field in fields_to_remove:
                        assistant_data.pop(field, None)
                    
                    self.logger.info(f"Restoring assistant: {assistant_name}")
                    
                    try:
                        # Check if assistant with same name already exists
                        existing_assistants = self.client.list_assistants()
                        existing_assistant = next((a for a in existing_assistants if a.get('name') == assistant_name), None)
                        
                        if existing_assistant:
                            # Update existing assistant
                            response = self.client._client.patch(f"/assistant/{existing_assistant['id']}", json=assistant_data)
                            result = self.client._handle_response(response, f"update assistant {assistant_name}")
                            new_id = existing_assistant['id']
                            action = "Updated"
                        else:
                            # Create new assistant
                            response = self.client._client.post("/assistant", json=assistant_data)
                            result = self.client._handle_response(response, f"create assistant {assistant_name}")
                            new_id = result.get('id')
                            action = "Created"
                        
                        if not new_id:
                            raise ReceptionistDeploymentError(f"Failed to restore assistant {assistant_name}: no ID returned")
                        
                        restored_resources['assistants'][assistant_name] = {
                            'id': new_id,
                            'original_id': original_id,
                            'action': action
                        }
                        
                        self.logger.info(f"{action} assistant: {assistant_name} ({new_id})")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to restore assistant {assistant_name}: {e}")
                        raise ReceptionistDeploymentError(f"Failed to restore assistant {assistant_name}: {e}")
            
            # Finally restore squads (they reference assistants)
            if restore_plan['squads'] and 'squads' in backup_dirs:
                self.logger.info("Restoring squads...")
                for squad_info in restore_plan['squads']:
                    squad_file = backup_dirs['squads'] / squad_info['filename']
                    if not squad_file.exists():
                        self.logger.warning(f"Squad file not found: {squad_file}")
                        continue
                    
                    # Load squad data from backup
                    with open(squad_file, 'r', encoding='utf-8') as f:
                        squad_data = json.load(f)
                    
                    original_id = squad_data['id']
                    squad_name = squad_data['name']
                    
                    # Remove fields that shouldn't be restored
                    fields_to_remove = ['id', 'orgId', 'createdAt', 'updatedAt']
                    for field in fields_to_remove:
                        squad_data.pop(field, None)
                    
                    # Update assistant IDs in squad members if we restored them
                    if 'members' in squad_data:
                        for member in squad_data['members']:
                            if 'assistantId' in member:
                                # Find if we restored this assistant
                                for assistant_name, assistant_info in restored_resources['assistants'].items():
                                    if assistant_info['original_id'] == member['assistantId']:
                                        member['assistantId'] = assistant_info['id']
                                        self.logger.info(f"Updated assistant reference in squad: {assistant_name} -> {assistant_info['id']}")
                                        break
                    
                    self.logger.info(f"Restoring squad: {squad_name}")
                    
                    try:
                        # Check if squad with same name already exists
                        existing_squads = self.client.list_squads()
                        existing_squad = next((s for s in existing_squads if s.get('name') == squad_name), None)
                        
                        if existing_squad:
                            # Update existing squad
                            response = self.client._client.patch(f"/squad/{existing_squad['id']}", json=squad_data)
                            result = self.client._handle_response(response, f"update squad {squad_name}")
                            new_id = existing_squad['id']
                            action = "Updated"
                        else:
                            # Create new squad
                            response = self.client._client.post("/squad", json=squad_data)
                            result = self.client._handle_response(response, f"create squad {squad_name}")
                            new_id = result.get('id')
                            action = "Created"
                        
                        if not new_id:
                            raise ReceptionistDeploymentError(f"Failed to restore squad {squad_name}: no ID returned")
                        
                        restored_resources['squads'][squad_name] = {
                            'id': new_id,
                            'original_id': original_id,
                            'action': action
                        }
                        
                        self.logger.info(f"{action} squad: {squad_name} ({new_id})")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to restore squad {squad_name}: {e}")
                        raise ReceptionistDeploymentError(f"Failed to restore squad {squad_name}: {e}")
            
            # Build final result
            total_restored = sum(len(resources) for resources in restored_resources.values())
            
            result = {
                'backup_paths': {k: str(v) for k, v in backup_dirs.items()},
                'backup_timestamps': backup_timestamps,
                'restored_resources': restored_resources,
                'total_restored': total_restored,
                'restored_assistants': restored_resources['assistants'],  # For backward compatibility
                'restored_squads': restored_resources['squads'],
                'restored_tools': restored_resources['tools'],
                'organization': self.organization_service.get_organization_name_directly()
            }
            
            self.logger.info(f"Successfully restored {len(restored_resources['assistants'])} assistants, {len(restored_resources['squads'])} squads, {len(restored_resources['tools'])} tools from backup")
            return result
            
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            raise ReceptionistDeploymentError(f"Restore failed: {e}")

    def check_deployment_health(self, clinic_config: Dict[str, Any]) -> Dict[str, Any]:
        """Check health and status of a deployed receptionist system.
        
        Args:
            clinic_config: Configuration containing clinic_name, version, etc.
            
        Returns:
            Health check results with status and issues
        """
        import re
        
        self.logger.info(f"Starting health check for clinic: {clinic_config.get('clinic_name')}")
        
        # Generate expected resource names
        clinic_name = clinic_config['clinic_name']
        version = clinic_config.get('version', '1.0')
        receptionist_name = clinic_config.get('receptionist_name', 'Assistant')
        
        # Convert to safe names for matching
        clinic_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', clinic_name)
        version_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', version)
        receptionist_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', receptionist_name)
        
        # Expected names
        expected_squad_name = f"{clinic_safe}_receptionist_v{version_safe}"
        expected_tool_name = f"{receptionist_safe}_EmergencyTransfer_v{version_safe}"
        
        # Assistant roles and expected names
        assistant_roles = ['Greeter', 'Emergency', 'NoteTaker', 'FAQ']
        expected_assistant_names = [f"{receptionist_safe}_{role}_v{version_safe}" for role in assistant_roles]
        
        health_result = {
            'overall_status': 'healthy',
            'assistants': {'expected': len(assistant_roles), 'found': 0, 'details': []},
            'squad': {'exists': False, 'details': None},
            'emergency_tool': {'exists': False, 'details': None},
            'issues': []
        }
        
        try:
            # Check assistants
            all_assistants = self.client.get_assistants()
            found_assistants = []
            
            for assistant in all_assistants:
                assistant_name = assistant.get('name', '')
                if assistant_name in expected_assistant_names:
                    found_assistants.append(assistant)
                    health_result['assistants']['details'].append({
                        'name': assistant_name,
                        'id': assistant['id'],
                        'status': 'found'
                    })
            
            health_result['assistants']['found'] = len(found_assistants)
            
            # Check for missing assistants
            found_names = [a.get('name') for a in found_assistants]
            missing_assistants = [name for name in expected_assistant_names if name not in found_names]
            
            for missing_name in missing_assistants:
                health_result['issues'].append(f"Missing assistant: {missing_name}")
                health_result['assistants']['details'].append({
                    'name': missing_name,
                    'status': 'missing'
                })
            
            # Check squad
            all_squads = self.client.get_squads()
            found_squad = None
            
            for squad in all_squads:
                squad_name = squad.get('name', '')
                if squad_name == expected_squad_name:
                    found_squad = squad
                    health_result['squad']['exists'] = True
                    health_result['squad']['details'] = {
                        'name': squad_name,
                        'id': squad['id'],
                        'status': 'found'
                    }
                    break
            
            if not found_squad:
                health_result['issues'].append(f"Missing squad: {expected_squad_name}")
                health_result['squad']['details'] = {
                    'name': expected_squad_name,
                    'status': 'missing'
                }
            
            # Check emergency transfer tool
            all_tools = self.client.get_tools()
            found_tool = None
            
            for tool in all_tools:
                tool_name = tool.get('name', '')
                function_name = tool.get('function', {}).get('name', '') if tool.get('function') else ''
                
                if tool_name == expected_tool_name or function_name == expected_tool_name:
                    found_tool = tool
                    health_result['emergency_tool']['exists'] = True
                    health_result['emergency_tool']['details'] = {
                        'name': tool_name or function_name,
                        'id': tool['id'],
                        'type': tool.get('type'),
                        'status': 'found'
                    }
                    break
            
            if not found_tool:
                health_result['issues'].append(f"Missing emergency transfer tool: {expected_tool_name}")
                health_result['emergency_tool']['details'] = {
                    'name': expected_tool_name,
                    'status': 'missing'
                }
            
            # Determine overall status
            if health_result['issues']:
                health_result['overall_status'] = 'unhealthy'
            
            self.logger.info(f"Health check completed: {health_result['overall_status']}")
            return health_result
            
        except Exception as e:
            health_result['overall_status'] = 'error'
            health_result['issues'].append(f"Health check failed: {e}")
            self.logger.error(f"Health check error: {e}")
            return health_result

    def _resolve_secrets(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve environment variables and secrets in configuration.
        
        Supports patterns:
        - env:VAR_NAME -> os.getenv('VAR_NAME')
        - file:/path/to/secret -> read from file
        - json:/path/to/secrets.json#key -> read key from JSON file
        """
        import os
        import json
        from pathlib import Path
        
        def resolve_value(value):
            if not isinstance(value, str):
                return value
                
            # Environment variable pattern: env:VAR_NAME
            if value.startswith('env:'):
                env_var = value[4:]  # Remove 'env:' prefix
                resolved = os.getenv(env_var)
                if resolved is None:
                    self.logger.warning(f"Environment variable '{env_var}' not set")
                    return value  # Return original if not found
                self.logger.debug(f"Resolved env:{env_var} -> ***MASKED***")
                return resolved
            
            # File pattern: file:/path/to/secret
            elif value.startswith('file:'):
                file_path = Path(value[5:])  # Remove 'file:' prefix
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        resolved = f.read().strip()
                    self.logger.debug(f"Resolved file:{file_path} -> ***MASKED***")
                    return resolved
                except Exception as e:
                    self.logger.error(f"Failed to read secret from {file_path}: {e}")
                    return value  # Return original if file read fails
            
            # JSON file pattern: json:/path/to/secrets.json#key
            elif value.startswith('json:'):
                parts = value[5:].split('#', 1)  # Remove 'json:' prefix
                if len(parts) != 2:
                    self.logger.error(f"Invalid json: pattern '{value}'. Use format 'json:/path/file.json#key'")
                    return value
                
                file_path, key = parts
                try:
                    with open(Path(file_path), 'r', encoding='utf-8') as f:
                        secrets = json.load(f)
                    resolved = secrets.get(key)
                    if resolved is None:
                        self.logger.warning(f"Key '{key}' not found in {file_path}")
                        return value
                    self.logger.debug(f"Resolved json:{file_path}#{key} -> ***MASKED***")
                    return resolved
                except Exception as e:
                    self.logger.error(f"Failed to read JSON secret from {file_path}: {e}")
                    return value
            
            return value
        
        def resolve_dict(obj):
            if isinstance(obj, dict):
                return {k: resolve_dict(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [resolve_dict(item) for item in obj]
            else:
                return resolve_value(obj)
        
        return resolve_dict(config)

    def backup_receptionist(self, clinic_config: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """Backup all components of a receptionist system into a single folder.
        
        Args:
            clinic_config: Configuration containing clinic_name, version, etc.
            dry_run: If True, show what would be backed up without creating files
            
        Returns:
            Backup result with backup location and statistics
        """
        from pathlib import Path
        import json
        from datetime import datetime
        import re
        
        self.logger.info(f"Starting receptionist backup for clinic: {clinic_config.get('clinic_name')}")
        
        if dry_run:
            self.logger.info("DRY RUN MODE - No backup files will be created")
        
        # Get organization info
        org_name = self.organization_service.get_organization_name_directly()
        org_info = self.organization_service.get_organization_from_vapi()
        org_id = org_info.get('id', 'unknown')
        
        # Generate expected resource names based on clinic config
        clinic_name = clinic_config['clinic_name']
        version = clinic_config.get('version', '1.0')
        receptionist_name = clinic_config.get('receptionist_name', 'Assistant')
        
        # Convert to safe names for matching
        clinic_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', clinic_name)
        version_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', version)
        receptionist_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', receptionist_name)
        
        # Expected names
        expected_squad_name = f"{clinic_safe}_receptionist_v{version_safe}"
        expected_tool_name = f"{receptionist_safe}_EmergencyTransfer_v{version_safe}"
        
        # Assistant roles and expected names
        assistant_roles = ['Greeter', 'Emergency', 'NoteTaker', 'FAQ']
        expected_assistant_names = [f"{receptionist_safe}_{role}_v{version_safe}" for role in assistant_roles]
        
        self.logger.info(f"Looking for receptionist components:")
        self.logger.info(f"  Squad: {expected_squad_name}")
        self.logger.info(f"  Assistants: {', '.join(expected_assistant_names)}")
        self.logger.info(f"  Emergency Tool: {expected_tool_name}")
        
        # Find matching resources
        found_resources = {
            'assistants': [],
            'squads': [],
            'tools': []
        }
        
        # Find assistants
        all_assistants = self.client.get_assistants()
        for assistant in all_assistants:
            assistant_name = assistant.get('name', '')
            if assistant_name in expected_assistant_names:
                found_resources['assistants'].append(assistant)
                self.logger.info(f"Found assistant: {assistant_name} ({assistant['id']})")
        
        # Find squad
        all_squads = self.client.get_squads()
        for squad in all_squads:
            squad_name = squad.get('name', '')
            if squad_name == expected_squad_name:
                found_resources['squads'].append(squad)
                self.logger.info(f"Found squad: {squad_name} ({squad['id']})")
        
        # Find emergency transfer tool
        all_tools = self.client.get_tools()
        for tool in all_tools:
            # Check both top-level name and function name
            tool_name = tool.get('name', '')
            function_name = tool.get('function', {}).get('name', '') if tool.get('function') else ''
            
            if tool_name == expected_tool_name or function_name == expected_tool_name:
                found_resources['tools'].append(tool)
                display_name = tool_name or function_name or f"Tool ({tool.get('type', 'unknown')})"
                self.logger.info(f"Found tool: {display_name} ({tool['id']})")
        
        # Calculate totals
        total_found = sum(len(resources) for resources in found_resources.values())
        
        if total_found == 0:
            if dry_run:
                return {
                    'dry_run': True,
                    'found_resources': {
                        'assistants': 0,
                        'squads': 0,
                        'tools': 0,
                        'total': 0
                    }
                }
            else:
                raise ReceptionistDeploymentError(f"No receptionist resources found for clinic '{clinic_name}' version '{version}'")
        
        self.logger.info(f"Found {len(found_resources['assistants'])} assistants, {len(found_resources['squads'])} squads, {len(found_resources['tools'])} tools")
        
        if dry_run:
            return {
                'dry_run': True,
                'found_resources': {
                    'assistants': len(found_resources['assistants']),
                    'squads': len(found_resources['squads']),
                    'tools': len(found_resources['tools']),
                    'total': total_found
                }
            }
        
        # Create backup directory
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir_name = f"receptionist_{clinic_safe}_v{version_safe}_{timestamp}"
        
        # Use clinic-specific backup folder if provided, otherwise use global location
        if clinic_config.get('backup_folder'):
            backup_dir = Path(clinic_config['backup_folder']) / backup_dir_name
            self.logger.info(f"Using clinic-specific backup location: {backup_dir}")
        else:
            backup_dir = Path("data") / "vapi_backups" / org_name.replace(' ', '_') / backup_dir_name
            self.logger.info(f"Using global backup location: {backup_dir}")
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Creating backup in: {backup_dir}")
        
        # Backup resources
        backed_up_resources = {
            'assistants': 0,
            'squads': 0,
            'tools': 0
        }
        
        resource_details = {
            'assistants': [],
            'squads': [],
            'tools': []
        }
        
        try:
            # Backup assistants
            if found_resources['assistants']:
                assistants_dir = backup_dir / "assistants"
                assistants_dir.mkdir(exist_ok=True)
                
                for assistant in found_resources['assistants']:
                    assistant_id = assistant['id']
                    assistant_name = assistant['name']
                    
                    # Get full assistant data
                    assistant_data = self.client.get_assistant(assistant_id)
                    
                    # Save to file
                    filename = f"{assistant_name}_{assistant_id}.json"
                    file_path = assistants_dir / filename
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(assistant_data, f, indent=2, ensure_ascii=False)
                    
                    backed_up_resources['assistants'] += 1
                    resource_details['assistants'].append(assistant_name)
                    self.logger.info(f"Backed up assistant: {assistant_name}")
            
            # Backup squads
            if found_resources['squads']:
                squads_dir = backup_dir / "squads"
                squads_dir.mkdir(exist_ok=True)
                
                for squad in found_resources['squads']:
                    squad_id = squad['id']
                    squad_name = squad['name']
                    
                    # Get full squad data
                    squad_data = self.client.get_squad(squad_id)
                    
                    # Save to file
                    filename = f"{squad_name}_{squad_id}.json"
                    file_path = squads_dir / filename
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(squad_data, f, indent=2, ensure_ascii=False)
                    
                    backed_up_resources['squads'] += 1
                    resource_details['squads'].append(squad_name)
                    self.logger.info(f"Backed up squad: {squad_name}")
            
            # Backup tools
            if found_resources['tools']:
                tools_dir = backup_dir / "tools"
                tools_dir.mkdir(exist_ok=True)
                
                for tool in found_resources['tools']:
                    tool_id = tool['id']
                    tool_name = tool.get('name') or tool.get('function', {}).get('name', f"tool_{tool_id[:8]}")
                    tool_type = tool.get('type', 'unknown')
                    
                    # Get full tool data
                    tool_data = self.client.get_tool(tool_id)
                    
                    # Save to file
                    filename = f"{tool_type}_{tool_name}_{tool_id}.json"
                    file_path = tools_dir / filename
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(tool_data, f, indent=2, ensure_ascii=False)
                    
                    backed_up_resources['tools'] += 1
                    resource_details['tools'].append(tool_name)
                    self.logger.info(f"Backed up tool: {tool_name}")
            
            # Create backup summary
            backup_summary = {
                'backup_timestamp': datetime.now().isoformat(),
                'clinic_name': clinic_name,
                'version': version,
                'receptionist_name': receptionist_name,
                'organization_id': org_id,
                'organization_name': org_name,
                'backup_type': 'receptionist',
                'backed_up_resources': backed_up_resources,
                'resource_details': resource_details,
                'total_resources': sum(backed_up_resources.values())
            }
            
            summary_file = backup_dir / "backup_summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(backup_summary, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Backup completed successfully: {sum(backed_up_resources.values())} resources backed up")
            
            return {
                'organization': org_name,
                'backup_directory': str(backup_dir),
                'backup_timestamp': backup_summary['backup_timestamp'],
                'backed_up_resources': backed_up_resources,
                'resource_details': resource_details
            }
            
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            raise ReceptionistDeploymentError(f"Backup failed: {e}")

    def restore_receptionist_backup(self, backup_folder: str, dry_run: bool = False) -> Dict[str, Any]:
        """Restore all components from a receptionist backup folder.
        
        Args:
            backup_folder: Path to receptionist backup folder or just the folder name
            dry_run: If True, show what would be restored without making changes
            
        Returns:
            Restore result with restored resource IDs
        """
        from pathlib import Path
        import json
        
        self.logger.info(f"Starting receptionist backup restore from: {backup_folder}")
        
        if dry_run:
            self.logger.info("DRY RUN MODE - No resources will be restored")
        
        # Resolve backup folder path
        backup_path = Path(backup_folder)
        
        # If it's not an absolute path or doesn't exist, try to find it in the org backup directory
        if not backup_path.is_absolute() or not backup_path.exists():
            org_name = self.organization_service.get_organization_name_directly()
            org_backup_dir = Path("data") / "vapi_backups" / org_name.replace(' ', '_')
            
            # Try exact folder name first
            backup_path = org_backup_dir / backup_folder
            if not backup_path.exists():
                # Try adding the receptionist prefix if missing
                if not backup_folder.startswith('receptionist_'):
                    backup_path = org_backup_dir / f"receptionist_{backup_folder}"
                    
        if not backup_path.exists():
            raise ReceptionistDeploymentError(f"Receptionist backup folder not found: {backup_folder}")
        
        if not backup_path.is_dir():
            raise ReceptionistDeploymentError(f"Backup path is not a directory: {backup_path}")
        
        # Verify it's a receptionist backup by checking for backup_summary.json
        summary_file = backup_path / "backup_summary.json"
        if not summary_file.exists():
            raise ReceptionistDeploymentError(f"Not a valid receptionist backup: missing backup_summary.json in {backup_path}")
        
        # Load backup summary
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                backup_summary = json.load(f)
        except Exception as e:
            raise ReceptionistDeploymentError(f"Failed to read backup summary: {e}")
        
        # Verify it's a receptionist backup
        backup_type = backup_summary.get('backup_type')
        if backup_type != 'receptionist':
            raise ReceptionistDeploymentError(f"Not a receptionist backup (type: {backup_type})")
        
        self.logger.info(f"Found receptionist backup: {backup_summary.get('clinic_name', 'Unknown')} v{backup_summary.get('version', 'Unknown')}")
        
        # Analyze backup contents
        backup_info = {
            'clinic_name': backup_summary.get('clinic_name'),
            'receptionist_name': backup_summary.get('receptionist_name'), 
            'version': backup_summary.get('version'),
            'organization_name': backup_summary.get('organization_name'),
            'backup_timestamp': backup_summary.get('backup_timestamp')
        }
        
        # Find resource files
        restore_plan = {
            'assistants': [],
            'squads': [],
            'tools': []
        }
        
        # Process assistants
        assistants_dir = backup_path / "assistants"
        if assistants_dir.exists():
            for file_path in assistants_dir.glob("*.json"):
                assistant_name = file_path.stem.split('_')[0:-1]  # Remove the ID part
                assistant_name = '_'.join(assistant_name)
                restore_plan['assistants'].append({
                    'name': assistant_name,
                    'file_path': file_path
                })
        
        # Process squads
        squads_dir = backup_path / "squads"
        if squads_dir.exists():
            for file_path in squads_dir.glob("*.json"):
                squad_name = file_path.stem.split('_')[0:-1]  # Remove the ID part
                squad_name = '_'.join(squad_name)
                restore_plan['squads'].append({
                    'name': squad_name,
                    'file_path': file_path
                })
        
        # Process tools
        tools_dir = backup_path / "tools"
        if tools_dir.exists():
            for file_path in tools_dir.glob("*.json"):
                # Tool files are named like: transferCall_ToolName_ID.json
                parts = file_path.stem.split('_')
                if len(parts) >= 3:
                    tool_name = '_'.join(parts[1:-1])  # Remove type and ID
                else:
                    tool_name = file_path.stem
                restore_plan['tools'].append({
                    'name': tool_name,
                    'file_path': file_path
                })
        
        # Calculate totals
        total_items = sum(len(resources) for resources in restore_plan.values())
        
        if total_items == 0:
            raise ReceptionistDeploymentError("No resources found in receptionist backup")
        
        self.logger.info(f"Found {len(restore_plan['assistants'])} assistants, {len(restore_plan['squads'])} squads, {len(restore_plan['tools'])} tools to restore")
        
        if dry_run:
            return {
                'dry_run': True,
                'backup_info': backup_info,
                'backup_folder': str(backup_path),
                'would_restore': {
                    'assistants': len(restore_plan['assistants']),
                    'assistant_names': [a['name'] for a in restore_plan['assistants']],
                    'squads': len(restore_plan['squads']),
                    'squad_names': [s['name'] for s in restore_plan['squads']],
                    'tools': len(restore_plan['tools']),
                    'tool_names': [t['name'] for t in restore_plan['tools']]
                }
            }
        
        # Perform actual restore
        restored_resources = {
            'assistants': {},
            'squads': {},
            'tools': {}
        }
        
        # Create unified receptionist backup before restore
        self.logger.info("Creating receptionist backup before restore...")
        try:
            # Try to create a receptionist backup of the existing system that will be overwritten
            # Use the backup info from the restore source to build a clinic config for backup
            pre_restore_clinic_config = {
                'clinic_name': backup_info.get('clinic_name', 'PreRestore_Backup'),
                'receptionist_name': backup_info.get('receptionist_name', 'Assistant'),
                'version': backup_info.get('version', '1.0')
            }
            
            # Create the receptionist backup (will automatically handle if no matching resources exist)
            self.logger.info(f"Creating pre-restore backup for: {pre_restore_clinic_config['clinic_name']}")
            self.backup_receptionist(pre_restore_clinic_config, dry_run=False)
            
        except Exception as e:
            # If receptionist backup fails (e.g., no matching resources), fall back to general backup
            self.logger.warning(f"Receptionist backup failed ({e}), falling back to general backup...")
            self.backup_service.backup_all()
        
        try:
            # First restore tools (they might be referenced by assistants)
            if restore_plan['tools']:
                self.logger.info("Restoring tools...")
                for tool_info in restore_plan['tools']:
                    tool_file = tool_info['file_path']
                    tool_name = tool_info['name']
                    
                    # Load tool data from backup
                    with open(tool_file, 'r', encoding='utf-8') as f:
                        tool_data = json.load(f)
                    
                    original_id = tool_data['id']
                    
                    # Get actual tool name - for transferCall tools, it's in function.name
                    actual_tool_name = tool_data.get('name') 
                    if not actual_tool_name and tool_data.get('function', {}).get('name'):
                        actual_tool_name = tool_data['function']['name']
                    if not actual_tool_name:
                        actual_tool_name = tool_name
                    
                    # Remove fields that shouldn't be restored
                    fields_to_remove = ['id', 'orgId', 'createdAt', 'updatedAt', 'type']
                    for field in fields_to_remove:
                        tool_data.pop(field, None)
                    
                    self.logger.info(f"Restoring tool: {actual_tool_name}")
                    
                    try:
                        # Check if tool with same name already exists
                        existing_tools = self.client.get_tools()
                        existing_tool = None
                        for t in existing_tools:
                            if t.get('name') == actual_tool_name or t.get('function', {}).get('name') == actual_tool_name:
                                existing_tool = t
                                break
                        
                        if existing_tool:
                            # Update existing tool
                            response = self.client._client.patch(f"/tool/{existing_tool['id']}", json=tool_data)
                            result = self.client._handle_response(response, f"update tool {actual_tool_name}")
                            new_id = existing_tool['id']
                            action = "Updated"
                        else:
                            # Create new tool
                            response = self.client._client.post("/tool", json=tool_data)
                            result = self.client._handle_response(response, f"create tool {actual_tool_name}")
                            new_id = result.get('id')
                            action = "Created"
                        
                        if not new_id:
                            raise ReceptionistDeploymentError(f"Failed to restore tool {actual_tool_name}: no ID returned")
                        
                        restored_resources['tools'][actual_tool_name] = {
                            'id': new_id,
                            'original_id': original_id,
                            'action': action
                        }
                        
                        self.logger.info(f"{action} tool: {actual_tool_name} ({new_id})")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to restore tool {actual_tool_name}: {e}")
                        raise ReceptionistDeploymentError(f"Failed to restore tool {actual_tool_name}: {e}")
            
            # Then restore assistants
            if restore_plan['assistants']:
                self.logger.info("Restoring assistants...")
                for assistant_info in restore_plan['assistants']:
                    assistant_file = assistant_info['file_path']
                    assistant_name = assistant_info['name']
                    
                    # Load assistant data from backup
                    with open(assistant_file, 'r', encoding='utf-8') as f:
                        assistant_data = json.load(f)
                    
                    original_id = assistant_data['id']
                    actual_assistant_name = assistant_data['name']
                    
                    # Remove fields that shouldn't be restored
                    fields_to_remove = ['id', 'orgId', 'createdAt', 'updatedAt', 'isServerUrlSecretSet']
                    for field in fields_to_remove:
                        assistant_data.pop(field, None)
                    
                    # Update tool references if we restored them
                    if 'toolIds' in assistant_data and assistant_data['toolIds']:
                        updated_tool_ids = []
                        for old_tool_id in assistant_data['toolIds']:
                            # Find if we restored this tool
                            for tool_name, tool_info in restored_resources['tools'].items():
                                if tool_info['original_id'] == old_tool_id:
                                    updated_tool_ids.append(tool_info['id'])
                                    self.logger.info(f"Updated tool reference in assistant: {tool_name} -> {tool_info['id']}")
                                    break
                            else:
                                # Tool not found in restored tools, keep original ID
                                updated_tool_ids.append(old_tool_id)
                        assistant_data['toolIds'] = updated_tool_ids
                    
                    self.logger.info(f"Restoring assistant: {actual_assistant_name}")
                    
                    try:
                        # Check if assistant with same name already exists
                        existing_assistants = self.client.get_assistants()
                        existing_assistant = next((a for a in existing_assistants if a.get('name') == actual_assistant_name), None)
                        
                        if existing_assistant:
                            # Update existing assistant
                            updated_assistant = self.client.update_assistant(existing_assistant['id'], assistant_data)
                            new_id = existing_assistant['id']
                            action = "Updated"
                        else:
                            # Create new assistant
                            response = self.client._client.post("/assistant", json=assistant_data)
                            result = self.client._handle_response(response, f"create assistant {actual_assistant_name}")
                            new_id = result.get('id')
                            action = "Created"
                        
                        if not new_id:
                            raise ReceptionistDeploymentError(f"Failed to restore assistant {actual_assistant_name}: no ID returned")
                        
                        restored_resources['assistants'][actual_assistant_name] = {
                            'id': new_id,
                            'original_id': original_id,
                            'action': action
                        }
                        
                        self.logger.info(f"{action} assistant: {actual_assistant_name} ({new_id})")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to restore assistant {actual_assistant_name}: {e}")
                        raise ReceptionistDeploymentError(f"Failed to restore assistant {actual_assistant_name}: {e}")
            
            # Finally restore squads
            if restore_plan['squads']:
                self.logger.info("Restoring squads...")
                for squad_info in restore_plan['squads']:
                    squad_file = squad_info['file_path']
                    squad_name = squad_info['name']
                    
                    # Load squad data from backup
                    with open(squad_file, 'r', encoding='utf-8') as f:
                        squad_data = json.load(f)
                    
                    original_id = squad_data['id']
                    actual_squad_name = squad_data['name']
                    
                    # Remove fields that shouldn't be restored
                    fields_to_remove = ['id', 'orgId', 'createdAt', 'updatedAt']
                    for field in fields_to_remove:
                        squad_data.pop(field, None)
                    
                    # Update assistant IDs in squad members if we restored them
                    if 'members' in squad_data:
                        for member in squad_data['members']:
                            if 'assistantId' in member:
                                # Find if we restored this assistant
                                for assistant_name, assistant_info in restored_resources['assistants'].items():
                                    if assistant_info['original_id'] == member['assistantId']:
                                        member['assistantId'] = assistant_info['id']
                                        self.logger.info(f"Updated assistant reference in squad: {assistant_name} -> {assistant_info['id']}")
                                        break
                    
                    self.logger.info(f"Restoring squad: {actual_squad_name}")
                    
                    try:
                        # Check if squad with same name already exists
                        existing_squads = self.client.get_squads()
                        existing_squad = next((s for s in existing_squads if s.get('name') == actual_squad_name), None)
                        
                        if existing_squad:
                            # Update existing squad
                            updated_squad = self.client.update_squad(existing_squad['id'], squad_data)
                            new_id = existing_squad['id']
                            action = "Updated"
                        else:
                            # Create new squad
                            created_squad = self.client.create_squad(squad_data)
                            new_id = created_squad.get('id')
                            action = "Created"
                        
                        if not new_id:
                            raise ReceptionistDeploymentError(f"Failed to restore squad {actual_squad_name}: no ID returned")
                        
                        restored_resources['squads'][actual_squad_name] = {
                            'id': new_id,
                            'original_id': original_id,
                            'action': action
                        }
                        
                        self.logger.info(f"{action} squad: {actual_squad_name} ({new_id})")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to restore squad {actual_squad_name}: {e}")
                        raise ReceptionistDeploymentError(f"Failed to restore squad {actual_squad_name}: {e}")
            
            # Final result
            total_restored = sum(len(resources) for resources in restored_resources.values())
            
            result = {
                'organization': self.organization_service.get_organization_name_directly(),
                'backup_folder': str(backup_path),
                'total_restored': total_restored,
                'restored_assistants': restored_resources['assistants'],
                'restored_squads': restored_resources['squads'],
                'restored_tools': restored_resources['tools']
            }
            
            self.logger.info(f"Successfully restored {len(restored_resources['assistants'])} assistants, {len(restored_resources['squads'])} squads, {len(restored_resources['tools'])} tools from receptionist backup")
            return result
            
        except Exception as e:
            self.logger.error(f"Receptionist backup restore failed: {e}")
            raise ReceptionistDeploymentError(f"Receptionist backup restore failed: {e}")
    
    def list_receptionists(self) -> List[Dict[str, Any]]:
        """List all receptionist squads in the organization.
        
        Returns:
            List of receptionist squad information with associated resources
        """
        self.logger.info("Fetching all receptionist squads")
        
        try:
            # Get all squads
            all_squads = self.client.get_squads()
            
            # Filter for receptionist squads (those with 'receptionist' in the name)
            receptionist_squads = []
            
            for squad in all_squads:
                squad_name = squad.get('name', '')
                if 'receptionist' in squad_name.lower():
                    # Parse clinic name and version from squad name
                    # Expected format: "Clinic_Name_receptionist_v1_0"
                    clinic_info = self._parse_receptionist_squad_name(squad_name)
                    
                    # Get squad members
                    members = squad.get('members', [])
                    
                    # Get assistant details for each member
                    assistant_details = []
                    for member in members:
                        assistant_id = member.get('assistantId')
                        if assistant_id:
                            try:
                                assistant = self.client.get_assistant(assistant_id)
                                assistant_name = assistant.get('name', 'Unknown')
                                assistant_type = self._determine_assistant_type(assistant_name)
                                
                                assistant_details.append({
                                    'id': assistant_id,
                                    'name': assistant_name,
                                    'type': assistant_type,
                                    'model': assistant.get('model', {}).get('model', 'Unknown'),
                                    'voice': assistant.get('voice', {}).get('voiceId', 'Unknown')
                                })
                            except Exception as e:
                                self.logger.warning(f"Failed to get assistant {assistant_id}: {e}")
                                assistant_details.append({
                                    'id': assistant_id,
                                    'name': 'Unknown',
                                    'type': 'Unknown',
                                    'error': str(e)
                                })
                    
                    # Find associated emergency transfer tool
                    emergency_tool = self._find_emergency_tool_for_squad(clinic_info['clinic_name'], clinic_info['version'])
                    
                    receptionist_info = {
                        'squad_id': squad.get('id'),
                        'squad_name': squad_name,
                        'clinic_name': clinic_info['clinic_name'],
                        'version': clinic_info['version'],
                        'created_at': squad.get('createdAt'),
                        'updated_at': squad.get('updatedAt'),
                        'assistants': assistant_details,
                        'assistant_count': len(assistant_details),
                        'emergency_tool': emergency_tool,
                        'status': 'active' if len(assistant_details) > 0 else 'inactive'
                    }
                    
                    receptionist_squads.append(receptionist_info)
            
            self.logger.info(f"Found {len(receptionist_squads)} receptionist squads")
            return sorted(receptionist_squads, key=lambda x: (x['clinic_name'], x['version']))
            
        except Exception as e:
            self.logger.error(f"Failed to list receptionists: {e}")
            raise ReceptionistDeploymentError(f"Failed to list receptionists: {e}")
    
    def _parse_receptionist_squad_name(self, squad_name: str) -> Dict[str, str]:
        """Parse clinic name and version from receptionist squad name.
        
        Args:
            squad_name: Squad name in format "Clinic_Name_receptionist_vX_Y"
            
        Returns:
            Dictionary with clinic_name and version
        """
        # Try to parse versioned format: "Clinic_Name_receptionist_v1_0"
        version_match = re.search(r'(.+)_receptionist_v(\d+)_(\d+)$', squad_name, re.IGNORECASE)
        if version_match:
            clinic_name = version_match.group(1).replace('_', ' ')
            major_version = version_match.group(2)
            minor_version = version_match.group(3)
            return {
                'clinic_name': clinic_name,
                'version': f"{major_version}.{minor_version}"
            }
        
        # Try to parse basic format: "Clinic_Name_receptionist"
        basic_match = re.search(r'(.+)_receptionist$', squad_name, re.IGNORECASE)
        if basic_match:
            clinic_name = basic_match.group(1).replace('_', ' ')
            return {
                'clinic_name': clinic_name,
                'version': '1.0'  # Default version
            }
        
        # Fallback for any squad with 'receptionist' in name
        return {
            'clinic_name': squad_name.replace('_', ' '),
            'version': 'Unknown'
        }
    
    def _determine_assistant_type(self, assistant_name: str) -> str:
        """Determine the type of assistant based on its name.
        
        Args:
            assistant_name: Assistant name
            
        Returns:
            Assistant type (Greeter, Emergency, FAQ, NoteTaker, or Other)
        """
        name_lower = assistant_name.lower()
        
        if 'greeter' in name_lower:
            return 'Greeter'
        elif 'emergency' in name_lower:
            return 'Emergency'
        elif 'faq' in name_lower:
            return 'FAQ'
        elif 'note' in name_lower or 'notetaker' in name_lower:
            return 'NoteTaker'
        else:
            return 'Other'
    
    def _find_emergency_tool_for_squad(self, clinic_name: str, version: str) -> Optional[Dict[str, Any]]:
        """Find the emergency transfer tool associated with a receptionist squad.
        
        Args:
            clinic_name: Name of the clinic
            version: Version of the deployment
            
        Returns:
            Emergency tool information or None if not found
        """
        try:
            # Get all tools
            all_tools = self.client.get_tools()
            
            # Look for emergency transfer tool matching the receptionist and version
            receptionist_name_normalized = receptionist_name.replace(' ', '_')
            expected_tool_name = f"{receptionist_name_normalized}_EmergencyTransfer_v{version.replace('.', '_')}"
            
            for tool in all_tools:
                tool_name = tool.get('name', '')
                if tool_name.lower() == expected_tool_name.lower():
                    return {
                        'id': tool.get('id'),
                        'name': tool_name,
                        'type': tool.get('type'),
                        'phone': self._extract_phone_from_tool(tool)
                    }
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Failed to find emergency tool for {clinic_name} v{version}: {e}")
            return None
    
    def _extract_phone_from_tool(self, tool: Dict[str, Any]) -> Optional[str]:
        """Extract phone number from emergency transfer tool.
        
        Args:
            tool: Tool data
            
        Returns:
            Phone number or None if not found
        """
        try:
            if tool.get('type') == 'transferCall':
                destinations = tool.get('transferCall', {}).get('destinations', [])
                if destinations and len(destinations) > 0:
                    return destinations[0].get('number')
            return None
        except Exception:
            return None