# VAPI Tool for Ange

A comprehensive Python CLI tool for managing VAPI assistants, squads, and agents. This tool provides a structured approach to create, read, update, and delete conversational AI assistants on the VAPI platform.

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## ✨ Features

- **Assistant Management**: Full CRUD operations for VAPI assistants
- **Squad Management**: Create and manage squads that group multiple assistants
- **Agent Management**: High-level abstraction combining squads with their assistants
- **Rich CLI Interface**: Beautiful terminal output with formatted tables
- **Async Architecture**: Built with async/await for optimal performance
- **Type Safety**: Full Pydantic model validation
- **Extensible Design**: Easy to add new VAPI entity types

## 🏗️ Architecture

The project follows a clean architecture pattern with clear separation of concerns:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│     CLI     │────▶│   Services  │────▶│  VAPI API   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│   Models    │     │   Client    │
└─────────────┘     └─────────────┘
```

- **Models**: Pydantic models for data validation
- **Services**: Business logic layer
- **CLI**: User interface with rich formatting
- **Client**: HTTP client for VAPI API communication

## 📦 Installation

### Prerequisites

- Python 3.12 or higher
- Poetry (for dependency management)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/vapi-tool-for-ange.git
cd vapi-tool-for-ange
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env and add your VAPI API key
```

## ⚙️ Configuration

Create a `.env` file in the project root with the following variables:

```env
VAPI_API_KEY="your-vapi-api-key-here"
```

Optional configuration:
```env
VAPI_BASE_URL="https://api.vapi.ai"  # Default VAPI API URL
LOG_LEVEL="INFO"                      # Logging level
TIMEOUT=30                             # API timeout in seconds
```

## 🚀 Usage

### Basic Commands

The tool provides three main command groups: `assistant`, `squad`, and `agent`.

#### Assistant Commands

List all assistants:
```bash
poetry run vapi-manager assistant list
```

List assistants with limit:
```bash
poetry run vapi-manager assistant list --limit 10
```

Get assistant details:
```bash
poetry run vapi-manager assistant get <assistant-id>
```

#### Squad Commands

List all squads:
```bash
poetry run vapi-manager squad list
```

List squads with limit:
```bash
poetry run vapi-manager squad list --limit 5
```

#### Agent Commands

List all agents (squads with their assistants):
```bash
poetry run vapi-manager agent list
```

List agents with limit:
```bash
poetry run vapi-manager agent list --limit 10
```

### Command Examples

```bash
# Get help for the main command
poetry run vapi-manager --help

# Get help for assistant commands
poetry run vapi-manager assistant --help

# List all assistants with their details
poetry run vapi-manager assistant list

# Get specific assistant information
poetry run vapi-manager assistant get 46ceb742-224f-49ea-affc-14cbbe4191b5

# List all squads
poetry run vapi-manager squad list

# List all agents (complete view of squads and their assistants)
poetry run vapi-manager agent list
```

### Output Example

```
                          VAPI Assistants
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┓
┃ ID          ┃ Name         ┃ Model       ┃ Voice     ┃ Created ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━┩
│ 46ceb742... │ triage       │ gpt-4o-mini │ minimax   │ 2025-09 │
│ 8eb5b995... │ scheduler    │ gpt-4o-mini │ minimax   │ 2025-09 │
│ a702f56a... │ manager      │ gpt-4o-mini │ minimax   │ 2025-09 │
└─────────────┴──────────────┴─────────────┴───────────┴─────────┘
```

## 📚 API Reference

### Models

#### Assistant
- `id`: Unique identifier
- `name`: Assistant name
- `voice`: Voice configuration
- `model`: AI model configuration
- `transcriber`: Speech-to-text settings
- `first_message`: Initial greeting
- `analysis_plan`: Post-call analysis configuration

#### Squad
- `id`: Unique identifier
- `name`: Squad name
- `members`: List of assistant IDs in the squad

#### Agent
- `id`: Unique identifier
- `name`: Agent name
- `squad`: Associated squad
- `assistants`: List of assistants in the squad

## 📁 Project Structure

```
vapi-tool-for-ange/
├── vapi_manager/
│   ├── core/
│   │   ├── models/          # Pydantic data models
│   │   │   ├── assistant.py
│   │   │   ├── squad.py
│   │   │   └── agent.py
│   │   ├── schemas/         # API request/response schemas
│   │   └── exceptions/      # Custom exceptions
│   ├── services/            # Business logic
│   │   ├── vapi_client.py  # HTTP client
│   │   ├── assistant_service.py
│   │   ├── squad_service.py
│   │   └── agent_service.py
│   ├── config/
│   │   └── settings.py      # Configuration management
│   ├── utils/
│   │   └── helpers.py       # Utility functions
│   └── cli/
│       └── simple_cli.py    # Command-line interface
├── tests/                   # Test files
├── .env                     # Environment variables (git-ignored)
├── .gitignore              # Git ignore rules
├── pyproject.toml          # Project dependencies
├── poetry.lock             # Locked dependencies
└── README.md               # This file
```

## 🛠️ Development

### Running Tests

```bash
poetry run pytest
```

### Code Formatting

```bash
poetry run black vapi_manager/
```

### Linting

```bash
poetry run ruff vapi_manager/
```

### Type Checking

```bash
poetry run mypy vapi_manager/
```

### Installing Development Dependencies

```bash
poetry install --with dev
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add type hints to all functions
- Write docstrings for all public methods
- Add tests for new features
- Update README for new commands

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built for managing VAPI.ai assistants
- Uses Poetry for dependency management
- Rich library for beautiful terminal output
- Pydantic for data validation

## 📞 Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Note**: This tool is not officially affiliated with VAPI.ai. It's an independent tool created to facilitate VAPI assistant management.