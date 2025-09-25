# VAPI Built-in Tools Integration Guide

This guide explains how to integrate VAPI's built-in tools (like `endCall`, `transferCall`, `dtmf`, etc.) into your assistants using the framework's tooling system.

## Overview

VAPI provides several built-in tools that don't require external webhooks:
- **endCall**: Terminates the current call
- **transferCall**: Transfers calls to phone numbers or other assistants
- **dtmf**: Sends touch-tone signals
- **voicemail**: Routes to voicemail

## Quick Start

### Method 1: Use Core Tools Collection (Recommended)

Add this to your assistant's `tools/functions.yaml`:

```yaml
functions:
  # Your custom functions
  - name: queryKnowledgeBase
    description: "Query information"
    parameters:
      type: object
      required: [query]
      properties:
        query:
          type: string
          description: "User's question"
    server:
      url: "https://your-webhook.com/endpoint"

  # Include VAPI core tools
  - $ref: "shared/tools/vapi-core-tools.yaml"
```

### Method 2: Individual Tool References

```yaml
functions:
  # Your custom functions...

  # Individual VAPI tools
  - $ref: "shared/tools/vapi-builtins/endCall.yaml"
  - $ref: "shared/tools/vapi-builtins/dtmf.yaml"
```

## Available VAPI Tools

### Core Tools Collection

Located at: `shared/tools/vapi-core-tools.yaml`

**Enabled by default:**
- `endCall`: Essential for call termination
- `transferCall`: Essential for call routing (uses your `transfers.yaml` config)

**Disabled by default (can be enabled):**
- `dtmf`: For phone system interaction
- `voicemail`: For voicemail routing

### Individual Tools

Located in: `shared/tools/vapi-builtins/`

- `endCall.yaml`: End call tool
- `transferCall.yaml`: Transfer call tool
- `dtmf.yaml`: DTMF/touch-tone tool
- `voicemail.yaml`: Voicemail tool

## Configuration

### Enabling Optional Tools

To enable optional tools in the core collection, modify your local copy or create a custom configuration:

```yaml
# In your tools/functions.yaml
functions:
  - name: custom-vapi-tools
    type: vapi-builtin-collection
    vapi_tools:
      endCall:
        type: endCall
        enabled: true
      transferCall:
        type: transferCall
        enabled: true
      dtmf:
        type: dtmf
        enabled: true  # Enable DTMF
      voicemail:
        type: voicemail
        enabled: true  # Enable voicemail
        message: "Please leave a message"
```

### Transfer Destinations

Transfer destinations are configured in your assistant's `tools/transfers.yaml`:

```yaml
transfers:
  - type: number
    number: "+12125551234"
    description: "Emergency services"
  - type: number
    number: "+18005551234"
    description: "Main office"
```

## Integration Flow

1. **Tool Definition**: VAPI tools are defined in YAML templates
2. **Reference Resolution**: The framework resolves `$ref` links to shared tools
3. **Processing**: VAPI builtin tools are processed during assistant compilation
4. **Deployment**: Tools are included in the final VAPI API request

## Framework Processing

The framework automatically:
- ✅ Processes VAPI built-in tool collections
- ✅ Handles individual VAPI tool references
- ✅ Integrates with transfer destinations from `transfers.yaml`
- ✅ Includes tools in manifest, bootstrap, create, and update operations
- ✅ Avoids duplicating `endCall` (added by default) and `transferCall` (handled by transfers)

## Examples

### Basic Assistant with Core Tools

```yaml
# assistant.yaml
name: basic_assistant
description: "Assistant with VAPI tools"
# ... other config

# tools/functions.yaml
functions:
  - $ref: "shared/tools/vapi-core-tools.yaml"

# tools/transfers.yaml
transfers:
  - type: number
    number: "+12125551234"
    description: "Support line"
```

### Advanced Assistant with Custom Tools

```yaml
# tools/functions.yaml
functions:
  - name: bookAppointment
    description: "Book an appointment"
    # ... function definition

  - name: advanced-vapi-tools
    type: vapi-builtin-collection
    vapi_tools:
      endCall:
        type: endCall
        enabled: true
      transferCall:
        type: transferCall
        enabled: true
      dtmf:
        type: dtmf
        enabled: true
      voicemail:
        type: voicemail
        enabled: true
        message: "Custom voicemail message"
```

## Testing

Test your VAPI tools integration:

```bash
# Update squad with VAPI tools
poetry run vapi-manager squad update your_squad --env development

# Check assistant configuration
poetry run vapi-manager assistant get your_assistant --env development
```

## Troubleshooting

**Common Issues:**

1. **Tool not appearing**: Check that it's enabled in the collection
2. **Transfer not working**: Verify `transfers.yaml` configuration
3. **Duplicate tools**: Framework prevents duplication of core tools
4. **Reference errors**: Ensure shared tool files exist

**Validation:**
- VAPI tools are validated during assistant updates
- Invalid configurations will show clear error messages
- Use `--dry-run` to preview changes before applying

## Best Practices

1. **Use core tools collection** for standard assistants
2. **Enable optional tools** only when needed
3. **Configure transfers properly** in transfers.yaml
4. **Test thoroughly** after adding VAPI tools
5. **Use descriptive transfer descriptions** for better UX