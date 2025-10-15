# Transfer with Context - Quick Setup Summary

## What Was Done

Added a custom transfer tool to the **triage-ange** assistant that:
1. Extracts customer name, phone, and intent during the greeting
2. Sends this data to an n8n webhook
3. Updates the VAPI call with `variableValues` so all subsequent assistants can use the data
4. Performs the transfer to the appropriate specialist

## Files Modified

### 1. `assistants/triage-ange/tools/functions.yaml`
**Added**: `transferWithContext` function tool

**What it does**:
- Replaces the default `transferCall` tool
- Captures customer information (first name, last name, phone, intent, notes)
- Sends data to n8n webhook for processing

**Required parameters**:
- `destination`: scheduler | manager | emergency
- `intent`: new_appointment | modify_appointment | cancel_appointment | emergency | general_inquiry

**Optional parameters**:
- `customer_first_name`
- `customer_last_name`
- `customer_phone`
- `notes`

### 2. `assistants/triage-ange/prompts/system.md`
**Updated**: Data extraction instructions and routing logic

**Key changes**:
- Added explicit instructions to extract customer name from first response
- Updated routing logic to use `transferWithContext` instead of default `transferCall`
- Added examples of how to extract names from user responses

## How It Works

### Flow Diagram

```
1. Customer calls → Triage Assistant greets
   ↓
2. Customer responds: "Hi, this is John Smith, I need to book an appointment"
   ↓
3. Triage Assistant extracts:
   - first_name: "John"
   - last_name: "Smith"
   - intent: "new_appointment"
   ↓
4. Triage Assistant calls: transferWithContext()
   ↓
5. n8n webhook receives data
   ↓
6. n8n updates VAPI call with variableValues:
   {
     "customer_name": "John Smith",
     "customer_first_name": "John",
     "customer_last_name": "Smith",
     "customer_intent": "new_appointment"
   }
   ↓
7. Transfer happens to Scheduler Assistant
   ↓
8. Scheduler Assistant greets: "Hi John! I'd be happy to help you schedule an appointment."
```

## Next Steps

### 1. Create n8n Webhook (REQUIRED)

See detailed guide: `docs/n8n-transfer-with-context-webhook.md`

**Minimum implementation** (4 nodes):
1. **Webhook** - Receive POST at `/webhook/transfer-with-context`
2. **Function** - Extract customer data from request
3. **HTTP Request** - PATCH to `https://api.vapi.ai/call/{callId}` with `variableValues`
4. **Response** - Return success message

**Webhook URL**: `https://n8n-2-u19609.vm.elestio.app/webhook/transfer-with-context`

### 2. Update Assistant Prompts to Use Variables

Update **all** assistants in your squad to use the extracted variables:

#### `assistants/scheduler-ange/prompts/system.md`
```markdown
You are the scheduling specialist for Vicky Dental Clinic.

Customer Information:
- Name: {{customer_name}}
- First Name: {{customer_first_name}}
- Phone: {{customer_phone}}
- Intent: {{customer_intent}}

IMPORTANT: Greet the customer warmly using their first name.

Example: "Hi {{customer_first_name}}! I'd be happy to help you schedule an appointment."
```

#### `assistants/manager-ange/prompts/system.md`
```markdown
You are the appointment manager for Vicky Dental Clinic.

Customer Information:
- Name: {{customer_name}}
- Phone: {{customer_phone}}
- Intent: {{customer_intent}}

IMPORTANT: Use their name throughout the conversation for a personalized experience.

Example: "Hi {{customer_first_name}}! I can help you with that appointment."
```

### 3. Deploy Updated Assistants

```bash
# Update the triage assistant with new tool
vapi-manager assistant update triage-ange --env production

# Update scheduler and manager assistants with new prompts
vapi-manager assistant update scheduler-ange --env production
vapi-manager assistant update manager-ange --env production

# Update the squad to ensure all changes propagate
vapi-manager squad update ange-vicky --env production
```

### 4. Test the Implementation

**Test call flow**:
1. Call your VAPI number
2. When greeted, say: "Hi, this is [Your Name], I need to book an appointment"
3. Verify the transfer happens
4. **Listen carefully**: Does the scheduler greet you using your first name?

**Expected behavior**:
- Triage: "Thank you for calling Vicky Dental, this is Sarah. How can I help you today?"
- You: "Hi, this is John, I need to book an appointment"
- [Silent transfer]
- Scheduler: "Hi John! I'd be happy to help you schedule an appointment."

## Troubleshooting

### Problem: Name not being used by scheduler

**Check**:
1. Is the n8n webhook receiving the data? (Check n8n execution logs)
2. Is the VAPI call being updated? (Check VAPI dashboard call logs)
3. Are the variables in the scheduler prompt correct? ({{customer_first_name}})

**Solution**:
- Add logging to n8n workflow to see what data is received
- Test the webhook directly with curl (see webhook docs)
- Verify scheduler assistant has been deployed with updated prompt

### Problem: Transfer not happening

**Check**:
1. Is the `transferWithContext` function being called? (Check VAPI call logs)
2. Is the webhook responding correctly?
3. Are there any errors in n8n execution?

**Solution**:
- Review the function definition in `functions.yaml`
- Ensure webhook URL is correct and accessible
- Check n8n workflow is activated

### Problem: Variables are empty

**Check**:
1. Is the triage assistant extracting the name correctly?
2. Is the name being passed to the webhook?

**Solution**:
- Review conversation transcript to see what the AI extracted
- Update the triage system prompt to be more explicit about extraction
- Test with very clear name introductions: "This is John Smith"

## Available Variables

After setup, these variables are available to **all assistants** in the squad:

- `{{customer_name}}` - Full name (e.g., "John Smith")
- `{{customer_first_name}}` - First name only (e.g., "John")
- `{{customer_last_name}}` - Last name only (e.g., "Smith")
- `{{customer_phone}}` - Phone number (e.g., "+15551234567")
- `{{customer_intent}}` - Intent (e.g., "new_appointment")
- `{{customer_notes}}` - Any additional notes

## Benefits

✅ **Personalized experience**: Greet customers by name throughout the call
✅ **Context preservation**: All assistants know the customer's intent
✅ **Better routing**: Transfer based on explicit intent, not just AI guessing
✅ **CRM integration ready**: Customer data can be logged to your database
✅ **No conversation history needed**: Variables are explicit, not inferred

## Future Enhancements

Consider adding:
- **Database storage**: Store customer context in database for future calls
- **CRM lookup**: If phone number recognized, pre-load customer information
- **Appointment history**: Retrieve past appointments and include in transfer
- **Sentiment analysis**: Track customer mood and pass to next assistant
- **Multi-language support**: Detect language preference and pass to squad

---

**Status**: Ready for implementation
**Created**: 2025-10-10
**Last Updated**: 2025-10-10
