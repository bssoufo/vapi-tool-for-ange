# n8n Webhook: Transfer with Context

This webhook handles the `transferWithContext` function tool from the triage assistant, extracting customer information and performing a VAPI transfer while injecting variables.

## Webhook URL
```
https://n8n-2-u19609.vm.elestio.app/webhook/transfer-with-context
```

## Purpose
1. Receive customer information (name, phone, intent) from the greeter assistant
2. Store this information temporarily (keyed by call ID)
3. Update the current call with `variableValues` to make data available to all subsequent assistants
4. Optionally perform the actual transfer to the destination assistant

## Request Format (from VAPI)

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
          "name": "transferWithContext",
          "arguments": {
            "destination": "scheduler",
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

### Step 1: Webhook Node
- **Method**: POST
- **Path**: `/webhook/transfer-with-context`
- **Authentication**: None (or Bearer token if needed)

### Step 2: Extract Data (Function Node)

```javascript
// Extract parameters from VAPI request
const message = $input.item.json.message;
const call = message.call;
const args = message.toolCallList[0].function.arguments;

// Build customer context
const customerContext = {
  callId: call.id,
  firstName: args.customer_first_name || '',
  lastName: args.customer_last_name || '',
  fullName: [args.customer_first_name, args.customer_last_name].filter(Boolean).join(' '),
  phone: args.customer_phone || call.customer?.number || '',
  intent: args.intent || 'general_inquiry',
  destination: args.destination || 'scheduler',
  notes: args.notes || '',
  timestamp: new Date().toISOString()
};

return {
  json: {
    customerContext,
    callId: call.id,
    vapiApiKey: '{{YOUR_VAPI_API_KEY}}'  // From n8n credentials
  }
};
```

### Step 3: Update VAPI Call with Variables (HTTP Request Node)

**Configuration:**
- **Method**: PATCH
- **URL**: `https://api.vapi.ai/call/{{$json.callId}}`
- **Authentication**: Bearer Token
  - Token: `{{$json.vapiApiKey}}`
- **Headers**:
  ```json
  {
    "Content-Type": "application/json"
  }
  ```
- **Body** (JSON):
  ```json
  {
    "assistantOverrides": {
      "variableValues": {
        "customer_name": "={{$json.customerContext.fullName}}",
        "customer_first_name": "={{$json.customerContext.firstName}}",
        "customer_last_name": "={{$json.customerContext.lastName}}",
        "customer_phone": "={{$json.customerContext.phone}}",
        "customer_intent": "={{$json.customerContext.intent}}",
        "customer_notes": "={{$json.customerContext.notes}}"
      }
    }
  }
  ```

### Step 4: Map Destination to Assistant ID (Function Node)

```javascript
const destination = $input.item.json.customerContext.destination;

// Map friendly names to actual VAPI assistant IDs
const assistantMap = {
  'scheduler': 'scheduler-ange-assistant-id',  // Replace with actual ID
  'manager': 'manager-ange-assistant-id',      // Replace with actual ID
  'emergency': '+15550199'                      // Phone number for emergency
};

const targetAssistant = assistantMap[destination] || assistantMap['scheduler'];

return {
  json: {
    ...item.json,
    targetAssistant,
    isPhoneTransfer: destination === 'emergency'
  }
};
```

### Step 5: Perform Transfer (IF Node + HTTP Request)

**Option A: Transfer to Assistant (if NOT emergency)**

**HTTP Request Configuration:**
- **Method**: POST
- **URL**: `https://api.vapi.ai/call/{{$json.callId}}/transfer`
- **Authentication**: Bearer Token
- **Body**:
  ```json
  {
    "destinationType": "assistant",
    "assistantId": "={{$json.targetAssistant}}"
  }
  ```

**Option B: Transfer to Phone Number (if emergency)**

**HTTP Request Configuration:**
- **Method**: POST
- **URL**: `https://api.vapi.ai/call/{{$json.callId}}/transfer`
- **Authentication**: Bearer Token
- **Body**:
  ```json
  {
    "destinationType": "number",
    "number": "={{$json.targetAssistant}}"
  }
  ```

### Step 6: Return Response to VAPI (Function Node)

```javascript
const context = $input.item.json.customerContext;

// Return success response
return {
  json: {
    success: true,
    message: context.firstName
      ? `Perfect, ${context.firstName}. Connecting you now...`
      : "Perfect. Connecting you now...",
    results: [
      {
        customer_name: context.fullName,
        intent: context.intent,
        destination: context.destination,
        transfer_status: "completed"
      }
    ]
  }
};
```

## Alternative: Simpler Implementation (Store Only)

If you want to just **store the context** and let VAPI's built-in `transferCall` handle the actual transfer:

### Simplified n8n Workflow

**Step 1: Webhook** (same as above)

**Step 2: Update Call Variables** (HTTP Request)
```javascript
// Same as Step 3 above - just update variableValues
```

**Step 3: Return Success**
```javascript
return {
  json: {
    success: true,
    message: "Information captured successfully."
  }
};
```

Then in your squad configuration (`members.yaml`), the built-in `transferCall` tool will automatically use the updated variables.

## Using the Extracted Variables in Subsequent Assistants

Once the variables are set via the webhook, ALL subsequent assistants in the squad can use them in their prompts:

**Example: `assistants/scheduler-ange/prompts/system.md`**
```markdown
You are the scheduling specialist for Vicky Dental Clinic.

**Customer Information:**
- Name: {{customer_name}}
- Phone: {{customer_phone}}
- Intent: {{customer_intent}}
- Notes: {{customer_notes}}

**IMPORTANT**:
- Greet the customer warmly using their first name: "Hi {{customer_first_name}}!"
- Reference their intent naturally in your response
- If notes are provided, take them into account

Example greeting: "Hi {{customer_first_name}}! I'd be happy to help you schedule an appointment."
```

## Testing the Webhook

### Test Request (using curl)

```bash
curl -X POST https://n8n-2-u19609.vm.elestio.app/webhook/transfer-with-context \
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
            "name": "transferWithContext",
            "arguments": {
              "destination": "scheduler",
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
  "message": "Perfect, John. Connecting you now...",
  "results": [
    {
      "customer_name": "John Doe",
      "intent": "new_appointment",
      "destination": "scheduler",
      "transfer_status": "completed"
    }
  ]
}
```

## Deployment Steps

1. **Create the n8n workflow** using the nodes described above
2. **Update VAPI API key** in n8n credentials
3. **Get assistant IDs** for scheduler and manager:
   ```bash
   cat assistants/scheduler-ange/vapi_state.json | jq -r '.environments.production.id'
   cat assistants/manager-ange/vapi_state.json | jq -r '.environments.production.id'
   ```
4. **Update the triage assistant**:
   ```bash
   vapi-manager assistant update triage-ange --env production
   ```
5. **Update the squad** to ensure changes propagate:
   ```bash
   vapi-manager squad update ange-vicky --env production
   ```
6. **Test the workflow** with a real call

## Troubleshooting

### Issue: Variables not appearing in subsequent assistants

**Solution**: Ensure the PATCH call to update `assistantOverrides.variableValues` completes BEFORE the transfer happens. Add a delay if needed.

### Issue: Transfer not happening

**Solution**: Check that you're using the correct assistant IDs in the mapping. Verify with:
```bash
vapi-manager assistant get <assistant-id>
```

### Issue: Empty values in variables

**Solution**: Check that the triage assistant is properly extracting the data. Review the conversation logs to see what was passed to the `transferWithContext` function.

## Security Considerations

- Store VAPI API key securely in n8n credentials
- Validate incoming webhook requests
- Consider adding authentication to the webhook endpoint
- Don't log sensitive customer information (PII)

---

**Last Updated**: 2025-10-10
**Framework Version**: 1.0.0
