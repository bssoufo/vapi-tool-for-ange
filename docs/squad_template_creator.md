# Squad Template Creator

The Squad Template Creator provides a powerful builder pattern API for creating squad templates with manifests. This enables you to programmatically define reusable squad configurations that can be deployed across multiple environments.

## Features

- **Fluent Builder Pattern**: Chainable methods for easy template construction
- **Manifest Generation**: Automatic creation of bootstrap-compatible manifest.yaml files
- **Comprehensive Validation**: Built-in validation of template configuration
- **Environment Support**: Multi-environment configuration with overrides
- **Tool Integration**: Seamless integration with shared tools
- **CLI Integration**: Command-line interface for template creation

## Quick Start

### CLI Usage

Create a simple squad template:

```bash
vapi-manager squad create-template my_squad \
  --description "Customer service squad" \
  --assistant "receptionist:vicky_dental_clinic:Front desk reception" \
  --assistant "support:vicky_dental_clinic:Customer support" \
  --tool "crm-lookup:data_lookup:url=https://api.crm.com/lookup" \
  --environment development \
  --environment production
```

Preview before creating:

```bash
vapi-manager squad create-template my_squad \
  --description "Customer service squad" \
  --assistant "receptionist:vicky_dental_clinic:Front desk reception" \
  --preview
```

### Programmatic Usage

```python
from vapi_manager.core.squad_template_creator import SquadTemplateCreator

# Create a comprehensive squad template
creator = SquadTemplateCreator("real_estate_squad")

template_path = (creator
    .with_description("Complete real estate reception system")
    .with_metadata(version="1.0", category="real_estate")
    .add_tool("crm-lookup", "data_lookup",
              url="https://api.crm.com/clients",
              api_key="${CRM_API_KEY}")
    .add_assistant("lead_qualifier", "real_estate_qualifier",
                   "Handles lead qualification and routing",
                   priority=1,
                   required_tools=["shared/tools/crm-lookup.yaml"])
    .add_assistant("property_info", "real_estate_info",
                   "Provides property information",
                   priority=2)
    .with_deployment_config(strategy="rolling", health_checks=True)
    .add_environment("development",
                     tool_overrides=[{
                         "name": "crm-lookup",
                         "variables": {"url": "https://dev-api.crm.com/clients"}
                     }])
    .add_environment("production")
    .create())

print(f"Template created at: {template_path}")
```

## API Reference

### SquadTemplateCreator

#### Constructor

```python
SquadTemplateCreator(template_name: str)
```

Creates a new template creator instance.

**Parameters:**
- `template_name`: Name of the template to create

#### Core Methods

##### `with_description(description: str) -> SquadTemplateCreator`

Sets the template description.

```python
creator.with_description("A comprehensive customer service squad")
```

##### `with_metadata(**metadata) -> SquadTemplateCreator`

Adds metadata to the template.

```python
creator.with_metadata(
    version="1.0",
    author="Your Company",
    category="customer_service"
)
```

##### `add_assistant(name, template, role=None, priority=2, required_tools=None, config_overrides=None) -> SquadTemplateCreator`

Adds an assistant to the squad template.

```python
creator.add_assistant(
    name="customer_support",
    template="vicky_dental_clinic",
    role="Handles customer inquiries and support",
    priority=1,
    required_tools=["shared/tools/crm-lookup.yaml"],
    config_overrides={"model": {"temperature": 0.7}}
)
```

**Parameters:**
- `name`: Assistant instance name
- `template`: Assistant template to use
- `role`: Description of the assistant's role
- `priority`: Routing priority (1 = highest)
- `required_tools`: List of tool references
- `config_overrides`: Configuration overrides

##### `add_tool(name, template, description=None, **variables) -> SquadTemplateCreator`

Adds a shared tool to the squad template.

```python
creator.add_tool(
    name="api_connector",
    template="webhook",
    description="External API integration",
    url="https://api.service.com/webhook",
    api_key="${API_KEY}",
    timeout=30
)
```

##### `with_deployment_config(strategy="rolling", rollback_on_failure=True, health_checks=True, validation_steps=None) -> SquadTemplateCreator`

Configures deployment settings.

```python
creator.with_deployment_config(
    strategy="blue_green",
    rollback_on_failure=True,
    health_checks=True,
    validation_steps=["api_connectivity", "database_check"]
)
```

##### `add_environment(environment, assistant_overrides=None, tool_overrides=None) -> SquadTemplateCreator`

Adds environment-specific configuration.

```python
creator.add_environment(
    "production",
    assistant_overrides=[{
        "name": "customer_support",
        "config_overrides": {"model": {"model": "gpt-4"}}
    }],
    tool_overrides=[{
        "name": "api_connector",
        "variables": {"url": "https://prod-api.service.com/webhook"}
    }]
)
```

##### `add_routing_rule(rule_name, rule_type, priority, triggers, destination, description=None) -> SquadTemplateCreator`

Adds routing rules to the template.

```python
creator.add_routing_rule(
    rule_name="urgent_escalation",
    rule_type="priority",
    priority=1,
    triggers=[{"type": "keyword", "keywords": ["urgent", "emergency"]}],
    destination="human_agent",
    description="Route urgent requests to human agents"
)
```

##### `with_squad_config(**config) -> SquadTemplateCreator`

Adds squad-level configuration.

```python
creator.with_squad_config(
    business_hours="9:00-17:00",
    time_zone="America/New_York",
    max_concurrent_calls=50
)
```

#### Utility Methods

##### `validate() -> List[str]`

Validates the current template configuration.

```python
errors = creator.validate()
if errors:
    print("Validation errors:", errors)
```

##### `preview() -> str`

Generates a preview of the template structure.

```python
preview_text = creator.preview()
print(preview_text)
```

##### `create(force=False) -> Path`

Creates the squad template files.

```python
template_path = creator.create(force=True)  # Overwrite if exists
```

## CLI Command Reference

### `vapi-manager squad create-template`

Creates a new squad template with manifest.

```bash
vapi-manager squad create-template TEMPLATE_NAME \
  --description DESCRIPTION \
  [--assistant NAME:TEMPLATE:ROLE] \
  [--tool NAME:TEMPLATE:VAR1=VAL1,VAR2=VAL2] \
  [--environment ENV] \
  [--deployment-strategy STRATEGY] \
  [--force] \
  [--preview] \
  [--output-dir DIR]
```

**Arguments:**
- `TEMPLATE_NAME`: Name of the template to create

**Options:**
- `--description`: Template description (required)
- `--assistant`: Assistant specification (can be used multiple times)
- `--tool`: Tool specification (can be used multiple times)
- `--environment`: Environment to include (can be used multiple times)
- `--deployment-strategy`: Deployment strategy (rolling, blue_green, all_at_once)
- `--force`: Overwrite existing template
- `--preview`: Preview template without creating
- `--output-dir`: Output directory for template

**Assistant Specification Format:**
```
name:template:role
```

**Tool Specification Format:**
```
name:template:var1=val1,var2=val2
```

## Examples

### Real Estate Squad Template

```bash
vapi-manager squad create-template real_estate_squad \
  --description "Complete real estate reception system" \
  --assistant "lead_qualifier:real_estate_qualifier:Lead qualification and routing" \
  --assistant "property_info:real_estate_info:Property information specialist" \
  --assistant "scheduler:real_estate_scheduler:Appointment scheduling coordinator" \
  --tool "crm-lookup:data_lookup:url=https://api.crm.com/clients,api_key=\${CRM_API_KEY}" \
  --tool "mls-search:data_lookup:url=https://api.mls.com/search,api_key=\${MLS_API_KEY}" \
  --tool "calendar-booking:appointment_booking:url=https://api.calendar.com/book" \
  --environment development \
  --environment staging \
  --environment production \
  --deployment-strategy rolling
```

### E-commerce Support Squad

```bash
vapi-manager squad create-template ecommerce_support_squad \
  --description "E-commerce customer support and order management" \
  --assistant "order_support:ecommerce_support:Order inquiries and support" \
  --assistant "returns_handler:ecommerce_support:Returns and refunds specialist" \
  --assistant "shipping_tracker:ecommerce_support:Shipping and tracking assistant" \
  --tool "order-lookup:data_lookup:url=https://api.shop.com/orders" \
  --tool "inventory-check:data_lookup:url=https://api.shop.com/inventory" \
  --tool "shipping-api:webhook:url=https://api.shipping.com/track" \
  --environment development \
  --environment production \
  --deployment-strategy blue_green
```

### Restaurant Reservation Squad

```bash
vapi-manager squad create-template restaurant_squad \
  --description "Restaurant reservation and customer service system" \
  --assistant "host:restaurant_host:Reservation and seating coordinator" \
  --assistant "takeout:restaurant_takeout:Takeout and delivery orders" \
  --assistant "events:restaurant_events:Private events and catering" \
  --tool "reservation-system:appointment_booking:url=https://api.restaurant.com/reservations" \
  --tool "menu-lookup:data_lookup:url=https://api.restaurant.com/menu" \
  --tool "pos-integration:webhook:url=https://api.restaurant.com/orders" \
  --environment development \
  --environment production \
  --deployment-strategy rolling
```

## Integration with Bootstrap

Once you've created a squad template, you can use it with the bootstrap system:

```bash
# Create template
vapi-manager squad create-template my_squad --description "My squad" --assistant "support:vicky_dental_clinic:Support"

# Bootstrap a squad from the template
vapi-manager squad bootstrap my_production_squad --template my_squad --deploy --env production

# Preview bootstrap
vapi-manager squad bootstrap my_test_squad --template my_squad --dry-run
```

## File Structure

When you create a template, the following files are generated:

```
templates/squads/my_squad/
├── manifest.yaml       # Bootstrap manifest with tools and assistants
├── squad.yaml         # Squad configuration with variables
├── members.yaml       # Member definitions and priorities
└── routing/           # Optional routing configuration
    └── destinations.yaml
```

### manifest.yaml

Contains the complete bootstrap configuration:

```yaml
description: "Squad description"
metadata:
  version: "1.0"
  author: "VAPI Manager"
tools:
  - name: "tool_name"
    template: "tool_template"
    variables:
      key: "value"
assistants:
  - name: "assistant_name"
    template: "assistant_template"
    role: "Assistant role"
deployment:
  strategy: "rolling"
  rollback_on_failure: true
  health_checks: true
environments:
  development: {}
  production: {}
```

### squad.yaml

Contains squad-level configuration with template variables:

```yaml
name: "{{squad_name}}"
description: "{{description|Default description}}"
# Additional squad configuration
```

### members.yaml

Contains member definitions:

```yaml
members:
  - assistant_name: "assistant1"
    role: "Assistant role"
    priority: 1
  - assistant_name: "assistant2"
    role: "Another role"
    priority: 2
```

## Best Practices

1. **Descriptive Names**: Use clear, descriptive names for templates and assistants
2. **Environment Variables**: Use environment variables for sensitive data like API keys
3. **Validation**: Always validate templates before creation
4. **Preview First**: Use `--preview` to review templates before creating
5. **Version Control**: Store template files in version control
6. **Documentation**: Document custom configurations and variables
7. **Testing**: Test templates with `--dry-run` before deployment

## Error Handling

Common validation errors and solutions:

- **"Template description is required"**: Add `--description` parameter
- **"At least one assistant is required"**: Add at least one `--assistant` parameter
- **"Assistant references unknown tool"**: Ensure all referenced tools are defined
- **"Template already exists"**: Use `--force` to overwrite or choose a different name

## Advanced Usage

### Programmatic Template Building

```python
from vapi_manager.core.squad_template_creator import SquadTemplateCreator

def create_industry_template(industry: str, assistants: list, tools: list):
    """Create a template for a specific industry."""
    creator = SquadTemplateCreator(f"{industry}_squad")

    creator.with_description(f"{industry.title()} customer service squad")
    creator.with_metadata(category=industry, version="1.0")

    for i, (name, role) in enumerate(assistants):
        creator.add_assistant(name, "vicky_dental_clinic", role, priority=i+1)

    for tool_name, tool_config in tools.items():
        creator.add_tool(tool_name, tool_config["template"], **tool_config["variables"])

    creator.with_deployment_config(strategy="rolling")
    creator.add_environment("development")
    creator.add_environment("production")

    return creator.create()

# Usage
assistants = [
    ("receptionist", "Front desk reception"),
    ("support", "Customer support specialist")
]

tools = {
    "crm": {
        "template": "data_lookup",
        "variables": {"url": "https://api.crm.com/lookup"}
    }
}

template_path = create_industry_template("healthcare", assistants, tools)
```

This documentation provides comprehensive coverage of the Squad Template Creator functionality, from basic CLI usage to advanced programmatic use cases.