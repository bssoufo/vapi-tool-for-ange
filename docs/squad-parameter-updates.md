# Squad-Wide Parameter Updates

The VAPI Manager tool provides a powerful command to update parameters across all assistants in a squad simultaneously. This feature is essential for maintaining consistency across your squad members.

## Command Overview

```bash
vapi-manager squad set-params <squad_name> [options]
```

## Available Parameters

### Voice Configuration
- `--voice-provider` - Voice provider (vapi, azure, cartesia, deepgram, elevenlabs, etc.)
- `--voice-id` - Voice ID for the selected provider

### Model Configuration
- `--model-provider` - Model provider (openai, anthropic, azure, google, etc.)
- `--model` - Model name (e.g., gpt-4o-mini, claude-3-haiku)
- `--temperature` - Model temperature (0.0-2.0)
- `--max-tokens` - Maximum tokens for model responses

### Transcriber Configuration
- `--transcriber-provider` - Transcriber provider (deepgram, assembly, azure, google, groq)
- `--transcriber-model` - Transcriber model (e.g., nova-2, whisper-large-v3)
- `--transcriber-language` - Transcriber language (e.g., en, es, fr)

### General Configuration
- `--first-message-mode` - First message mode
- `--server-timeout` - Server timeout in seconds
- `--enable-recording` - Enable call recording (true/false)
- `--enable-transcription` - Enable call transcription (true/false)

### Operational Flags
- `--env` - Target environment (development, staging, production)
- `--dry-run` - Preview changes without applying them
- `--update-vapi` - Also update assistants in VAPI after local changes

## Usage Examples

### 1. Update Voice Settings
Change voice provider and voice ID for all assistants in a squad:

```bash
vapi-manager squad set-params my_squad --voice-provider vapi --voice-id Jennifer
```

### 2. Update Model Configuration
Change the AI model and temperature:

```bash
vapi-manager squad set-params my_squad --model-provider openai --model gpt-4o-mini --temperature 0.7
```

### 3. Update Multiple Parameters
Update voice, model, and transcriber settings at once:

```bash
vapi-manager squad set-params my_squad \
  --voice-provider elevenlabs \
  --voice-id Rachel \
  --model gpt-4 \
  --temperature 0.5 \
  --transcriber-model nova-2
```

### 4. Dry Run Mode
Preview what will be changed without making actual updates:

```bash
vapi-manager squad set-params my_squad --model gpt-3.5-turbo --dry-run
```

### 5. Update and Deploy to VAPI
Update local configurations and immediately deploy to VAPI:

```bash
vapi-manager squad set-params my_squad \
  --voice-id Jennifer \
  --update-vapi \
  --env production
```

## How It Works

1. **Load Squad Configuration**: The command reads the squad's `members.yaml` file to identify all assistants
2. **Apply Updates**: Updates are applied to each assistant's `assistant.yaml` file
3. **Environment-Specific Updates**: If environment-specific configurations exist, they are updated as well
4. **VAPI Deployment**: If `--update-vapi` is specified, changes are deployed to VAPI

## Parameter Merging Strategy

The updater uses an intelligent merging strategy:
- **Nested objects** (voice, model, transcriber): Existing values are preserved, only specified fields are updated
- **Features**: Merged with existing feature settings
- **Server settings**: Merged with existing server configuration
- **Top-level settings**: Replaced entirely when specified

## Best Practices

1. **Always Use Dry Run First**: Test your changes with `--dry-run` before applying
2. **Batch Updates**: Update multiple parameters in a single command for efficiency
3. **Environment Awareness**: Specify the correct environment with `--env`
4. **Validate After Update**: Check assistant configurations after updates

## Example Workflow

1. **Check Current Settings**:
```bash
vapi-manager assistant get triage_assistant_pa
```

2. **Preview Changes**:
```bash
vapi-manager squad set-params test_squad --model gpt-4 --dry-run
```

3. **Apply Updates**:
```bash
vapi-manager squad set-params test_squad --model gpt-4
```

4. **Deploy to VAPI**:
```bash
vapi-manager squad set-params test_squad --model gpt-4 --update-vapi
```

## Error Handling

The command includes comprehensive error handling:
- Validates parameter values before applying
- Checks for assistant existence
- Preserves YAML formatting and structure
- Reports individual assistant update status

## Architecture Recommendation

### Single Flexible Command vs Multiple Commands

The implementation uses a **single flexible command** with parameter flags. This approach offers several advantages:

1. **Efficiency**: Update multiple settings in one operation
2. **Atomicity**: All updates succeed or fail together
3. **Simplicity**: One command to remember
4. **Flexibility**: Mix and match parameters as needed

Alternative approaches considered:
- Individual commands per setting (e.g., `set-voice`, `set-model`)
- Config file based updates
- Interactive mode

The chosen approach balances power and simplicity, making it easy to script and integrate into CI/CD pipelines while remaining user-friendly for manual operations.