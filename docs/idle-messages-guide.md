# Idle Messages (Hooks) Configuration Guide

## Overview

Idle messages are automated prompts that your assistant can send during periods of user inactivity. This helps maintain engagement and reduce call abandonment. In Vapi, idle messages are configured using **hooks** that trigger on specific events.

## How It Works

Idle messages use the `customer.speech.timeout` hook event, which triggers when the user hasn't spoken for a specified duration. The assistant can then perform actions like saying a message to prompt the user.

**Important Notes:**
- Idle messages are automatically disabled during tool calls and warm transfers
- Account for 2-3 seconds of audio processing time when choosing timeout values
- Set lower temperature values (0.4 or lower) to prevent randomness in idle messages

## Configuration Structure

Add hooks configuration to your `assistant.yaml` file:

```yaml
# assistant.yaml

name: "Your Assistant"
voice:
  provider: minimax
  voiceId: socialmedia_female_1_v1

model:
  provider: openai
  model: gpt-4o-mini
  temperature: 0.4  # Lower temperature for consistent idle messages

# Hooks configuration for idle messages
# IMPORTANT: Quote the "on" key to prevent YAML from interpreting it as a boolean
hooks:
  - "on": customer.speech.timeout
    options:
      timeoutSeconds: 7        # Trigger after 30 seconds of silence
      triggerMaxCount: 3        # Maximum 3 times per call
      triggerResetMode: onUserSpeech  # Reset counter when user speaks
    do:
      - type: say
        prompt: "Generate a friendly message in french to check if the user is still there. Consider what we were discussing and offer relevant help. {{transcript}}"
```

**Important YAML Note:** The `on` key must be quoted (`"on":`) because `on` is a reserved word in YAML (boolean value). Without quotes, the YAML parser will interpret it incorrectly.

## Configuration Options

### Hook Event
- **on**: `customer.speech.timeout` - Triggered when user hasn't spoken

### Hook Options
- **timeoutSeconds**: Duration of silence before triggering (1-1000 seconds, default ~7.5s)
- **triggerMaxCount**: Maximum number of times the hook can trigger in a call
- **triggerResetMode**: When to reset the trigger count
  - `onUserSpeech`: Reset when user speaks (recommended)

### Actions
- **type**: `say` - Make the assistant speak
- **exact**: The exact message to say (static, always the same)
- **prompt**: A prompt for the LLM to generate a contextual message based on conversation history

**Note**: Use either `exact` OR `prompt`, not both. Choose `exact` for consistent messages, or `prompt` for context-aware responses.

## Examples

### Simple Idle Message
```yaml
hooks:
  - "on": customer.speech.timeout
    options:
      timeoutSeconds: 20
      triggerMaxCount: 2
      triggerResetMode: onUserSpeech
    do:
      - type: say
        exact: "Hello? Are you still there?"
```

### Multiple Idle Messages
You can configure multiple hooks for different scenarios:

```yaml
hooks:
  # First idle message after 15 seconds
  - "on": customer.speech.timeout
    options:
      timeoutSeconds: 15
      triggerMaxCount: 1
      triggerResetMode: onUserSpeech
    do:
      - type: say
        exact: "I'm here whenever you're ready to continue."

  # More urgent message after 45 seconds
  - "on": customer.speech.timeout
    options:
      timeoutSeconds: 45
      triggerMaxCount: 2
      triggerResetMode: onUserSpeech
    do:
      - type: say
        exact: "Are you still there? Let me know if you need help."
```

### Helpful Idle Message
```yaml
hooks:
  - "on": customer.speech.timeout
    options:
      timeoutSeconds: 25
      triggerMaxCount: 3
      triggerResetMode: onUserSpeech
    do:
      - type: say
        exact: "Take your time. I'm here if you have any questions."
```

### Model-Generated Contextual Messages

Instead of using `exact`, you can use `prompt` to have the LLM generate contextual messages based on the conversation:

```yaml
hooks:
  - "on": customer.speech.timeout
    options:
      timeoutSeconds: 30
      triggerMaxCount: 2
      triggerResetMode: onUserSpeech
    do:
      - type: say
        prompt: "Generate a friendly message to check if the user is still there. Consider what we were discussing and offer relevant help."
```

**Benefits of model-generated messages:**
- Context-aware responses that reference the current conversation
- More natural and personalized interactions
- Can adapt based on where the user left off

**When to use `exact` vs `prompt`:**
- **Use `exact`**: When you want consistent, predictable messages (e.g., compliance, branding)
- **Use `prompt`**: When you want natural, context-aware messages that feel more conversational

### Combined Example with Multiple Hooks

You can combine different approaches with staggered timing:

```yaml
hooks:
  # First check - simple exact message
  - "on": customer.speech.timeout
    options:
      timeoutSeconds: 20
      triggerMaxCount: 1
      triggerResetMode: onUserSpeech
    do:
      - type: say
        exact: "I'm here whenever you're ready."

  # Second check - contextual message
  - "on": customer.speech.timeout
    options:
      timeoutSeconds: 45
      triggerMaxCount: 2
      triggerResetMode: onUserSpeech
    do:
      - type: say
        prompt: "Generate a helpful message checking on the user. Reference what we were discussing and offer to clarify or help with next steps."
```

## Best Practices

1. **Keep messages concise**: Users may be distracted, so shorter messages work better
2. **Use encouraging tone**: Avoid demanding or impatient language
3. **Offer specific help**: Guide users toward productive next steps
4. **Set appropriate timeouts**: Consider your use case:
   - Customer support: 20-30 seconds
   - Form filling: 30-45 seconds
   - Complex decisions: 45-60 seconds
5. **Limit trigger count**: Avoid annoying users with too many prompts (2-3 max)
6. **Lower temperature**: Set model temperature to 0.4 or lower for consistent responses

## Deploying

After configuring hooks in your `assistant.yaml`, deploy your assistant:

```bash
# Create new assistant
vapi-manager assistant create your-assistant-name

# Update existing assistant
vapi-manager assistant update your-assistant-name
```

## Testing

Test idle messages by:
1. Starting a call with your assistant
2. Staying silent for the configured timeout duration
3. Verifying the idle message is spoken
4. Speaking to verify the trigger count resets (if `triggerResetMode: onUserSpeech`)

## Troubleshooting

**Idle message not triggering:**
- Check that `timeoutSeconds` accounts for processing delay (add 2-3 seconds)
- Verify the assistant is not in a tool call or transfer
- Ensure hooks are properly deployed with your assistant

**Message varies from configuration:**
- Lower the model temperature to 0.4 or below
- Ensure you're using the `exact` field in the action

**Message triggers too frequently:**
- Increase `timeoutSeconds`
- Lower `triggerMaxCount`

## Related Documentation

- [Vapi Idle Messages Official Docs](https://docs.vapi.ai/assistants/idle-messages)
- [Vapi Assistant Hooks API Reference](https://docs.vapi.ai/api-reference/assistants/create)
