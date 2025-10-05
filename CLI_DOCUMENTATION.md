# VAPI Manager CLI Documentation

**Version**: 1.0.0
**Purpose**: Comprehensive CLI tool for managing VAPI assistants and squads with support for templates, deployments, and team collaboration

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Command Overview](#command-overview)
- [Assistant Commands](#assistant-commands)
- [Squad Commands](#squad-commands)
- [Agent Commands](#agent-commands)
- [File Commands](#file-commands)
- [Tool Commands](#tool-commands)
- [Environment Variables](#environment-variables)
- [Common Patterns](#common-patterns)

---

## Installation

### Via pip (Recommended)
```bash
pip install vapi-manager
```

### Via pipx (Isolated Environment)
```bash
pipx install vapi-manager
```

### Development Installation
```bash
git clone https://github.com/vapi-ai/vapi-manager
cd vapi-manager
pip install -e .
```

---

## Configuration

### Environment Variables

**Required:**
```bash
export VAPI_API_KEY="your-api-key-here"
```

**Optional:**
```bash
export VAPI_BASE_URL="https://api.vapi.ai"  # Default
export VAPI_MANAGER_CONFIG_DIR="~/.vapi-manager"  # Config directory
export VAPI_MANAGER_LOG_LEVEL="INFO"  # Log level
```

---

## Command Overview

The CLI provides three command entry points (all equivalent):
- `vapi-manager`
- `vapi`
- `vapictl`

### Command Groups

1. **assistant** (alias: `ast`) - Manage individual assistants
2. **squad** - Manage squads of assistants
3. **agent** - Agent management operations
4. **file** - File-based assistant operations
5. **tool** - Shared tool management

### Common Options Across Commands

- `--env` - Environment selection: `development`, `staging`, `production`
- `--dir` - Directory path for assistants or squads
- `--force` - Force operation without confirmation
- `--dry-run` - Preview changes without applying them

---

## Assistant Commands

### `assistant list`

List all assistants from VAPI.

**Usage:**
```bash
vapi-manager assistant list [OPTIONS]
```

**Options:**
- `--limit INTEGER` - Limit number of results

**Example:**
```bash
vapi-manager assistant list --limit 10
```

---

### `assistant get`

Get assistant details by ID.

**Usage:**
```bash
vapi-manager assistant get <id>
```

**Parameters:**
- `id` (required) - Assistant ID from VAPI

**Example:**
```bash
vapi-manager assistant get abc123-def456-ghi789
```

---

### `assistant validate`

Validate assistant configuration files.

**Usage:**
```bash
vapi-manager assistant validate <name> [OPTIONS]
```

**Parameters:**
- `name` (required) - Assistant name (directory name)

**Options:**
- `--dir TEXT` - Directory containing assistants (default: `assistants`)

**Example:**
```bash
vapi-manager assistant validate my_assistant
vapi-manager assistant validate my_assistant --dir custom_assistants
```

---

### `assistant init`

Initialize a new assistant from a template.

**Usage:**
```bash
vapi-manager assistant init <name> [OPTIONS]
```

**Parameters:**
- `name` (required) - Assistant name (directory name to create)

**Options:**
- `--template TEXT` - Template to use (default: `vicky_dental_clinic`)
- `--force` - Overwrite if assistant already exists

**Example:**
```bash
vapi-manager assistant init customer_service --template default
vapi-manager assistant init receptionist --template vicky_dental_clinic --force
```

---

### `assistant create`

Create assistant in VAPI and track deployment ID.

**Usage:**
```bash
vapi-manager assistant create <name> [OPTIONS]
```

**Parameters:**
- `name` (required) - Assistant name (directory name)

**Options:**
- `--env [development|staging|production]` - Environment to deploy to (default: `production`)
- `--force` - Force recreation if already deployed
- `--dir TEXT` - Directory containing assistants (default: `assistants`)

**Example:**
```bash
vapi-manager assistant create my_assistant --env development
vapi-manager assistant create my_assistant --env production --force
```

---

### `assistant delete`

Delete an assistant from VAPI.

**Usage:**
```bash
vapi-manager assistant delete <name> [OPTIONS]
```

**Parameters:**
- `name` (required) - Assistant name to delete

**Options:**
- `--env [development|staging|production]` - Environment to delete from (default: `development`)
- `--force` - Force deletion without confirmation
- `--dir TEXT` - Directory containing assistants (default: `assistants`)

**Example:**
```bash
vapi-manager assistant delete old_assistant --env development
vapi-manager assistant delete old_assistant --env production --force
```

---

### `assistant update`

Update an existing assistant with change detection.

**Usage:**
```bash
vapi-manager assistant update <name> [OPTIONS]
```

**Parameters:**
- `name` (required) - Assistant name (directory name)

**Options:**
- `--env [development|staging|production]` - Environment to update (default: `development`)
- `--scope [configuration|prompts|tools|analysis|full]` - Update scope (default: `full`)
- `--dry-run` - Preview changes without applying them
- `--no-backup` - Skip backup creation before update
- `--force` - Force update even if no changes detected
- `--dir TEXT` - Directory containing assistants (default: `assistants`)

**Update Scopes:**
- `configuration` - Only update assistant configuration (voice, model, transcriber, etc.)
- `prompts` - Only update system prompts and messages
- `tools` - Only update tools and functions
- `analysis` - Only update analysis plan
- `full` - Update all components (default)

**Example:**
```bash
vapi-manager assistant update my_assistant --env development
vapi-manager assistant update my_assistant --env production --scope prompts --dry-run
vapi-manager assistant update my_assistant --force --no-backup
```

---

### `assistant backup`

Create a backup of one or more assistants.

**Usage:**
```bash
vapi-manager assistant backup [ASSISTANTS...] [OPTIONS]
```

**Parameters:**
- `assistants` (optional) - Space-separated assistant names to backup (empty = all assistants)

**Options:**
- `--env [development|staging|production]` - Environment to backup from (default: `development`)
- `--type [full|vapi_only|config_only]` - Backup type (default: `full`)
- `--description TEXT` - Backup description
- `--tags TEXT` - Comma-separated tags for the backup
- `--dir TEXT` - Directory containing assistants (default: `assistants`)

**Backup Types:**
- `full` - Backup both local configuration and VAPI data
- `vapi_only` - Backup only VAPI deployment data
- `config_only` - Backup only local configuration files

**Example:**
```bash
# Backup all assistants
vapi-manager assistant backup --env production --description "Pre-release backup"

# Backup specific assistants
vapi-manager assistant backup assistant1 assistant2 --env development

# Backup with tags
vapi-manager assistant backup --tags "release-1.0,production" --type full
```

---

### `assistant restore`

Restore assistants from a backup file.

**Usage:**
```bash
vapi-manager assistant restore <backup_path> [OPTIONS]
```

**Parameters:**
- `backup_path` (required) - Path to backup file (.zip)

**Options:**
- `--env [development|staging|production]` - Target environment for restore (default: `development`)
- `--overwrite` - Overwrite existing assistants
- `--config-only` - Restore only local configuration
- `--vapi-only` - Restore only VAPI data
- `--dry-run` - Preview restore without applying changes
- `--dir TEXT` - Directory for assistants (default: `assistants`)

**Example:**
```bash
vapi-manager assistant restore backup_20240101_120000.zip --env development
vapi-manager assistant restore backup.zip --env staging --overwrite
vapi-manager assistant restore backup.zip --config-only --dry-run
```

---

### `assistant add-tool`

Add a shared tool to an assistant.

**Usage:**
```bash
vapi-manager assistant add-tool <name> --tool <tool_path> [OPTIONS]
```

**Parameters:**
- `name` (required) - Assistant name (directory name)

**Options:**
- `--tool TEXT` (required) - Path to shared tool (e.g., `shared/tools/bookAppointment_clinic.yaml`)
- `--dir TEXT` - Directory containing assistants (default: `assistants`)

**Example:**
```bash
vapi-manager assistant add-tool my_assistant --tool shared/tools/bookAppointment.yaml
vapi-manager assistant add-tool receptionist --tool shared/tools/transfer.yaml
```

---

## Squad Commands

### `squad list`

List all squads from VAPI.

**Usage:**
```bash
vapi-manager squad list [OPTIONS]
```

**Options:**
- `--limit INTEGER` - Limit number of results

**Example:**
```bash
vapi-manager squad list --limit 5
```

---

### `squad get`

Get squad details by ID.

**Usage:**
```bash
vapi-manager squad get <id>
```

**Parameters:**
- `id` (required) - Squad ID from VAPI

**Example:**
```bash
vapi-manager squad get squad-abc123-def456
```

---

### `squad init`

Initialize a new squad from a template.

**Usage:**
```bash
vapi-manager squad init <name> [OPTIONS]
```

**Parameters:**
- `name` (required) - Squad name (directory name to create)

**Options:**
- `--template TEXT` - Template to use (default: `dental_clinic_squad`)
- `--assistants TEXT` - Comma-separated list of assistant names
- `--description TEXT` - Squad description
- `--force` - Overwrite if squad already exists
- `--dir TEXT` - Directory for squads (default: `squads`)

**Example:**
```bash
vapi-manager squad init customer_service --template dental_clinic_squad
vapi-manager squad init my_squad --assistants triage,billing,support --force
```

---

### `squad create`

Create squad in VAPI and track deployment ID.

**Usage:**
```bash
vapi-manager squad create <name> [OPTIONS]
```

**Parameters:**
- `name` (required) - Squad name (directory name)

**Options:**
- `--env [development|staging|production]` - Environment to deploy to (default: `development`)
- `--force` - Force recreation if already deployed
- `--auto-deploy-assistants` - Automatically deploy missing assistants
- `--dir TEXT` - Directory containing squads (default: `squads`)
- `--assistants-dir TEXT` - Directory containing assistants (default: `assistants`)

**Example:**
```bash
vapi-manager squad create my_squad --env development
vapi-manager squad create my_squad --env production --auto-deploy-assistants
```

---

### `squad file-list`

List file-based squads in the local directory.

**Usage:**
```bash
vapi-manager squad file-list [OPTIONS]
```

**Options:**
- `--dir TEXT` - Directory containing squads (default: `squads`)

**Example:**
```bash
vapi-manager squad file-list
vapi-manager squad file-list --dir custom_squads
```

---

### `squad templates`

List available squad templates.

**Usage:**
```bash
vapi-manager squad templates
```

**Example:**
```bash
vapi-manager squad templates
```

---

### `squad template-info`

Show detailed information about a squad template.

**Usage:**
```bash
vapi-manager squad template-info <template>
```

**Parameters:**
- `template` (required) - Template name

**Example:**
```bash
vapi-manager squad template-info dental_clinic_squad
```

---

### `squad create-template`

Create a new squad template with manifest.

**Usage:**
```bash
vapi-manager squad create-template <template_name> --description <desc> [OPTIONS]
```

**Parameters:**
- `template_name` (required) - Name of the template to create

**Options:**
- `--description TEXT` (required) - Template description
- `--assistant TEXT` (repeatable) - Assistant specification: `name:template:role`
- `--tool TEXT` (repeatable) - Tool specification: `name:template:var1=val1,var2=val2`
- `--environment TEXT` (repeatable) - Environment to include
- `--deployment-strategy [rolling|blue_green|all_at_once]` - Deployment strategy (default: `rolling`)
- `--force` - Overwrite existing template
- `--preview` - Preview template without creating
- `--output-dir TEXT` - Output directory for template (default: `templates/squads`)
- `--no-auto-create-assistants` - Disable automatic creation of missing assistant templates
- `--assistants-dir TEXT` - Directory containing assistant templates (default: `templates/assistants`)
- `--validate-strict` - Fail if any assistant validation errors occur

**Example:**
```bash
vapi-manager squad create-template my_template \
  --description "Customer service squad" \
  --assistant "triage:default:receptionist" \
  --assistant "support:default:specialist" \
  --tool "booking:basic_webhook:url=https://api.example.com/book" \
  --environment development \
  --environment production

vapi-manager squad create-template my_template --description "Test" --preview
```

---

### `squad update`

Update an existing squad with change detection.

**Usage:**
```bash
vapi-manager squad update <name> [OPTIONS]
```

**Parameters:**
- `name` (required) - Squad name (directory name)

**Options:**
- `--env [development|staging|production]` - Environment to update (default: `development`)
- `--dry-run` - Preview changes without applying them
- `--force` - Force update even if no changes detected
- `--update-assistants / --no-update-assistants` - Also update all assistants in the squad (default: `True`)
- `--dir TEXT` - Directory containing squads (default: `squads`)

**Example:**
```bash
vapi-manager squad update my_squad --env development
vapi-manager squad update my_squad --env production --dry-run
vapi-manager squad update my_squad --no-update-assistants --force
```

---

### `squad status`

Show squad deployment status across environments.

**Usage:**
```bash
vapi-manager squad status [name] [OPTIONS]
```

**Parameters:**
- `name` (optional) - Squad name (shows all squads if omitted)

**Options:**
- `--dir TEXT` - Directory containing squads (default: `squads`)

**Example:**
```bash
vapi-manager squad status
vapi-manager squad status my_squad
```

---

### `squad delete`

Delete a squad from VAPI.

**Usage:**
```bash
vapi-manager squad delete <name> [OPTIONS]
```

**Parameters:**
- `name` (required) - Squad name to delete

**Options:**
- `--env [development|staging|production]` - Environment to delete from (default: `development`)
- `--force` - Force deletion without confirmation
- `--delete-assistants` - Also delete all assistants that are members of this squad
- `--dir TEXT` - Directory containing squads (default: `squads`)

**Example:**
```bash
vapi-manager squad delete old_squad --env development
vapi-manager squad delete old_squad --env production --force --delete-assistants
```

---

### `squad add-member`

Add a member assistant to a squad and sync with VAPI.

**Usage:**
```bash
vapi-manager squad add-member <squad_name> --assistant-name <name> [OPTIONS]
```

**Parameters:**
- `squad_name` (required) - Squad name

**Options:**
- `--assistant-name TEXT` (required) - Assistant name to add
- `--env [development|staging|production]` - Environment to sync with (default: `development`)
- `--dir TEXT` - Directory containing squads (default: `squads`)
- `--assistants-dir TEXT` - Directory containing assistants (default: `assistants`)

**Example:**
```bash
vapi-manager squad add-member my_squad --assistant-name new_assistant --env development
```

---

### `squad backup`

Create a backup of a squad with all related components.

**Usage:**
```bash
vapi-manager squad backup <squad_name> [OPTIONS]
```

**Parameters:**
- `squad_name` (required) - Squad name to backup

**Options:**
- `--env [development|staging|production]` - Environment to backup from (default: `development`)
- `--type [complete|squad_only|with_assistants]` - Squad backup type (default: `complete`)
- `--description TEXT` - Backup description
- `--tags TEXT` - Comma-separated tags for the backup
- `--dir TEXT` - Directory containing squads (default: `squads`)

**Backup Types:**
- `complete` - Backup squad, all assistants, and VAPI data
- `squad_only` - Backup only squad configuration
- `with_assistants` - Backup squad and assistants configurations (no VAPI data)

**Example:**
```bash
vapi-manager squad backup my_squad --env production --type complete
vapi-manager squad backup my_squad --description "Before major update" --tags "v1.0,production"
```

---

### `squad restore`

Restore a squad from backup with all related components.

**Usage:**
```bash
vapi-manager squad restore <backup_path> [OPTIONS]
```

**Parameters:**
- `backup_path` (required) - Path to squad backup file (.zip)

**Options:**
- `--env [development|staging|production]` - Target environment for restore (default: `development`)
- `--overwrite` - Overwrite existing squad and assistants
- `--config-only` - Restore only local configuration
- `--vapi-only` - Restore only VAPI data
- `--skip-assistants` - Skip restoring assistants
- `--assistant-prefix TEXT` - Prefix for restored assistant names (default: `""`)
- `--squad-name TEXT` - Override squad name for restore
- `--dry-run` - Preview restore without applying changes
- `--dir TEXT` - Directory for squads (default: `squads`)

**Example:**
```bash
vapi-manager squad restore squad_backup_20240101.zip --env development
vapi-manager squad restore backup.zip --env staging --overwrite
vapi-manager squad restore backup.zip --squad-name new_squad --assistant-prefix "test_"
vapi-manager squad restore backup.zip --skip-assistants --dry-run
```

---

### `squad backups`

List available squad backups.

**Usage:**
```bash
vapi-manager squad backups [OPTIONS]
```

**Options:**
- `--dir TEXT` - Directory containing squads (default: `squads`)

**Example:**
```bash
vapi-manager squad backups
```

---

### `squad backup-info`

Show detailed squad backup information.

**Usage:**
```bash
vapi-manager squad backup-info <backup_id> [OPTIONS]
```

**Parameters:**
- `backup_id` (required) - Squad backup ID to show details for

**Options:**
- `--dir TEXT` - Directory containing squads (default: `squads`)

**Example:**
```bash
vapi-manager squad backup-info backup_20240101_120000
```

---

### `squad backup-delete`

Delete a squad backup.

**Usage:**
```bash
vapi-manager squad backup-delete <backup_id> [OPTIONS]
```

**Parameters:**
- `backup_id` (required) - Squad backup ID to delete

**Options:**
- `--dir TEXT` - Directory containing squads (default: `squads`)

**Example:**
```bash
vapi-manager squad backup-delete backup_20240101_120000
```

---

### `squad set-params`

Update parameters for all assistants in a squad.

**Usage:**
```bash
vapi-manager squad set-params <squad_name> [OPTIONS]
```

**Parameters:**
- `squad_name` (required) - Name of the squad

**Options:**

**Environment:**
- `--env [development|staging|production]` - Environment to update (default: `development`)

**Voice Parameters:**
- `--voice-provider [vapi|azure|cartesia|deepgram|elevenlabs|lmnt|neets|openai|playht|rime]` - Voice provider
- `--voice-id TEXT` - Voice ID for the selected provider
- `--voice-model TEXT` - Voice model (optional, provider-specific)

**Model Parameters:**
- `--model-provider [openai|anthropic|azure|google|together|anyscale|openrouter|perplexity|deepinfra|groq]` - Model provider
- `--model TEXT` - Model name (e.g., `gpt-4o-mini`, `claude-3-haiku`)
- `--temperature FLOAT` - Model temperature (0.0-2.0)
- `--max-tokens INTEGER` - Maximum tokens for model responses

**Transcriber Parameters:**
- `--transcriber-provider [deepgram|assembly|azure|google|groq]` - Transcriber provider
- `--transcriber-model TEXT` - Transcriber model (e.g., `nova-2`, `whisper-large-v3`)
- `--transcriber-language TEXT` - Transcriber language (e.g., `en`, `es`, `fr`)

**General Parameters:**
- `--first-message-mode [assistant-speaks-first|assistant-waits-for-user|assistant-speaks-first-with-model-generated-message]` - First message mode
- `--server-timeout INTEGER` - Server timeout in seconds
- `--enable-recording BOOLEAN` - Enable call recording
- `--enable-transcription BOOLEAN` - Enable call transcription

**Execution Options:**
- `--dry-run` - Show what would be updated without making changes
- `--update-vapi` - Also update assistants in VAPI after local changes

**Example:**
```bash
# Update voice for all assistants in squad
vapi-manager squad set-params my_squad --voice-provider elevenlabs --voice-id Rachel

# Update model settings
vapi-manager squad set-params my_squad --model gpt-4 --temperature 0.7 --max-tokens 2000

# Update transcriber
vapi-manager squad set-params my_squad --transcriber-provider deepgram --transcriber-model nova-2

# Dry run to preview changes
vapi-manager squad set-params my_squad --model gpt-4 --dry-run

# Update and sync to VAPI
vapi-manager squad set-params my_squad --voice-id Jennifer --update-vapi --env production
```

---

### `squad bootstrap`

Bootstrap a complete squad system from template.

**Usage:**
```bash
vapi-manager squad bootstrap <squad_name> [OPTIONS]
```

**Parameters:**
- `squad_name` (required) - Name of the squad to create

**Options:**
- `--template TEXT` - Squad template to use (default: `dental_clinic_squad`)
- `--deploy` - Deploy after creation
- `--env [development|staging|production]` - Target environment for deployment (default: `development`)
- `--dry-run` - Preview without executing
- `--force` - Overwrite existing components
- `--validate-only` - Only validate template

**Example:**
```bash
vapi-manager squad bootstrap my_squad --template dental_clinic_squad
vapi-manager squad bootstrap my_squad --template custom_template --deploy --env production
vapi-manager squad bootstrap my_squad --dry-run --validate-only
```

---

### `squad bootstrap-templates`

List bootstrap-ready squad templates.

**Usage:**
```bash
vapi-manager squad bootstrap-templates
```

**Example:**
```bash
vapi-manager squad bootstrap-templates
```

---

### `squad bootstrap-rollback`

Rollback a previously bootstrapped squad.

**Usage:**
```bash
vapi-manager squad bootstrap-rollback <squad_name> [OPTIONS]
```

**Parameters:**
- `squad_name` (required) - Name of the squad to rollback

**Options:**
- `--dir TEXT` - Directory containing squads (default: `squads`)

**Example:**
```bash
vapi-manager squad bootstrap-rollback my_squad
```

---

### `squad bootstrap-update`

Update an existing squad with new configuration.

**Usage:**
```bash
vapi-manager squad bootstrap-update <squad_name> --template <template> [OPTIONS]
```

**Parameters:**
- `squad_name` (required) - Name of the squad to update

**Options:**
- `--template TEXT` (required) - Squad template to use for update
- `--env [development|staging|production]` - Target environment (default: `development`)

**Example:**
```bash
vapi-manager squad bootstrap-update my_squad --template updated_template --env development
```

---

### `squad bootstrap-pipeline`

Deploy squad through multi-environment pipeline.

**Usage:**
```bash
vapi-manager squad bootstrap-pipeline <squad_name> [OPTIONS]
```

**Parameters:**
- `squad_name` (required) - Name of the squad to deploy

**Options:**
- `--environments TEXT` - Comma-separated environments in deployment order (default: `development,staging,production`)
- `--strategy [rolling|blue_green|all_at_once]` - Deployment strategy (default: `rolling`)
- `--approval` - Require manual approval between stages

**Deployment Strategies:**
- `rolling` - Deploy to one environment at a time, validating before moving to next
- `blue_green` - Deploy to parallel environment, then switch over
- `all_at_once` - Deploy to all environments simultaneously

**Example:**
```bash
vapi-manager squad bootstrap-pipeline my_squad --environments development,staging,production
vapi-manager squad bootstrap-pipeline my_squad --strategy blue_green --approval
```

---

### `squad health-check`

Run health checks on deployed squad.

**Usage:**
```bash
vapi-manager squad health-check <squad_name> [OPTIONS]
```

**Parameters:**
- `squad_name` (required) - Name of the squad to check

**Options:**
- `--env [development|staging|production]` - Environment to check (default: `development`)

**Example:**
```bash
vapi-manager squad health-check my_squad --env production
```

---

### `squad deployment-status`

Get deployment status across all environments.

**Usage:**
```bash
vapi-manager squad deployment-status <squad_name>
```

**Parameters:**
- `squad_name` (required) - Name of the squad to check

**Example:**
```bash
vapi-manager squad deployment-status my_squad
```

---

### `squad promote`

Promote squad from one environment to another.

**Usage:**
```bash
vapi-manager squad promote <squad_name> --from-env <env> --to-env <env> [OPTIONS]
```

**Parameters:**
- `squad_name` (required) - Name of the squad to promote

**Options:**
- `--from-env [development|staging|production]` (required) - Source environment
- `--to-env [development|staging|production]` (required) - Target environment
- `--skip-tests` - Skip running tests before promotion
- `--auto-approve` - Skip manual approval

**Example:**
```bash
vapi-manager squad promote my_squad --from-env staging --to-env production
vapi-manager squad promote my_squad --from-env development --to-env staging --skip-tests --auto-approve
```

---

## Agent Commands

### `agent list`

List all agents.

**Usage:**
```bash
vapi-manager agent list [OPTIONS]
```

**Options:**
- `--limit INTEGER` - Limit number of results

**Example:**
```bash
vapi-manager agent list --limit 20
```

---

## File Commands

The `file` command group provides file-based assistant operations similar to `assistant` commands.

### `file list`

List file-based assistants in the local directory.

**Usage:**
```bash
vapi-manager file list [OPTIONS]
```

**Options:**
- `--dir TEXT` - Directory containing assistants (default: `assistants`)

**Example:**
```bash
vapi-manager file list
vapi-manager file list --dir custom_assistants
```

---

### `file validate`

Validate assistant configuration files.

**Usage:**
```bash
vapi-manager file validate <name> [OPTIONS]
```

**Parameters:**
- `name` (required) - Assistant name (directory name)

**Options:**
- `--dir TEXT` - Directory containing assistants (default: `assistants`)

**Example:**
```bash
vapi-manager file validate my_assistant
```

---

### `file deploy`

Deploy assistant to VAPI.

**Usage:**
```bash
vapi-manager file deploy <name> [OPTIONS]
```

**Parameters:**
- `name` (required) - Assistant name (directory name)

**Options:**
- `--env TEXT` - Environment (default: `default`)
- `--dir TEXT` - Directory containing assistants (default: `assistants`)

**Example:**
```bash
vapi-manager file deploy my_assistant --env production
```

---

### `file init`

Initialize new assistant from template.

**Usage:**
```bash
vapi-manager file init <name> [OPTIONS]
```

**Parameters:**
- `name` (required) - Assistant name (directory name to create)

**Options:**
- `--template TEXT` - Template to use (default: `vicky_dental_clinic`)
- `--force` - Overwrite if assistant exists

**Example:**
```bash
vapi-manager file init new_assistant --template default
```

---

### `file templates`

List available assistant templates.

**Usage:**
```bash
vapi-manager file templates
```

**Example:**
```bash
vapi-manager file templates
```

---

### `file template-info`

Show template information.

**Usage:**
```bash
vapi-manager file template-info <template>
```

**Parameters:**
- `template` (required) - Template name

**Example:**
```bash
vapi-manager file template-info vicky_dental_clinic
```

---

### `file create`

Create assistant in VAPI and track ID.

**Usage:**
```bash
vapi-manager file create <name> [OPTIONS]
```

**Parameters:**
- `name` (required) - Assistant name (directory name)

**Options:**
- `--env [development|staging|production]` - Environment to deploy to (default: `production`)
- `--force` - Force recreation if already deployed
- `--dir TEXT` - Directory containing assistants (default: `assistants`)

**Example:**
```bash
vapi-manager file create my_assistant --env development
```

---

### `file status`

Show deployment status of assistants.

**Usage:**
```bash
vapi-manager file status [name] [OPTIONS]
```

**Parameters:**
- `name` (optional) - Assistant name (shows all if omitted)

**Options:**
- `--dir TEXT` - Directory containing assistants (default: `assistants`)

**Example:**
```bash
vapi-manager file status
vapi-manager file status my_assistant
```

---

### `file update`

Update an existing assistant with change detection.

**Usage:**
```bash
vapi-manager file update <name> [OPTIONS]
```

**Parameters:**
- `name` (required) - Assistant name (directory name)

**Options:**
- `--env [development|staging|production]` - Environment to update (default: `development`)
- `--scope [configuration|prompts|tools|analysis|full]` - Update scope (default: `full`)
- `--dry-run` - Preview changes without applying them
- `--no-backup` - Skip backup creation
- `--force` - Force update even if no changes detected
- `--dir TEXT` - Directory containing assistants (default: `assistants`)

**Example:**
```bash
vapi-manager file update my_assistant --env development --scope prompts
```

---

### `file backup`

Create a backup of assistants.

**Usage:**
```bash
vapi-manager file backup [ASSISTANTS...] [OPTIONS]
```

**Parameters:**
- `assistants` (optional) - Space-separated assistant names (empty = all)

**Options:**
- `--env [development|staging|production]` - Environment to backup from (default: `development`)
- `--type [full|vapi_only|config_only]` - Backup type (default: `full`)
- `--description TEXT` - Backup description
- `--tags TEXT` - Comma-separated tags for the backup
- `--dir TEXT` - Directory containing assistants (default: `assistants`)

**Example:**
```bash
vapi-manager file backup --env production --type full
vapi-manager file backup assistant1 assistant2 --description "Before update"
```

---

### `file restore`

Restore assistants from a backup.

**Usage:**
```bash
vapi-manager file restore <backup_path> [OPTIONS]
```

**Parameters:**
- `backup_path` (required) - Path to backup file (.zip)

**Options:**
- `--env [development|staging|production]` - Target environment for restore (default: `development`)
- `--overwrite` - Overwrite existing assistants
- `--config-only` - Restore only local configuration
- `--vapi-only` - Restore only VAPI data
- `--dry-run` - Preview restore without applying changes
- `--dir TEXT` - Directory for assistants (default: `assistants`)

**Example:**
```bash
vapi-manager file restore backup_20240101.zip --env development --overwrite
```

---

### `file backups`

List available backups.

**Usage:**
```bash
vapi-manager file backups [OPTIONS]
```

**Options:**
- `--dir TEXT` - Directory containing assistants (default: `assistants`)

**Example:**
```bash
vapi-manager file backups
```

---

### `file backup-info`

Show detailed backup information.

**Usage:**
```bash
vapi-manager file backup-info <backup_id> [OPTIONS]
```

**Parameters:**
- `backup_id` (required) - Backup ID to show details for

**Options:**
- `--dir TEXT` - Directory containing assistants (default: `assistants`)

**Example:**
```bash
vapi-manager file backup-info backup_20240101_120000
```

---

### `file backup-delete`

Delete a backup.

**Usage:**
```bash
vapi-manager file backup-delete <backup_id> [OPTIONS]
```

**Parameters:**
- `backup_id` (required) - Backup ID to delete

**Options:**
- `--dir TEXT` - Directory containing assistants (default: `assistants`)

**Example:**
```bash
vapi-manager file backup-delete backup_20240101_120000
```

---

## Tool Commands

### `tool create`

Create a new shared tool from a template.

**Usage:**
```bash
vapi-manager tool create <name> [OPTIONS]
```

**Parameters:**
- `name` (required) - Tool name (filename without .yaml extension)

**Options:**
- `--template TEXT` - Template to use (default: `basic_webhook`)
- `--description TEXT` - Tool description
- `--url TEXT` - Server webhook URL
- `--force` - Overwrite if tool exists
- `--dry-run` - Preview without creating

**Example:**
```bash
vapi-manager tool create bookAppointment --template basic_webhook --url https://api.example.com/book
vapi-manager tool create customTool --description "Custom tool" --force
```

---

### `tool templates`

List available tool templates.

**Usage:**
```bash
vapi-manager tool templates
```

**Example:**
```bash
vapi-manager tool templates
```

---

### `tool template-info`

Show tool template information.

**Usage:**
```bash
vapi-manager tool template-info <template>
```

**Parameters:**
- `template` (required) - Template name

**Example:**
```bash
vapi-manager tool template-info basic_webhook
```

---

### `tool preview`

Preview tool generation from template.

**Usage:**
```bash
vapi-manager tool preview <name> [OPTIONS]
```

**Parameters:**
- `name` (required) - Tool name

**Options:**
- `--template TEXT` - Template to use (default: `basic_webhook`)
- `--description TEXT` - Tool description
- `--url TEXT` - Server webhook URL

**Example:**
```bash
vapi-manager tool preview myTool --template basic_webhook --url https://api.example.com
```

---

## Environment Variables

### Required

**`VAPI_API_KEY`**
Your VAPI API key for authentication.

```bash
export VAPI_API_KEY="your-api-key-here"
```

### Optional

**`VAPI_BASE_URL`**
Base URL for VAPI API (default: `https://api.vapi.ai`)

```bash
export VAPI_BASE_URL="https://api.vapi.ai"
```

**`VAPI_MANAGER_CONFIG_DIR`**
Configuration directory for VAPI Manager (default: `~/.vapi-manager`)

```bash
export VAPI_MANAGER_CONFIG_DIR="~/.vapi-manager"
```

**`VAPI_MANAGER_LOG_LEVEL`**
Logging level (default: `INFO`)

```bash
export VAPI_MANAGER_LOG_LEVEL="DEBUG"
```

---

## Common Patterns

### Working with Environments

VAPI Manager supports three standard environments:
- `development` - For active development and testing
- `staging` - For pre-production validation
- `production` - For production deployments

**Example workflow:**
```bash
# Create in development
vapi-manager assistant create my_assistant --env development

# Test and iterate
vapi-manager assistant update my_assistant --env development

# Promote to staging
vapi-manager assistant create my_assistant --env staging --force

# Promote to production
vapi-manager assistant create my_assistant --env production --force
```

### Backup and Restore Workflow

**Creating backups:**
```bash
# Backup specific assistant before update
vapi-manager assistant backup my_assistant --env production --description "Pre-update backup"

# Backup entire squad
vapi-manager squad backup my_squad --env production --type complete
```

**Restoring from backup:**
```bash
# Restore to development for testing
vapi-manager assistant restore backup_20240101.zip --env development

# Restore and overwrite production
vapi-manager assistant restore backup_20240101.zip --env production --overwrite
```

### Template-Based Development

**Initialize from template:**
```bash
# Create assistant from template
vapi-manager assistant init customer_service --template default

# Create squad from template
vapi-manager squad init support_team --template dental_clinic_squad
```

**Create custom templates:**
```bash
# Create squad template
vapi-manager squad create-template my_template \
  --description "My custom squad" \
  --assistant "triage:default:receptionist" \
  --assistant "support:default:specialist"
```

### Dry Run Pattern

Use `--dry-run` to preview changes before applying:

```bash
# Preview assistant update
vapi-manager assistant update my_assistant --env production --dry-run

# Preview squad parameter changes
vapi-manager squad set-params my_squad --model gpt-4 --dry-run

# Preview restore operation
vapi-manager assistant restore backup.zip --dry-run
```

### Squad-Wide Updates

Update parameters across all assistants in a squad:

```bash
# Update voice for all squad members
vapi-manager squad set-params my_squad --voice-provider elevenlabs --voice-id Rachel

# Update model and temperature
vapi-manager squad set-params my_squad --model gpt-4o-mini --temperature 0.7

# Apply changes to VAPI
vapi-manager squad set-params my_squad --voice-id Jennifer --update-vapi --env production
```

### Pipeline Deployments

Deploy squads through multi-environment pipelines:

```bash
# Deploy through pipeline with approvals
vapi-manager squad bootstrap-pipeline my_squad \
  --environments development,staging,production \
  --strategy rolling \
  --approval

# Quick deployment to all environments
vapi-manager squad bootstrap-pipeline my_squad --strategy all_at_once
```

### Health Monitoring

Monitor squad and assistant health:

```bash
# Check squad health
vapi-manager squad health-check my_squad --env production

# View deployment status
vapi-manager squad deployment-status my_squad

# Check assistant status
vapi-manager file status my_assistant
```

---

## Project Structure

```
your-project/
├── assistants/              # Assistant configurations
│   ├── assistant1/
│   │   ├── assistant.yaml   # Main configuration
│   │   ├── vapi_state.json  # Deployment state tracking
│   │   ├── prompts/
│   │   │   ├── system.md    # System prompt
│   │   │   └── first_message.md
│   │   └── tools/
│   │       ├── functions.yaml    # Function tools
│   │       └── transfers.yaml    # Transfer destinations
│   └── assistant2/
│
├── squads/                  # Squad configurations
│   └── my_squad/
│       ├── squad.yaml       # Squad metadata
│       ├── members.yaml     # Squad members
│       ├── vapi_state.json  # Deployment state
│       └── routing/
│           └── destinations.yaml  # Routing config
│
├── shared/                  # Shared resources
│   ├── tools/              # Shared tool definitions
│   ├── prompts/            # Shared prompts
│   └── schemas/            # Shared schemas
│
├── templates/              # Custom templates
│   ├── assistants/         # Assistant templates
│   └── squads/             # Squad templates
│
└── .backups/               # Automatic backups
```

---

## Command Summary

### Assistant Commands (10)
- `assistant list` - List all assistants
- `assistant get` - Get assistant by ID
- `assistant validate` - Validate configuration
- `assistant init` - Initialize from template
- `assistant create` - Deploy to VAPI
- `assistant delete` - Delete from VAPI
- `assistant update` - Update with change detection
- `assistant backup` - Create backup
- `assistant restore` - Restore from backup
- `assistant add-tool` - Add shared tool

### Squad Commands (26)
- `squad list` - List all squads
- `squad get` - Get squad by ID
- `squad init` - Initialize from template
- `squad create` - Deploy to VAPI
- `squad file-list` - List local squads
- `squad templates` - List templates
- `squad template-info` - Show template details
- `squad create-template` - Create new template
- `squad update` - Update with change detection
- `squad status` - Show deployment status
- `squad delete` - Delete from VAPI
- `squad add-member` - Add member assistant
- `squad backup` - Create backup
- `squad restore` - Restore from backup
- `squad backups` - List backups
- `squad backup-info` - Show backup details
- `squad backup-delete` - Delete backup
- `squad set-params` - Update squad parameters
- `squad bootstrap` - Bootstrap from template
- `squad bootstrap-templates` - List bootstrap templates
- `squad bootstrap-rollback` - Rollback bootstrap
- `squad bootstrap-update` - Update bootstrapped squad
- `squad bootstrap-pipeline` - Multi-environment deployment
- `squad health-check` - Run health checks
- `squad deployment-status` - Get deployment status
- `squad promote` - Promote between environments

### File Commands (13)
- `file list` - List local assistants
- `file validate` - Validate configuration
- `file deploy` - Deploy to VAPI
- `file init` - Initialize from template
- `file templates` - List templates
- `file template-info` - Show template details
- `file create` - Create in VAPI
- `file status` - Show deployment status
- `file update` - Update with change detection
- `file backup` - Create backup
- `file restore` - Restore from backup
- `file backups` - List backups
- `file backup-info` - Show backup details
- `file backup-delete` - Delete backup

### Tool Commands (4)
- `tool create` - Create shared tool
- `tool templates` - List tool templates
- `tool template-info` - Show template details
- `tool preview` - Preview tool generation

### Agent Commands (1)
- `agent list` - List all agents

**Total Commands: 55**

---

## Support and Resources

- **Documentation**: https://docs.vapi-manager.io
- **GitHub Repository**: https://github.com/vapi-ai/vapi-manager
- **Issue Tracker**: https://github.com/vapi-ai/vapi-manager/issues
- **Discussions**: https://github.com/vapi-ai/vapi-manager/discussions
- **Discord Community**: https://discord.gg/vapi-manager

---

## License

This project is licensed under the MIT License.

---

**Generated**: 2025-10-01
**Version**: 1.0.0
**CLI Tool**: vapi-manager, vapi, vapictl
