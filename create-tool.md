### 3. Recommended Strategy & Implementation Plan

**I strongly recommend Strategy 3: The Template-Driven Approach.** It aligns with your codebase's philosophy, promotes consistency, and provides the best balance of user guidance and flexibility.

Here is a detailed implementation plan:

#### A. Command Structure

Define the new CLI command and its arguments in `vapi_manager/cli/simple_cli.py`.

```bash
# Basic usage
vapi-manager tool create <tool_name> --template <template_name>

# With optional parameters for variable substitution
vapi-manager tool create cancel-appointment \
    --template webhook-with-params \
    --description "Cancels an existing appointment" \
    --url "https://my-api.com/appointments/cancel" \
    --force
```

#### B. Directory Structure

1.  **Create a new directory for tool templates:**
    ```
    templates/
    └── tools/
        ├── basic_webhook.yaml
        └── data_lookup.yaml
    ```
2.  The output files will be created in the existing `shared/tools/` directory.

#### C. Template Example

Create a sample template file like `templates/tools/basic_webhook.yaml`:

```yaml
# templates/tools/basic_webhook.yaml
name: "{{tool_name}}"
description: "{{description|A simple webhook tool}}"
server:
  url: "{{url|${WEBHOOK_URL}}}"
parameters:
  type: object
  required:
    - id
  properties:
    id:
      type: string
      description: "The unique identifier for the item"
```
*This uses the same Jinja2-like syntax found in your squad templates (`templates/squads/dental_clinic_squad/squad.yaml`).*

#### D. Implementation Steps

1.  **Create a `ToolTemplateManager`:**
    *   Create a new file: `vapi_manager/core/tool_template_manager.py`.
    *   This class will be very similar to `vapi_manager/core/template_manager.py` but will be configured to read from `templates/tools` and write to `shared/tools`.
    *   It will handle variable substitution for fields like `name`, `description`, and `url`.

2.  **Integrate into the CLI (`simple_cli.py`):**
    *   Add a new subparser for the `tool` command.
    *   Implement the `create` subcommand, which will call the `ToolTemplateManager`.
    *   Add a `tool templates` command to list available tool templates, similar to the existing `file templates` command.

    ```python
    # In vapi_manager/cli/simple_cli.py, within main()

    # ... existing parsers ...

    # Tool commands
    tool_parser = subparsers.add_parser("tool", help="Manage shared tools")
    tool_subparsers = tool_parser.add_subparsers(dest="tool_command")

    tool_create_parser = tool_subparsers.add_parser("create", help="Create a new shared tool from a template")
    tool_create_parser.add_argument("name", help="Tool name (filename without .yaml)")
    tool_create_parser.add_argument("--template", default="basic_webhook", help="Template to use")
    tool_create_parser.add_argument("--description", help="Tool description")
    tool_create_parser.add_argument("--url", help="Server webhook URL")
    tool_create_parser.add_argument("--force", action="store_true", help="Overwrite if tool exists")

    tool_templates_parser = tool_subparsers.add_parser("templates", help="List available tool templates")

    # ... in the command handling logic ...
    elif args.command == "tool":
        if args.tool_command == "create":
            # from ..core.tool_template_manager import ToolTemplateManager
            # manager = ToolTemplateManager()
            # manager.init_tool(...)
            pass # Add logic here
        elif args.tool_command == "templates":
            # list tool templates
            pass # Add logic here
    ```

3.  **Create Default Templates:**
    *   Populate the `templates/tools/` directory with a few useful templates like `basic_webhook.yaml` and `data_lookup.yaml` to make the feature immediately useful.

4.  **Documentation and Testing:**
    *   Update the README and command help text.
    *   Add unit tests for the `ToolTemplateManager` to ensure file creation and variable substitution work correctly.

By following this plan, you will introduce a powerful and consistent way to manage shared tools that seamlessly integrates with your existing architecture.
