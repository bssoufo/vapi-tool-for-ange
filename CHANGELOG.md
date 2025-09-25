# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-25

### Added
- Initial release of VAPI Manager
- Assistant management (create, update, delete, list)
- Squad management with routing and member configuration
- Multi-environment deployment support (development, staging, production)
- Template system for assistants and squads
- Backup and restore functionality
- Squad-wide parameter updates with `squad set-params` command
- Bootstrap system for complete squad deployment
- VAPI built-in tools integration (endCall, transferCall)
- Shared tools and prompts management
- Deployment state tracking
- Rich CLI interface with formatted output
- Comprehensive validation and error handling

### Core Features
- **Assistant Operations**
  - Create assistants from templates
  - Deploy to multiple environments
  - Update with change detection
  - Backup and restore capabilities
  - Shared tool references

- **Squad Operations**
  - Initialize squads with multiple assistants
  - Automatic routing configuration
  - Member management
  - Health checks
  - Squad-wide parameter updates

- **Template System**
  - Pre-built assistant templates
  - Squad templates with manifest
  - Custom template creation
  - Template validation

- **Enterprise Features**
  - Multi-environment pipelines
  - Deployment promotion
  - Rollback capabilities
  - Team collaboration support

### Technical Details
- Python 3.8+ support
- Async architecture for optimal performance
- Pydantic models for validation
- YAML-based configuration
- Environment variable support
- Cross-platform compatibility

## [0.1.0] - 2024-01-01 (Pre-release)

### Added
- Basic assistant CRUD operations
- Simple squad creation
- Initial template support
- Basic CLI interface

---

## Upcoming Features (Roadmap)

### [1.1.0] - Planned
- Web dashboard for visual management
- Automated testing framework
- Performance analytics
- Advanced routing strategies
- Webhook management UI

### [1.2.0] - Planned
- Multi-tenant support
- Role-based access control
- Audit logging
- Advanced backup strategies
- Cloud storage integration

### [2.0.0] - Future
- GraphQL API
- Kubernetes operator
- Terraform provider
- CI/CD integrations
- Enterprise SSO support

---

## Migration Guide

### From 0.x to 1.0

1. **Configuration Changes**:
   - `rules.yaml` has been removed, use `destinations.yaml` instead
   - Squad members now use `assistant_name` instead of `assistant`

2. **Command Changes**:
   - `vapi-manager squad update` now supports `--update-assistants` flag
   - New command: `vapi-manager squad set-params` for bulk updates

3. **Tool Integration**:
   - VAPI built-in tools are now in `shared/tools/vapi-builtins/`
   - Use `$ref` syntax for shared tool references

---

## Support

For issues, feature requests, or questions:
- GitHub Issues: https://github.com/vapi-ai/vapi-manager/issues
- Documentation: https://docs.vapi-manager.io
- Discord: https://discord.gg/vapi-manager