# Analysis Configuration Guide

Complete guide for configuring call analysis with structured data extraction and summarization for VAPI assistants.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration Files](#configuration-files)
- [Step-by-Step Setup](#step-by-step-setup)
- [Schema Design Best Practices](#schema-design-best-practices)
- [Prompt Writing Guidelines](#prompt-writing-guidelines)
- [Deployment](#deployment)
- [Accessing Analysis Results](#accessing-analysis-results)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## Overview

VAPI's Analysis Plan allows you to automatically extract structured data and generate summaries from voice conversations. This feature enables:

- **Structured Data Extraction**: Extract specific information (customer details, appointments, lead scoring) in a structured JSON format
- **Call Summarization**: Generate concise summaries of conversations
- **Automated Insights**: Capture sentiment, urgency, and action items automatically

### How It Works

After each call, VAPI uses Claude Sonnet (with GPT-4o fallback) to:
1. Analyze the conversation transcript
2. Extract data according to your JSON schema
3. Generate a summary based on your prompts
4. Send results to your webhook endpoint

---

## Prerequisites

- Existing assistant configuration in `assistants/your_assistant/`
- VAPI Manager framework installed
- Basic understanding of JSON Schema
- Webhook endpoint configured (optional, for receiving results)

---

## Quick Start

For an existing assistant, you need to create 5 files:

```
assistants/your_assistant/
├── assistant.yaml                    # Update this file
├── schemas/
│   └── structured_data.yaml         # CREATE: JSON Schema for extraction
└── prompts/
    ├── extraction-system-prompt.md  # CREATE: System prompt for extraction
    ├── extraction-user-prompt.md    # CREATE: User prompt for extraction
    ├── summary-system-prompt.md     # CREATE: System prompt for summary
    └── summary-user-prompt.md       # CREATE: User prompt for summary
```

**Minimal setup time**: 30-60 minutes for a basic configuration

---

## Configuration Files

### 1. Enable Analysis in `assistant.yaml`

Add or update the `analysisPlan` section in your assistant configuration:

```yaml
# assistants/your_assistant/assistant.yaml

# ... existing configuration ...

analysisPlan:
  minMessagesThreshold: 2  # Minimum number of messages before analysis runs

  summaryPlan:
    enabled: true
    timeoutSeconds: 15     # Optional: analysis timeout

  structuredDataPlan:
    enabled: true
    timeoutSeconds: 15     # Optional: analysis timeout

# Optional: Configure server messages to receive analysis results
serverMessages:
  - end-of-call-report
```

**Configuration Options:**

- `minMessagesThreshold`: Number of conversation turns required before analysis runs (default: 2)
- `summaryPlan.enabled`: Enable/disable summary generation
- `structuredDataPlan.enabled`: Enable/disable structured data extraction
- `timeoutSeconds`: Maximum time in seconds for analysis (default: 15)

---

## Step-by-Step Setup

### Step 1: Create the Schema Directory

```bash
mkdir -p assistants/your_assistant/schemas
```

### Step 2: Define Your Structured Data Schema

Create `schemas/structured_data.yaml` with your JSON Schema definition.

**File**: `assistants/your_assistant/schemas/structured_data.yaml`

```yaml
type: object

# Define which fields are absolutely required
required:
  - call_type
  - sentiment_analysis

properties:
  # Customer Information Section
  customer_info:
    type: object
    properties:
      first_name:
        type: string
        description: "Customer's first name if provided"

      last_name:
        type: string
        description: "Customer's last name if provided"

      phone_number:
        type: string
        description: "Customer's phone number"
        pattern: "^\\+?1?\\d{10,14}$"  # Phone number validation pattern

      email:
        type: string
        format: email
        description: "Customer's email address"

      preferred_contact:
        type: string
        enum: ["phone", "email", "text", "any"]
        description: "Customer's preferred contact method"

  # Call Classification
  call_type:
    type: string
    enum:
      - new_inquiry
      - existing_customer
      - appointment_booking
      - information_request
      - complaint
      - follow_up
    description: "Primary purpose or type of the call"

  # Sentiment Analysis
  sentiment_analysis:
    type: object
    required:
      - overall_sentiment
      - urgency_level
    properties:
      overall_sentiment:
        type: string
        enum:
          - very_positive
          - positive
          - neutral
          - negative
          - frustrated
        description: "Customer's overall emotional tone during the call"

      urgency_level:
        type: string
        enum:
          - immediate
          - high
          - medium
          - low
          - casual
        description: "Level of urgency expressed by customer"

      customer_satisfaction:
        type: string
        enum:
          - satisfied
          - neutral
          - dissatisfied
        description: "Customer satisfaction with the interaction"

  # Lead Scoring
  lead_quality:
    type: string
    enum:
      - hot        # Ready to buy/book immediately
      - warm       # Interested, needs follow-up
      - cool       # Exploring options
      - cold       # Not interested or unqualified
    description: "Assessment of lead quality and likelihood to convert"

  # Call Outcome
  outcome:
    type: object
    properties:
      action_taken:
        type: string
        enum:
          - appointment_scheduled
          - information_provided
          - transferred
          - callback_scheduled
          - issue_resolved
          - no_action
        description: "Primary action taken during the call"

      follow_up_required:
        type: boolean
        description: "Whether follow-up is needed"

      follow_up_date:
        type: string
        format: date
        description: "Date for follow-up if scheduled"

  # Additional Notes
  key_points:
    type: array
    items:
      type: string
    description: "Key discussion points or important details from the call"

  notes:
    type: string
    description: "Any additional notes or observations from the conversation"
```

**Schema Features You Can Use:**

- **Types**: `string`, `number`, `integer`, `boolean`, `object`, `array`, `null`
- **String Formats**: `email`, `date`, `date-time`, `uri`, `uuid`
- **Patterns**: Regular expressions for validation (e.g., phone numbers)
- **Enums**: Controlled vocabularies for consistent values
- **Nested Objects**: Complex hierarchical data structures
- **Arrays**: Lists of items
- **Required Fields**: Mark fields that must always be present

---

### Step 3: Create Extraction System Prompt

Create the system prompt that instructs the AI on how to extract data.

**File**: `assistants/your_assistant/prompts/extraction-system-prompt.md`

```markdown
# Data Extraction Specialist

You are a data extraction specialist for [Your Business Name].

Your role is to analyze conversation transcripts and extract structured information according to the provided JSON schema.

## Extraction Guidelines

### Accuracy First
- Extract only information that was explicitly mentioned in the conversation
- Use `null` for fields where information was not provided
- Do not infer or assume information that wasn't stated
- Pay attention to corrections or updates made during the conversation

### Data Quality
- Validate phone numbers and email addresses if provided
- Ensure dates and times are in the correct format
- Normalize data (e.g., capitalize names consistently)
- Extract complete information when available

### Special Attention Points

1. **Customer Information**
   - Capture full names, phone numbers, and email addresses
   - Note preferred contact methods if mentioned
   - Track whether customer is new or existing

2. **Call Classification**
   - Identify the primary purpose of the call
   - Distinguish between inquiry types
   - Note if multiple topics were discussed

3. **Sentiment Analysis**
   - Assess overall customer sentiment throughout the call
   - Identify urgency based on language and context
   - Evaluate customer satisfaction with the interaction

4. **Lead Quality**
   - Hot: Customer ready to take action immediately
   - Warm: Interested customer needing follow-up
   - Cool: Browsing or exploring options
   - Cold: Not currently interested or unqualified

5. **Outcomes and Actions**
   - Record what action was taken (booking, transfer, etc.)
   - Note any follow-up requirements
   - Capture important discussion points

## Schema Compliance

Return structured data that **exactly matches** the provided JSON schema.
- Use the exact enum values defined in the schema
- Follow the required field specifications
- Use null for optional fields without data

**Schema:** {{schema}}
```

---

### Step 4: Create Extraction User Prompt

Create the user prompt that provides the conversation and requests extraction.

**File**: `assistants/your_assistant/prompts/extraction-user-prompt.md`

```markdown
Extract ALL relevant information from this conversation.

## Required Data Points

Analyze the conversation and extract the following information:

### 1. Customer Information
- First name and last name
- Phone number (with validation)
- Email address
- Preferred contact method
- Customer status (new or existing)

### 2. Call Type
Classify the primary purpose:
- New inquiry
- Existing customer follow-up
- Appointment booking
- Information request
- Complaint or issue
- Follow-up call

### 3. Sentiment Analysis
Assess the customer's emotional state:
- **Overall Sentiment**: Very positive, positive, neutral, negative, or frustrated
- **Urgency Level**: Immediate, high, medium, low, or casual browsing
- **Customer Satisfaction**: Satisfied, neutral, or dissatisfied with the interaction

### 4. Lead Quality Assessment
Score the lead based on readiness to act:
- **Hot**: Ready to buy/book immediately, high intent
- **Warm**: Interested and engaged, needs follow-up
- **Cool**: Exploring options, early stage
- **Cold**: Not interested or unqualified

### 5. Call Outcome
- What action was taken during the call?
- Is follow-up required?
- When should follow-up occur?
- Key points discussed
- Any additional notes

## Extraction Instructions

1. Read the entire conversation carefully
2. Extract information that was explicitly stated
3. Use `null` for any fields where information was not provided
4. Ensure all data matches the schema format exactly
5. Use only the enum values defined in the schema
6. Include any important context in the notes field

Return the extracted data as JSON matching the provided schema exactly.

**Conversation Transcript:**
{{transcript}}
```

---

### Step 5: Create Summary System Prompt

Create the system prompt for generating call summaries.

**File**: `assistants/your_assistant/prompts/summary-system-prompt.md`

```markdown
# Call Summary Specialist

You are an AI assistant specialized in summarizing customer service conversations.

## Your Role

Create concise, actionable summaries that capture the essential information from voice conversations.

## Summary Guidelines

### Focus Areas

1. **Customer Intent**
   - What did the customer want to accomplish?
   - What was their primary reason for calling?

2. **Key Information**
   - Important details discussed (names, dates, specifics)
   - Products, services, or topics of interest
   - Any commitments or promises made

3. **Actions Taken**
   - What was done during the call?
   - Were any bookings, transfers, or tasks completed?
   - What tools or resources were used?

4. **Next Steps**
   - Follow-up requirements and timeline
   - Pending actions or decisions
   - Customer expectations

5. **Sentiment and Urgency**
   - Customer's emotional state
   - Level of satisfaction
   - Urgency of their needs

### Writing Style

- **Concise**: 3-5 sentences typically sufficient
- **Objective**: State facts without interpretation
- **Actionable**: Focus on what matters for follow-up
- **Structured**: Use clear sections or bullet points
- **Professional**: Maintain business communication standards

### What to Avoid

- Don't include every detail of the conversation
- Avoid subjective opinions or judgments
- Don't repeat information multiple times
- Skip pleasantries unless relevant to outcome
- Don't use technical jargon unnecessarily

## Summary Format

Structure your summary clearly:
- Start with the primary purpose
- List key details and actions
- End with next steps or outcomes
```

---

### Step 6: Create Summary User Prompt

Create the user prompt for summary generation.

**File**: `assistants/your_assistant/prompts/summary-user-prompt.md`

```markdown
Provide a concise summary of this conversation.

## Summary Requirements

Include the following elements in your summary:

### 1. Call Purpose
- What was the customer's primary reason for calling?
- What did they want to accomplish?

### 2. Key Information Discussed
- Important details mentioned (names, dates, specifics)
- Products, services, or topics of interest
- Any specific requests or questions

### 3. Actions Taken
- What was done during the call?
- Appointments scheduled, transfers made, information provided
- Tools or functions used (if any)

### 4. Customer Sentiment
- Overall emotional tone of the customer
- Urgency level expressed
- Satisfaction with the interaction

### 5. Outcomes and Next Steps
- What was accomplished?
- Follow-up required and timeline
- Any pending actions or decisions
- Customer expectations set

## Format

Provide a well-structured summary using:
- Clear, professional language
- Bullet points or numbered lists where appropriate
- 3-5 sentences or key points
- Emphasis on actionable information

Focus on information that would be valuable for:
- Follow-up calls or actions
- Understanding customer needs
- Tracking conversation outcomes
- Quality assurance and improvement

**Conversation Transcript:**
{{transcript}}
```

---

## Schema Design Best Practices

### 1. Start Simple, Iterate

Begin with essential fields and expand based on needs:

```yaml
# Minimal schema
type: object
required:
  - call_type
properties:
  call_type:
    type: string
    enum: ["inquiry", "booking", "support"]
  customer_name:
    type: string
  notes:
    type: string
```

### 2. Use Descriptive Field Names

Good field names are self-documenting:

```yaml
# Good ✓
appointment_scheduled_date:
  type: string
  format: date
  description: "Date when appointment was scheduled"

# Avoid ✗
appt_dt:
  type: string
```

### 3. Provide Clear Descriptions

Help the AI understand what to extract:

```yaml
urgency_level:
  type: string
  enum: ["immediate", "high", "medium", "low"]
  description: "Customer's urgency based on timeline mentioned, language used, and expressed needs"
```

### 4. Use Enums for Controlled Values

Enums ensure consistency:

```yaml
call_outcome:
  type: string
  enum:
    - appointment_booked
    - information_provided
    - transferred
    - callback_scheduled
  description: "Primary outcome of the call"
```

### 5. Mark Only Critical Fields as Required

Use `required` sparingly for fields that should always be present:

```yaml
required:
  - call_type        # Always needed
  - call_timestamp   # Always available

# Optional fields don't need to be in required array
properties:
  customer_email:   # May not always be collected
    type: string
```

### 6. Nested Objects for Related Data

Group related information:

```yaml
appointment:
  type: object
  properties:
    date:
      type: string
      format: date
    time:
      type: string
      pattern: "^\\d{2}:\\d{2}$"
    type:
      type: string
      enum: ["consultation", "viewing", "follow_up"]
    confirmed:
      type: boolean
```

### 7. Arrays for Multiple Items

Use arrays for lists:

```yaml
interests:
  type: array
  items:
    type: string
  description: "List of topics or products customer expressed interest in"

action_items:
  type: array
  items:
    type: object
    properties:
      task:
        type: string
      priority:
        type: string
        enum: ["high", "medium", "low"]
      due_date:
        type: string
        format: date
```

### 8. Use Patterns for Validation

Regular expressions ensure data quality:

```yaml
phone_number:
  type: string
  pattern: "^\\+?1?\\d{10,14}$"
  description: "Phone number in international format"

email:
  type: string
  format: email
  description: "Valid email address"

postal_code:
  type: string
  pattern: "^[A-Z]\\d[A-Z] \\d[A-Z]\\d$"  # Canadian postal code
  description: "Canadian postal code (e.g., A1A 1A1)"
```

---

## Prompt Writing Guidelines

### Extraction Prompts

#### System Prompt Best Practices

1. **Define the Role Clearly**
   ```markdown
   You are a data extraction specialist for [Business Name].
   ```

2. **Explain the Task**
   ```markdown
   Your role is to analyze conversation transcripts and extract structured
   information according to the provided JSON schema.
   ```

3. **Provide Specific Guidelines**
   - What to extract
   - What to avoid
   - How to handle edge cases
   - Accuracy requirements

4. **Explain Special Fields**
   ```markdown
   ## Lead Quality Scoring
   - Hot: Customer ready to purchase immediately, clear timeline
   - Warm: Interested customer, needs follow-up within 1-2 weeks
   - Cool: Exploring options, timeline 1+ months
   - Cold: Not currently interested or unqualified
   ```

#### User Prompt Best Practices

1. **Be Explicit About Requirements**
   ```markdown
   Extract ALL relevant information from this conversation:

   1. Customer details (name, contact info)
   2. Purpose of call
   3. Sentiment and urgency
   4. Actions taken
   5. Follow-up needs
   ```

2. **Use Clear Sections**
   - Number your requirements
   - Use headers
   - Provide examples if helpful

3. **Reference the Transcript**
   ```markdown
   **Conversation Transcript:**
   {{transcript}}
   ```

### Summary Prompts

#### System Prompt Best Practices

1. **Define Summary Style**
   ```markdown
   Create concise, actionable summaries that capture essential information.

   - Length: 3-5 sentences
   - Style: Objective and professional
   - Focus: Actionable information for follow-up
   ```

2. **Provide Structure Guidance**
   ```markdown
   ## Summary Format
   1. Start with call purpose
   2. List key details
   3. Note actions taken
   4. End with next steps
   ```

#### User Prompt Best Practices

1. **List Required Elements**
   ```markdown
   Include:
   1. Call purpose
   2. Key information discussed
   3. Actions taken
   4. Outcomes and next steps
   ```

2. **Specify Format**
   ```markdown
   Use bullet points for clarity and include specific details
   (names, dates, amounts) that are important for follow-up.
   ```

---

## Deployment

### Update Your Assistant

Once all files are created, deploy the updated configuration:

```bash
# For existing assistants, use update command
vapi-manager assistant update your_assistant --env development

# Verify the update
vapi-manager assistant get $(cat assistants/your_assistant/vapi_state.json | jq -r '.environments.development.id')
```

### Deployment Process

The framework automatically:
1. Loads your `structured_data.yaml` schema
2. Loads all extraction and summary prompt files
3. Builds the complete `analysisPlan` configuration
4. Updates the assistant in VAPI

### Verify Configuration

Check that analysis is configured:

```bash
# View assistant details in VAPI dashboard
# or use the API to inspect the analysisPlan configuration
```

---

## Accessing Analysis Results

### Via Webhook

Configure your assistant to send analysis results:

```yaml
# assistants/your_assistant/assistant.yaml
serverMessages:
  - end-of-call-report

server:
  url: "https://your-webhook-endpoint.com/vapi/callback"
  timeoutSeconds: 20
```

### Webhook Payload Structure

After a call ends, VAPI sends analysis results:

```json
{
  "message": {
    "type": "end-of-call-report",
    "call": {
      "id": "call-uuid",
      "analysis": {
        "summary": "Customer called to inquire about property at 123 Main St...",
        "structuredData": {
          "customer_info": {
            "first_name": "John",
            "phone_number": "+15551234567"
          },
          "call_type": "property_inquiry",
          "sentiment_analysis": {
            "overall_sentiment": "positive",
            "urgency_level": "medium"
          },
          "lead_quality": "warm"
        },
        "successEvaluation": "8/10"
      }
    }
  }
}
```

### Processing Analysis Results

Example webhook handler (Node.js/Express):

```javascript
app.post('/vapi/callback', (req, res) => {
  const { message } = req.body;

  if (message.type === 'end-of-call-report') {
    const analysis = message.call.analysis;

    // Access summary
    const summary = analysis.summary;

    // Access structured data
    const structuredData = analysis.structuredData;
    const leadQuality = structuredData.lead_quality;
    const customerInfo = structuredData.customer_info;

    // Process data (save to database, trigger workflows, etc.)
    saveToDatabase(message.call.id, {
      summary,
      structuredData,
      callDuration: message.call.duration
    });

    // Trigger follow-up actions
    if (leadQuality === 'hot') {
      notifySalesTeam(customerInfo);
    }
  }

  res.sendStatus(200);
});
```

---

## Examples

### Example 1: Dental Clinic

**Schema** (`schemas/structured_data.yaml`):
```yaml
type: object
required:
  - call_type
  - transferred_to
  - sentimentAnalysis

properties:
  firstName:
    type: string
  lastName:
    type: string
  phoneNumber:
    type: string

  call_type:
    type: string
    enum: [emergency, informational, booking, management]

  transferred_to:
    type: string
    enum: [emergency_line, scheduler, manager, none]

  appointmentType:
    type: string
    enum: [cleaning, checkup, consultation, procedure, emergency]

  sentimentAnalysis:
    type: object
    properties:
      urgency:
        type: string
        enum: [low, medium, high, emergency]
      positivity:
        type: string
        enum: [negative, neutral, positive, very_positive]

  dentalConcern:
    type: string
    description: "Primary dental concern or reason for calling"

  painLevel:
    type: integer
    minimum: 0
    maximum: 10
```

### Example 2: Real Estate Brokerage

**Schema** (`schemas/structured_data.yaml`):
```yaml
type: object
required:
  - call_type
  - customer_status

properties:
  customer_info:
    type: object
    properties:
      validated_phone:
        type: string
        pattern: "^\\d{3}-\\d{3}-\\d{4}$"
      first_name:
        type: string
      email:
        type: string
        format: email

  call_type:
    type: string
    enum:
      - property_inquiry_specific
      - property_inquiry_beginner
      - appointment_booking
      - seller_inquiry

  customer_status:
    type: string
    enum:
      - first_time_buyer
      - beginner_buyer
      - informed_buyer
      - existing_client
      - seller

  property_details:
    type: object
    properties:
      property_address:
        type: string
      property_type:
        type: string
        enum: [house, condo, duplex, land, commercial]
      price_range:
        type: object
        properties:
          min:
            type: number
          max:
            type: number
      bedrooms:
        type: integer

  appointment_details:
    type: object
    properties:
      appointment_type:
        type: string
        enum: [property_showing, discovery_call, consultation]
      appointment_date:
        type: string
        format: date

  sentiment_analysis:
    type: object
    properties:
      overall_sentiment:
        type: string
        enum: [very_positive, positive, neutral, negative, frustrated]
      urgency_level:
        type: string
        enum: [immediate, high, medium, low, browsing]

  lead_quality:
    type: object
    properties:
      score:
        type: string
        enum: [hot, warm, cool, cold]
      timeline:
        type: string
        enum: [immediate, within_week, within_month, within_3_months]
```

---

## Troubleshooting

### Analysis Not Running

**Problem**: Analysis results not appearing after calls

**Solutions**:
1. Check `minMessagesThreshold` - ensure call had enough messages
2. Verify `analysisPlan.enabled: true` in assistant.yaml
3. Check VAPI dashboard for error messages
4. Ensure assistant was deployed after adding analysis configuration

### Incorrect Data Extraction

**Problem**: Extracted data doesn't match conversation

**Solutions**:
1. **Review your prompts**: Be more specific about what to extract
2. **Check schema descriptions**: Add clearer field descriptions
3. **Provide examples**: Add examples in extraction prompts
4. **Test with sample calls**: Iterate on prompts based on results

### Schema Validation Errors

**Problem**: "Schema validation failed" errors

**Solutions**:
1. Validate your YAML syntax using a YAML validator
2. Ensure `type: object` at root level
3. Check that all `enum` values are arrays
4. Verify `required` fields exist in `properties`
5. Test patterns with regex validator

### Missing Required Fields

**Problem**: Extraction fails due to missing required fields

**Solutions**:
1. Review which fields are truly required
2. Move optional fields out of `required` array
3. Update extraction prompt to emphasize required fields
4. Consider using `null` for unavailable data

### Summary Too Long or Too Short

**Problem**: Summaries not the right length

**Solutions**:
1. Be specific about length in summary prompts: "3-5 sentences"
2. Provide examples of good summaries
3. Emphasize conciseness or detail as needed
4. Adjust based on conversation complexity

### Webhook Not Receiving Results

**Problem**: Analysis complete but webhook not called

**Solutions**:
1. Verify `serverMessages: [end-of-call-report]` in config
2. Check webhook URL is accessible
3. Verify webhook timeout is sufficient (20+ seconds)
4. Check webhook returns 200 status
5. Review VAPI dashboard for delivery errors

---

## Additional Resources

- **VAPI Documentation**: https://docs.vapi.ai/assistants/call-analysis
- **JSON Schema Reference**: https://json-schema.org/understanding-json-schema/
- **Framework Examples**: See `assistants/real-estate-triage/` for complete example
- **Testing**: Use VAPI dashboard to review analysis results from test calls

---

## Support

For questions or issues:
- Framework issues: Check project README
- VAPI platform issues: Visit VAPI documentation or support
- Schema/prompt help: Review examples in `assistants/` directory

---

**Last Updated**: 2025-10-09
**Framework Version**: 1.0.0
