# Real Estate Squad Routing Implementation Guide

## Current Issues

The routing configuration in `routing/destinations.yaml` and `routing/rules.yaml` is not functional because:

1. **VAPI doesn't support squad-level routing** - Each assistant must define its own transfer destinations
2. **The format doesn't match VAPI's API** - VAPI expects `transferDestinations` in the assistant configuration
3. **Missing integration** - The routing files aren't integrated into the assistant deployment

## Correct Implementation

### Option 1: Assistant-Level Transfer Destinations

Each assistant should have `transferDestinations` in their configuration:

```yaml
# In assistants/real-estate-triage/assistant.yaml
transferDestinations:
  - type: assistant
    assistantName: real-estate-booking
    message: "I'll connect you with our booking specialist."
    transferMode:
      mode: rolling-history
  - type: assistant
    assistantName: real-estate-info
    message: "Let me transfer you to our property information specialist."
    transferMode:
      mode: rolling-history
```

### Option 2: Function-Based Routing

Add a transfer function to each assistant:

```yaml
# In assistants/real-estate-triage/tools/functions.yaml
functions:
  - name: transfer_to_specialist
    description: Transfer to appropriate specialist based on needs
    parameters:
      type: object
      properties:
        destination:
          type: string
          enum: ["booking", "info", "manager"]
        reason:
          type: string
      required: ["destination", "reason"]
```

Then in the system prompt:
```markdown
When the customer needs help with:
- Scheduling/appointments: Use transfer_to_specialist with destination="booking"
- Property information: Use transfer_to_specialist with destination="info"
- Complaints/escalation: Use transfer_to_specialist with destination="manager"
```

### Option 3: Server-Side Routing

Use server webhooks to handle routing decisions:

```yaml
# In assistant.yaml
server:
  url: "https://your-server.com/webhook"
  timeoutSeconds: 20

serverMessages:
  - transfer-request
```

Your server then responds with:
```json
{
  "action": "transferCall",
  "destination": {
    "type": "assistant",
    "assistantName": "real-estate-booking"
  }
}
```

## Implementation Steps

1. **Remove non-functional routing files**:
   - `routing/destinations.yaml` (not used by VAPI)
   - `routing/rules.yaml` (not used by VAPI)

2. **Update each assistant template** with proper transfer destinations

3. **Update system prompts** to include transfer logic

4. **Test transfers** between assistants

## Why This Matters

- **VAPI is assistant-centric**: Each assistant is a standalone entity
- **No central routing engine**: Unlike PBX systems, VAPI doesn't have centralized routing
- **Transfers are API calls**: Each transfer is an explicit API action, not a routing rule

## Recommended Approach

For the real estate squad, I recommend **Option 1** (Assistant-Level Transfer Destinations) combined with clear system prompts that guide when to transfer. This is the simplest and most reliable approach.