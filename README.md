# VAPI Manager

[![PyPI version](https://badge.fury.io/py/vapi-manager.svg)](https://badge.fury.io/py/vapi-manager)
[![Python Versions](https://img.shields.io/pypi/pyversions/vapi-manager.svg)](https://pypi.org/project/vapi-manager/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Downloads](https://pepy.tech/badge/vapi-manager)](https://pepy.tech/project/vapi-manager)

A comprehensive CLI tool for managing VAPI assistants and squads with support for templates, deployments, and team collaboration.

## Features

✨ **Assistant Management**
- Create, update, and delete VAPI assistants
- Template-based initialization
- Multi-environment deployments (development, staging, production)
- Backup and restore capabilities
- Advanced update strategies with change detection

🚀 **Squad Management**
- Orchestrate multiple assistants as cohesive squads
- Automatic routing configuration between squad members
- Bootstrap complete squad systems from templates
- Squad-wide parameter updates
- Health checks and deployment status monitoring

🔧 **Development Tools**
- YAML-based configuration
- Shared tools and prompt management
- VAPI built-in tools integration
- Template creation and customization
- Comprehensive validation

📦 **Enterprise Features**
- Multi-environment pipeline deployments
- Backup and restore with versioning
- Deployment state tracking
- Rollback capabilities
- Team collaboration support

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

## Quick Start

### 1. Set up your environment

```bash
export VAPI_API_KEY="your-api-key-here"
```

### 2. Initialize a new assistant

```bash
vapi-manager assistant init my_assistant --template default
```

### 3. Deploy to VAPI

```bash
vapi-manager assistant create my_assistant --env development
```

### 4. Create a squad

```bash
vapi-manager squad init my_squad --assistants assistant1,assistant2,assistant3
```

### 5. Deploy the squad

```bash
vapi-manager squad create my_squad --env development --auto-deploy-assistants
```

## Core Commands

### Assistant Management

```bash
# List all assistants
vapi-manager assistant list

# Create from template
vapi-manager assistant init my_assistant --template customer_service

# Deploy to VAPI
vapi-manager assistant create my_assistant --env production

# Update existing assistant
vapi-manager assistant update my_assistant --env development

# Backup assistant
vapi-manager assistant backup my_assistant --env production

# Delete assistant
vapi-manager assistant delete my_assistant --env production
```

### Squad Management

```bash
# List squads
vapi-manager squad list

# Initialize squad
vapi-manager squad init my_squad --template dental_clinic

# Deploy squad
vapi-manager squad create my_squad --env development

# Update all assistants in squad
vapi-manager squad update my_squad --env development --update-assistants

# Squad-wide parameter updates
vapi-manager squad set-params my_squad --voice-provider elevenlabs --voice-id Rachel

# Health check
vapi-manager squad health-check my_squad --env production
```

### Template Management

```bash
# List available templates
vapi-manager assistant templates

# Show template details
vapi-manager assistant template-info customer_service

# Create custom template
vapi-manager squad create-template my_template --assistants assistant1,assistant2
```

## Configuration Structure

```yaml
# assistants/my_assistant/assistant.yaml
name: my_assistant
description: Customer service assistant
model:
  provider: openai
  model: gpt-4
  temperature: 0.7
voice:
  provider: elevenlabs
  voiceId: Rachel
transcriber:
  provider: deepgram
  model: nova-2
  language: en
firstMessageMode: assistant-speaks-first-with-model-generated-message
server:
  url: https://your-webhook-url.com
  timeoutSeconds: 20
```

## Squad Configuration

```yaml
# squads/my_squad/squad.yaml
name: my_squad
description: Customer service squad
version: 1.0.0
metadata:
  created_by: team@example.com
  environment: production

# squads/my_squad/members.yaml
members:
- assistant_name: triage_assistant
  role: receptionist
  priority: 1
- assistant_name: billing_assistant
  role: specialist
  priority: 2
- assistant_name: technical_assistant
  role: specialist
  priority: 2
```

## Advanced Features

### Multi-Environment Deployments

```bash
# Deploy through pipeline
vapi-manager squad bootstrap-pipeline my_squad \
  --environments development staging production \
  --strategy rolling

# Promote between environments
vapi-manager squad promote my_squad \
  --from-env staging \
  --to-env production
```

### Squad-Wide Parameter Updates

```bash
# Update voice for all assistants
vapi-manager squad set-params my_squad \
  --voice-provider vapi \
  --voice-id Jennifer

# Update model settings
vapi-manager squad set-params my_squad \
  --model gpt-4 \
  --temperature 0.5 \
  --max-tokens 2000

# Dry run to preview changes
vapi-manager squad set-params my_squad \
  --model gpt-4 \
  --dry-run
```

### Backup and Restore

```bash
# Backup assistant
vapi-manager assistant backup my_assistant \
  --env production \
  --description "Before major update"

# Restore assistant
vapi-manager assistant restore backup_20240101_120000.zip \
  --env development

# Squad backup with all assistants
vapi-manager squad backup my_squad \
  --type complete \
  --env production

# Restore squad
vapi-manager squad restore squad_backup_20240101.zip \
  --env development
```

## Environment Variables

```bash
# Required
export VAPI_API_KEY="your-api-key"

# Optional
export VAPI_BASE_URL="https://api.vapi.ai"  # Default
export VAPI_MANAGER_CONFIG_DIR="~/.vapi-manager"  # Config directory
export VAPI_MANAGER_LOG_LEVEL="INFO"  # Log level
```

## Project Structure

```
your-project/
├── assistants/           # Assistant configurations
│   ├── assistant1/
│   │   ├── assistant.yaml
│   │   ├── prompts/
│   │   │   ├── system.md
│   │   │   └── first_message.md
│   │   └── tools/
│   │       ├── functions.yaml
│   │       └── transfers.yaml
│   └── assistant2/
├── squads/              # Squad configurations
│   └── my_squad/
│       ├── squad.yaml
│       ├── members.yaml
│       └── routing/
│           └── destinations.yaml
├── shared/              # Shared resources
│   ├── tools/
│   ├── prompts/
│   └── schemas/
└── templates/           # Custom templates
    ├── assistants/
    └── squads/
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

```bash
# Setup development environment
git clone https://github.com/vapi-ai/vapi-manager
cd vapi-manager
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black vapi_manager
ruff check vapi_manager
```

## Support

- 📖 [Documentation](https://docs.vapi-manager.io)
- 💬 [Discord Community](https://discord.gg/vapi-manager)
- 🐛 [Issue Tracker](https://github.com/vapi-ai/vapi-manager/issues)
- 💡 [Discussions](https://github.com/vapi-ai/vapi-manager/discussions)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with ❤️ by the VAPI community.

Special thanks to all contributors and users who make this project possible.