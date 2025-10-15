# n8n Webhook: Set Customer Context

This webhook handles the `setCustomerContext` function which stores customer information and makes it available to all assistants in the squad via VAPI's `variableValues`.

## Webhook URL
```
https://n8n-2-u19609.vm.elestio.app/webhook/set-customer-context
```

## How It Works

### Flow
1. **Triage assistant** extracts customer name, phone, and intent
2. **Calls** `setCustomerContext()` function with the data
3. **n8n webhook** receives the data
4. **n8n updates** the VAPI call with `variableValues` via PATCH API
5. **Triage assistant** then calls `transferCall` to transfer
6. **Next assistant** (scheduler/manager) can now use `{{customer_name}}`, `{{customer_first_name}}`, etc. in their prompts

### Request Format (from VAPI)

```json
{
  "message": {
    "type": "tool-calls",
    "call": {
      "id": "call-uuid-12345",
      "phoneNumberId": "...",
      "customer": {
        "number": "+15551234567"
      }
    },
    "toolCallList": [
      {
        "id": "tool-call-id",
        "type": "function",
        "function": {
          "name": "setCustomerContext",
          "arguments": {
            "intent": "new_appointment",
            "customer_first_name": "John",
            "customer_last_name": "Smith",
            "customer_phone": "+15551234567",
            "notes": "Prefers morning appointments"
          }
        }
      }
    ]
  }
}
```

## n8n Workflow Implementation

### Node 1: Webhook (Trigger)
- **Method**: POST
- **Path**: `/webhook/set-customer-context`
- **Response Mode**: "When Last Node Finishes"

### Node 2: Extract Customer Data (Code Node)

```javascript
// Extract data from VAPI request
const message = $input.item.json.message;
const call = message.call;
const args = message.toolCallList[0].function.arguments;

// Build customer context
const firstName = args.customer_first_name || '';
const lastName = args.customer_last_name || '';
const fullName = [firstName, lastName].filter(Boolean).join(' ');

return {
  callId: call.id,
  customerContext: {
    customer_name: fullName,
    customer_first_name: firstName,
    customer_last_name: lastName,
    customer_phone: args.customer_phone || call.customer?.number || '',
    customer_intent: args.intent || 'general_inquiry',
    customer_notes: args.notes || ''
  }
};
```

### Node 3: Update VAPI Call (HTTP Request Node)

**Configuration:**
- **Method**: PATCH
- **URL**: `https://api.vapi.ai/call/{{$json.callId}}`
- **Authentication**: Header Auth
  - **Header Name**: `Authorization`
  - **Header Value**: `Bearer YOUR_VAPI_API_KEY`
- **Headers**:
  ```json
  {
    "Content-Type": "application/json"
  }
  ```
- **Body** (JSON):
  ```json
  {
    "assistant": {
      "variableValues": {
        "customer_name": "={{ $json.customerContext.customer_name }}",
        "customer_first_name": "={{ $json.customerContext.customer_first_name }}",
        "customer_last_name": "={{ $json.customerContext.customer_last_name }}",
        "customer_phone": "={{ $json.customerContext.customer_phone }}",
        "customer_intent": "={{ $json.customerContext.customer_intent }}",
        "customer_notes": "={{ $json.customerContext.customer_notes }}"
      }
    }
  }
  ```

### Node 4: Return Success Response (Code Node)

```javascript
const context = $input.first().json.customerContext;

// Return success response to VAPI
return {
  success: true,
  message: "Customer context saved successfully",
  results: [{
    customer_name: context.customer_name,
    customer_intent: context.customer_intent
  }]
};
```

## Complete n8n Workflow (JSON)

<details>
<summary>Click to expand importable n8n workflow</summary>

```json
{
  "name": "VAPI - Set Customer Context",
  "nodes": [
    {
      "parameters": {
        "path": "set-customer-context",
        "responseMode": "lastNode",
        "options": {}
      },
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [250, 300],
      "webhookId": "set-customer-context"
    },
    {
      "parameters": {
        "jsCode": "const message = $input.item.json.message;\nconst call = message.call;\nconst args = message.toolCallList[0].function.arguments;\n\nconst firstName = args.customer_first_name || '';\nconst lastName = args.customer_last_name || '';\nconst fullName = [firstName, lastName].filter(Boolean).join(' ');\n\nreturn {\n  callId: call.id,\n  customerContext: {\n    customer_name: fullName,\n    customer_first_name: firstName,\n    customer_last_name: lastName,\n    customer_phone: args.customer_phone || call.customer?.number || '',\n    customer_intent: args.intent || 'general_inquiry',\n    customer_notes: args.notes || ''\n  }\n};"
      },
      "name": "Extract Data",
      "type": "n8n-nodes-base.code",
      "position": [450, 300]
    },
    {
      "parameters": {
        "method": "PATCH",
        "url": "=https://api.vapi.ai/call/{{ $json.callId }}",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "assistant.variableValues",
              "value": "={{ $json.customerContext }}"
            }
          ]
        }
      },
      "name": "Update VAPI Call",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 300],
      "credentials": {
        "httpHeaderAuth": {
          "id": "1",
          "name": "VAPI API Key"
        }
      }
    },
    {
      "parameters": {
        "jsCode": "const context = $input.first().json.customerContext;\n\nreturn {\n  success: true,\n  message: \"Customer context saved successfully\",\n  results: [{\n    customer_name: context.customer_name,\n    customer_intent: context.customer_intent\n  }]\n};"
      },
      "name": "Return Response",
      "type": "n8n-nodes-base.code",
      "position": [850, 300]
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{"node": "Extract Data", "type": "main", "index": 0}]]
    },
    "Extract Data": {
      "main": [[{"node": "Update VAPI Call", "type": "main", "index": 0}]]
    },
    "Update VAPI Call": {
      "main": [[{"node": "Return Response", "type": "main", "index": 0}]]
    }
  }
}
```

</details>

## Testing the Webhook

### Test with curl

```bash
curl -X POST https://n8n-2-u19609.vm.elestio.app/webhook/set-customer-context \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "tool-calls",
      "call": {
        "id": "test-call-123",
        "customer": {
          "number": "+15551234567"
        }
      },
      "toolCallList": [
        {
          "function": {
            "name": "setCustomerContext",
            "arguments": {
              "intent": "new_appointment",
              "customer_first_name": "John",
              "customer_last_name": "Doe",
              "customer_phone": "+15551234567"
            }
          }
        }
      ]
    }
  }'
```

### Expected Response

```json
{
  "success": true,
  "message": "Customer context saved successfully",
  "results": [
    {
      "customer_name": "John Doe",
      "customer_intent": "new_appointment"
    }
  ]
}
```

## Using Variables in Subsequent Assistants

Once the webhook sets the variables, they're available in ALL assistants:

### Update Scheduler Prompt

**File**: `assistants/scheduler-ange/prompts/system.md`

```markdown
You are the scheduling specialist for Vicky Dental Clinic.

**Customer Information:**
- Name: {{customer_name}}
- First Name: {{customer_first_name}}
- Last Name: {{customer_last_name}}
- Phone: {{customer_phone}}
- Intent: {{customer_intent}}
- Notes: {{customer_notes}}

**IMPORTANT**: Always greet the customer warmly using their first name.

Example: "Hi {{customer_first_name}}! I'd be happy to help you schedule an appointment."

If the customer's intent is "{{customer_intent}}", acknowledge it naturally in your greeting.
```

### Update Manager Prompt

**File**: `assistants/manager-ange/prompts/system.md`

```markdown
You are the appointment manager for Vicky Dental Clinic.

**Customer Information:**
- Name: {{customer_name}}
- Phone: {{customer_phone}}
- Intent: {{customer_intent}}
- Notes: {{customer_notes}}

Use their name throughout the conversation for a personalized experience.

Example: "Hi {{customer_first_name}}! I can help you with that appointment modification."
```

## How the Two-Step Process Works

### In the Triage Assistant

The AI performs these steps automatically:

```
User: "Hi, this is John Smith, I need to book an appointment"

AI extracts:
- first_name: "John"
- last_name: "Smith"
- intent: "new_appointment"

AI calls Tool 1: setCustomerContext({
  customer_first_name: "John",
  customer_last_name: "Smith",
  intent: "new_appointment"
})

↓ Webhook updates call with variables

AI calls Tool 2: transferCall("scheduler")

↓ Transfer happens

Scheduler sees variables and says:
"Hi John! I'd be happy to help you schedule an appointment."
```

## Deployment Steps

1. **Create the n8n workflow** as described above
2. **Set up VAPI API key** in n8n credentials:
   - Go to n8n Settings > Credentials
   - Create "Header Auth" credential
   - Name: "VAPI API Key"
   - Header Name: `Authorization`
   - Header Value: `Bearer YOUR_VAPI_API_KEY`
3. **Activate the workflow** in n8n
4. **Update assistants** with variable usage in prompts:
   ```bash
   vapi-manager assistant update scheduler-ange --env production
   vapi-manager assistant update manager-ange --env production
   ```
5. **Deploy the triage assistant**:
   ```bash
   vapi-manager assistant update triage-ange --env production
   ```
6. **Test with a real call**

## Troubleshooting

### Variables not showing up

**Check**:
1. Is the webhook being called? (Check n8n execution log)
2. Is the PATCH request succeeding? (Check HTTP node output)
3. Did the call ID match? (Verify in logs)

**Solution**: Add error handling and logging to each node

### Transfer happening before variables are set

**Possible cause**: AI calling transferCall too quickly

**Solution**: The webhook is fast (<500ms), but if needed, you can add a small delay or use VAPI's message system to ensure completion.

### Empty variable values

**Check**: What data did the triage assistant extract?

**Solution**: Review the conversation transcript and improve extraction instructions in the system prompt.

---

**Webhook URL**: `https://n8n-2-u19609.vm.elestio.app/webhook/set-customer-context`
**Last Updated**: 2025-10-10
**Status**: Ready for Implementation
