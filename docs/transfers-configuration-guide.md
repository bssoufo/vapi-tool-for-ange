# Multiple Transfer Destinations Configuration Guide

This guide shows how to configure multiple transfer destinations for different scenarios in your `transfers.yaml` file.

## Basic Multiple Numbers

```yaml
# assistants/your_assistant/tools/transfers.yaml
transfers:
- type: number
  number: "+14182640300"
  description: "Transfer to general support line"

- type: number
  number: "+14182640301"
  description: "Transfer to emergency services"

- type: number
  number: "+14182640302"
  description: "Transfer to technical support"

- type: number
  number: "+14182640303"
  description: "Transfer to billing department"

- type: number
  number: "+14182640304"
  description: "Transfer to appointment scheduling"
```

## Advanced Configuration with Conditions

```yaml
transfers:
# Emergency transfers (high priority)
- type: number
  number: "+14182640911"
  description: "Emergency line for urgent medical issues"
  priority: emergency
  keywords: ["emergency", "urgent", "immediate", "911"]

- type: number
  number: "+14182640301"
  description: "After hours emergency line"
  priority: emergency
  active_hours: "18:01-07:59"
  keywords: ["emergency", "after hours"]

# Department-specific transfers
- type: number
  number: "+14182640302"
  description: "Technical support for system issues"
  department: technical
  keywords: ["technical", "system", "bug", "error", "not working"]

- type: number
  number: "+14182640303"
  description: "Billing and payment inquiries"
  department: billing
  keywords: ["billing", "payment", "invoice", "charge", "refund"]

- type: number
  number: "+14182640304"
  description: "Appointment scheduling and changes"
  department: scheduling
  keywords: ["appointment", "schedule", "booking", "reschedule", "cancel"]

- type: number
  number: "+14182640305"
  description: "Sales and new customer inquiries"
  department: sales
  keywords: ["sales", "new customer", "pricing", "quote", "purchase"]

# Manager/supervisor escalation
- type: number
  number: "+14182640306"
  description: "Transfer to supervisor/manager"
  escalation: true
  keywords: ["manager", "supervisor", "escalate", "complaint"]

# International support
- type: number
  number: "+14182640307"
  description: "Spanish language support"
  language: spanish
  keywords: ["español", "spanish", "habla español"]

# General fallback
- type: number
  number: "+14182640300"
  description: "General support line (fallback)"
  fallback: true
```

## Environment-Specific Numbers

You can use environment variables for different phone numbers per environment:

```yaml
transfers:
- type: number
  number: "${SUPPORT_PHONE_DEVELOPMENT}"  # +14182640300 in dev
  description: "Development support line"

- type: number
  number: "${SUPPORT_PHONE_PRODUCTION}"   # +15551234567 in prod
  description: "Production support line"

- type: number
  number: "${EMERGENCY_PHONE}"
  description: "Emergency contact"
```

## Mixed Transfer Types

```yaml
transfers:
# Phone numbers
- type: number
  number: "+14182640300"
  description: "Human support agent"

- type: number
  number: "+14182640911"
  description: "Emergency services"

# Assistant-to-assistant transfers (within squad)
- type: assistant
  assistant_name: "booking_assistant_pa"
  description: "Transfer to booking specialist"

- type: assistant
  assistant_name: "billing_assistant_pa"
  description: "Transfer to billing specialist"
```

## Best Practices

### 1. Clear Descriptions
Use descriptive messages that help both the AI and users understand the purpose:

```yaml
- type: number
  number: "+14182640300"
  description: "Transfer to general support for account questions and technical issues"
```

### 2. Logical Organization
Group related numbers together:

```yaml
transfers:
# Emergency numbers (first for priority)
- type: number
  number: "+14182640911"
  description: "Medical emergencies"

- type: number
  number: "+14182640912"
  description: "Security emergencies"

# Department numbers
- type: number
  number: "+14182640301"
  description: "Sales department"

- type: number
  number: "+14182640302"
  description: "Support department"

# Management escalation (last)
- type: number
  number: "+14182640999"
  description: "Manager escalation"
```

### 3. Use Keywords for Context
Help the AI understand when to use each number:

```yaml
- type: number
  number: "+14182640302"
  description: "Technical support for system errors, bugs, and technical questions"
  keywords: ["technical", "system", "error", "bug", "not working", "broken"]
```

## How It Works in VAPI

When you configure multiple transfers, the framework:

1. **Processes all transfers** from `transfers.yaml`
2. **Creates a single transferCall tool** with all destinations
3. **Includes descriptions** for the AI to choose appropriately
4. **Validates phone numbers** and environment variables

The AI assistant will have access to all transfer options and can choose the most appropriate one based on the conversation context and the descriptions you provide.

## Testing Multiple Transfers

After configuring multiple transfers, update your assistant:

```bash
poetry run vapi-manager assistant update triage_assistant_pa --env development
```

The assistant will now have access to all configured transfer destinations through a single `transferCall` tool with multiple destination options.