# Tool Messages

Tool messages allow your assistant to speak during different stages of tool execution, providing feedback to users while tools are being called.

## Overview

Tool messages can be configured for both function tools and the endCall tool. When a tool is executed, you can configure the assistant to speak at four different stages:

- **request-start**: Spoken when the tool call begins
- **request-complete**: Spoken when the tool call completes successfully
- **request-failed**: Spoken when the tool call fails
- **request-response-delayed**: Spoken when the tool response takes longer than expected

## Configuration

Tool messages are configured in your `tools/functions.yaml` file. Add a `messages` array to any function definition.

### Basic Example

```yaml
functions:
  - name: check_availability
    description: Check calendar availability
    parameters:
      type: object
      properties:
        date:
          type: string
    messages:
      - type: request-start
        content: "Let me check the availability for that date..."
      - type: request-complete
        content: "I found the available slots."
      - type: request-failed
        content: "I'm having trouble checking availability right now."
```

### Message Types

#### request-start
Spoken immediately when the function is called.

```yaml
- type: request-start
  content: "Checking availability..."
```

#### request-complete
Spoken when the function completes successfully.

```yaml
- type: request-complete
  content: "I found the information you need!"
```

#### request-failed
Spoken when the function fails or returns an error.

```yaml
- type: request-failed
  content: "I'm having trouble accessing that information right now."
```

#### request-response-delayed
Spoken when the function takes longer than expected. Use `timingMilliseconds` to control when this message is spoken.

```yaml
- type: request-response-delayed
  content: "Still working on it, please bear with me..."
  timingMilliseconds: 5000  # Spoken after 5 seconds
```

### Optional Fields

#### timingMilliseconds

Delay in milliseconds before speaking the message. Only supported for `request-response-delayed` type.

```yaml
- type: request-response-delayed
  content: "This is taking longer than usual..."
  timingMilliseconds: 3000
```

#### language

Language code for the message. Defaults to `en` if not specified.

```yaml
- type: request-start
  content: "Vérification de la disponibilité..."
  language: fr
```

## Complete Example

```yaml
functions:
  - name: book_appointment
    description: Book an appointment for the customer
    server:
      url: https://api.example.com/book
    parameters:
      type: object
      required:
        - date
        - time
        - customer_name
      properties:
        date:
          type: string
          format: date
        time:
          type: string
        customer_name:
          type: string
    messages:
      - type: request-start
        content: "I'm booking your appointment now..."
      - type: request-complete
        content: "Your appointment has been successfully booked!"
      - type: request-failed
        content: "I couldn't complete the booking. Let me help you try again."
      - type: request-response-delayed
        content: "The booking system is taking a bit longer than usual, please hold on..."
        timingMilliseconds: 4000
```

## Mixed Configuration

You can have some functions with messages and others without. Messages are completely optional.

```yaml
functions:
  # Function with messages
  - name: check_availability
    description: Check calendar availability
    parameters:
      type: object
    messages:
      - type: request-start
        content: "Checking availability..."
      - type: request-complete
        content: "Found available slots!"

  # Function without messages (works as before)
  - name: get_pricing
    description: Get pricing information
    parameters:
      type: object
```

## Best Practices

1. **Keep messages concise**: Users should understand what's happening quickly
2. **Be specific**: Match the message to the actual operation
3. **Handle failures gracefully**: Provide reassurance and next steps in failure messages
4. **Use delayed messages wisely**: Only for operations that might take 3+ seconds
5. **Maintain consistent tone**: Match your assistant's personality

## Examples by Use Case

### E-commerce

```yaml
- name: check_inventory
  description: Check product inventory
  parameters:
    type: object
  messages:
    - type: request-start
      content: "Let me check if that item is in stock..."
    - type: request-complete
      content: "I've checked our inventory for you."
    - type: request-failed
      content: "I'm having trouble accessing our inventory system right now."
```

### Healthcare/Appointments

```yaml
- name: schedule_appointment
  description: Schedule a medical appointment
  parameters:
    type: object
  messages:
    - type: request-start
      content: "I'm scheduling your appointment now..."
    - type: request-complete
      content: "Your appointment has been scheduled! You'll receive a confirmation shortly."
    - type: request-failed
      content: "I couldn't complete the scheduling. Let me transfer you to our booking team."
    - type: request-response-delayed
      content: "Our scheduling system is responding slowly. I'm still working on it..."
      timingMilliseconds: 5000
```

### Customer Service

```yaml
- name: lookup_order
  description: Look up order status
  parameters:
    type: object
  messages:
    - type: request-start
      content: "Looking up your order now..."
    - type: request-complete
      content: "I found your order information."
    - type: request-failed
      content: "I couldn't find that order. Could you verify the order number?"
```

## Technical Details

- Messages use VAPI's contents array format internally
- The simplified `content` field is automatically converted to the proper format
- Only `timingMilliseconds` is currently supported as an optional field
- Empty messages arrays are ignored (treated as no messages)
- Messages are validated before being sent to VAPI

## endCall Tool Messages

The endCall tool also supports messages. Create an `endcall.yaml` file in your `tools/` directory:

```yaml
messages:
  - type: request-start
    content: "Thank you for calling. Have a great day!"
```

### Example with Multiple Messages

```yaml
messages:
  - type: request-start
    content: "I'll end the call now. Thank you for your time!"
  - type: request-complete
    content: "Goodbye!"
```

This allows you to customize what the assistant says when ending calls, providing a better user experience.

## Migration

If you have existing assistants without tool messages, they will continue to work exactly as before. Tool messages are completely optional and backward compatible.
