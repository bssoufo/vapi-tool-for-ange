### **Technical Specification: Shared Tools with Overrides**

**Document Version:** 1.0
**Author:** Senior Software Architect
**Date:** [Current Date]

#### **1. Objective**

To enhance the `vapi-manager` tool by implementing a system for shared, reusable tool definitions. This will allow an assistant's configuration to reference a canonical tool definition and optionally override parts of it, adhering to the DRY (Don't Repeat Yourself) principle. This is critical for managing tools that have a common structure but differ in specific values (e.g., server URLs, descriptions) across different use cases (e.g., "Clinic" vs. "Entrepreneur" appointments).

#### **2. Core Concepts & Proposed YAML Syntax**

We will introduce a new top-level directory `shared/` and a new syntax within tool definition files.

**2.1. Directory Structure**

A new directory will be created at the project root to store canonical, reusable components.

```
vapi-manager/
├── shared/
│   └── tools/
│       ├── bookAppointment_base.yaml      # The common, shared part
│       ├── bookAppointment_clinic.yaml    # Specialized for clinics
│       └── bookAppointment_entrepreneur.yaml # Specialized for entrepreneurs
├── assistants/
│   └── scheduler_bot/
│       └── tools/
│           └── functions.yaml             # Will reference a shared tool
└── ...
```

**2.2. YAML Syntax**

We will introduce two new keywords: `$ref` and `overrides`.

*   **`$ref`**: A key indicating that this object should be replaced by the content of the referenced file. The path is relative to the project root.
*   **`overrides`**: A key within a referencing object that contains a dictionary to be deep-merged onto the referenced content.

**Example 1: Base Tool (`shared/tools/bookAppointment_base.yaml`)**
This file contains the common structure.

```yaml
name: bookAppointment
description: "Schedules a generic appointment."
server:
  url: "${BOOKING_WEBHOOK_URL}"
parameters:
  type: object
  required:
    - firstName
    - lastName
    - dateTime
  properties:
    firstName:
      type: string
    lastName:
      type: string
    dateTime:
      type: string
      format: date-time
```

**Example 2: Specialized Tool (`shared/tools/bookAppointment_clinic.yaml`)**
This file "inherits" from the base and adds clinic-specific parameters.

```yaml
# Inherit the common structure
$ref: "shared/tools/bookAppointment_base.yaml"

# Override and extend the base
overrides:
  description: "Schedules a patient appointment for the dental clinic."
  parameters:
    required:
      - insuranceProvider # Add to the 'required' list from the base
    properties:
      insuranceProvider: # Add a new property
        type: string
        description: "The patient's insurance provider."
```

**Example 3: Assistant's Tool Configuration (`assistants/scheduler_bot/tools/functions.yaml`)**
The assistant's configuration is now extremely simple.

```yaml
functions:
  - $ref: "shared/tools/bookAppointment_clinic.yaml"
  - $ref: "shared/tools/queryKnowledgeBase.yaml" # Another shared tool
```

#### **3. Implementation Details: Core Logic**

The primary changes will be in the configuration loading mechanism.

**3.1. Target File for Modification**

*   `vapi_manager/core/assistant_config.py`

**3.2. Target Class and Method**

*   **Class**: `AssistantConfigLoader`
*   **Method to Modify**: `_load_tools()`

**3.3. Proposed Algorithm for `_load_tools()`**

The existing `_load_tools` method should be refactored. The new logic will process each item in a `functions.yaml` (or similar) file and resolve any `$ref`s it finds.

```python
# In vapi_manager/core/assistant_config.py -> AssistantConfigLoader

def _load_tools(self, tools_dir: Path) -> Dict:
    # ... (existing logic to find and load tool files like functions.yaml)

    # New logic starts here:
    if 'functions' in tools_config and 'functions' in tools_config['functions']:
        resolved_functions = []
        for tool_def in tools_config['functions']['functions']:
            if isinstance(tool_def, dict) and '$ref' in tool_def:
                # Pass the entire definition, which might include overrides
                resolved_tool = self._resolve_tool_reference(tool_def, visited=set())
                resolved_functions.append(resolved_tool)
            else:
                # This is a standard, locally-defined tool
                resolved_functions.append(tool_def)

        tools_config['functions']['functions'] = resolved_functions

    return tools_config
```

**3.4. New Helper Method: `_resolve_tool_reference()`**

This new private method will handle the recursive loading, merging, and circular dependency detection.

```python
# In vapi_manager/core/assistant_config.py -> AssistantConfigLoader

def _resolve_tool_reference(self, tool_def: Dict, visited: set) -> Dict:
    ref_path_str = tool_def.get('$ref')
    if not ref_path_str:
        return tool_def

    # Project root is the parent of the 'vapi_manager' directory
    project_root = Path(__file__).resolve().parents[2] 
    ref_path = project_root / ref_path_str

    if ref_path in visited:
        raise ValueError(f"Circular reference detected in tool definitions: {ref_path}")

    visited.add(ref_path)

    if not ref_path.exists():
        raise FileNotFoundError(f"Shared tool reference not found: {ref_path}")

    with open(ref_path, 'r', encoding='utf-8') as f:
        base_tool_config = yaml.safe_load(f)

    # Recursively resolve if the base file also has a reference
    if '$ref' in base_tool_config:
        base_tool_config = self._resolve_tool_reference(base_tool_config, visited)

    # Perform a deep merge with the overrides from the original tool_def
    if 'overrides' in tool_def:
        base_tool_config = self._deep_merge(base_tool_config, tool_def['overrides'])

    return base_tool_config
```

**3.5. New Utility Method: `_deep_merge()`**

A utility for merging dictionaries is required. This can be added to the `AssistantConfigLoader` or a separate utils file.

```python
# In vapi_manager/core/assistant_config.py -> AssistantConfigLoader

def _deep_merge(self, base: dict, override: dict) -> dict:
    """
    Recursively merges two dictionaries. Arrays are combined.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result, dict) and isinstance(value, dict):
            result = self._deep_merge(result[key], value)
        elif key in result and isinstance(result, list) and isinstance(value, list):
            # Combine lists and remove duplicates
            result = list(dict.fromkeys(result + value))
        else:
            result = value
    return result
```

#### **4. Implementation Details: CLI Command**

A new CLI command should be added to simplify adding shared tools to an assistant.

**4.1. Target File for Modification**

*   `vapi_manager/cli/simple_cli.py`

**4.2. Proposed Command**

*   `vapi-manager assistant add-tool <assistant_name> --tool <tool_ref_path>`
    *   Example: `vapi-manager assistant add-tool scheduler_bot --tool shared/tools/bookAppointment_clinic.yaml`

**4.3. Command Logic**

1.  Validate that `<assistant_name>` exists.
2.  Validate that the file at `<tool_ref_path>` exists.
3.  Load the `assistants/<assistant_name>/tools/functions.yaml` file.
4.  If the `functions` list doesn't exist, create it.
5.  Append a new item to the list: `{"$ref": "<tool_ref_path>"}`.
6.  Write the modified YAML back to the file, preserving comments and structure if possible (`ruamel.yaml` is excellent for this).

#### **5. Testing Strategy**

1.  **Unit Tests**:
    *   Test `_deep_merge` with various nested dictionaries and lists.
    *   Test `_resolve_tool_reference` for:
        *   Simple, one-level reference.
        *   Nested, multi-level references.
        *   Reference with overrides (ensure merge is correct).
        *   **Crucially, test for circular reference detection.**
        *   Test for `FileNotFoundError`.
2.  **Integration Tests**:
    *   Test the modified `AssistantConfigLoader._load_tools` to ensure a complete `AssistantConfig` object is correctly assembled from a combination of local and referenced tools.
3.  **End-to-End Tests**:
    *   Test the `vapi-manager assistant add-tool` CLI command to verify it correctly modifies the `functions.yaml` file.

#### **6. Implementation Plan / Phased Rollout**

1.  **Phase 1: Core Logic Implementation**
    *   Implement the changes in `vapi_manager/core/assistant_config.py` (`_load_tools`, `_resolve_tool_reference`, `_deep_merge`).
    *   Write and pass all unit and integration tests.
    *   At this stage, the feature is functional but must be configured manually.

2.  **Phase 2: CLI Command**
    *   Implement the `assistant add-tool` command in `vapi_manager/cli/simple_cli.py`.
    *   Add end-to-end tests for the CLI command.

3.  **Phase 3: Refactoring & Documentation**
    *   Create the `shared/tools/` directory and refactor existing, duplicated tools (like `queryKnowledgeBase`) into shared files.
    *   Update existing assistants to use the new `$ref` syntax.
    *   Update the project's `README.md` and any other relevant documentation to explain the new feature, syntax, and CLI command.

#### **7. Potential Risks & Mitigations**

*   **Risk**: Circular dependencies in `$ref`s could cause an infinite loop.
    *   **Mitigation**: The `_resolve_tool_reference` algorithm **must** include a `visited` set to detect and raise an error on circular references. This is non-negotiable.
*   **Risk**: Complex merge logic could be buggy.
    *   **Mitigation**: A comprehensive suite of unit tests for `_deep_merge` is essential to cover all edge cases (nested objects, lists, mixed types).

================================================================================