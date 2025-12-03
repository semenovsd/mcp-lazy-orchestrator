# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-01-XX

### Added
- **Automatic server discovery** - Automatically discovers all MCP servers from Docker MCP Toolkit
- **Compact catalog** - `get_capabilities()` returns lightweight catalog (~1200 tokens instead of 15k+)
- **Smart recommendations** - `suggest_servers(task)` with confidence scores
- **Semantic routing** - Keyword + semantic analysis for accurate server selection
- **Server profiles** - Predefined combinations for common tasks (web-development, data-science, etc.)
- **Usage monitoring** - Track server usage and get optimization recommendations
- **Auto-dependencies** - Automatically activates context7 for library documentation
- **Capabilities registry** - YAML-based configuration for server capabilities
- **Telemetry** - Observability for server activations and usage
- **Token optimization** - `optimize_servers()` auto-deactivates unused servers

### Changed
- **Breaking**: `activate_server()` now returns dict with full tools (legacy string format still available)
- **Breaking**: New core tools use dict returns for better structure
- Improved `activate_for_task()` with semantic analysis
- Enhanced error handling and logging

### Improved
- Token savings increased from 85% to 90-95%
- Better AI understanding through compact catalog
- Automatic technology → documentation mapping
- More accurate server recommendations

### Technical
- Modular architecture with separate components:
  - `discovery.py` - Automatic server discovery
  - `registry.py` - Server registry with caching
  - `capabilities.py` - Capabilities registry
  - `router.py` - Semantic routing
  - `analyzer.py` - Task analysis
  - `profiles.py` - Server profiles
  - `monitor.py` - Usage monitoring
  - `telemetry.py` - Observability
- Added PyYAML dependency for capabilities configuration

## [1.0.0] - 2025-12-03

### Added
- Initial release
- Core orchestration tools:
  - `list_available_servers()` - Server catalog with descriptions
  - `activate_server(name, reason)` - Enable MCP server on-demand
  - `deactivate_server(name)` - Disable MCP server
  - `activate_for_task(description)` - Auto-detect servers for task
  - `get_active_servers()` - List active servers with tools
  - `deactivate_all()` - Disable all servers
  - `server_info(name)` - Detailed server information
  - `sync_state()` - Sync with Docker MCP Toolkit
- Support for 8 Docker MCP Toolkit servers:
  - context7 (documentation)
  - playwright (browser automation)
  - github (GitHub integration)
  - fetch (HTTP client)
  - desktop-commander (file system)
  - postgres (PostgreSQL)
  - redis (Redis)
  - sequential-thinking (reasoning)
- English and Russian documentation
- Cursor and Claude Desktop configuration examples
- Unit tests with pytest
- CC BY-NC 4.0 license

### Performance
- Reduces token usage by 90%+ compared to loading all MCP tools
- Typical context: 500-2,000 tokens vs 15,000-20,000 tokens

## [Unreleased]

### Planned
- Support for additional MCP servers
- Configuration file for custom server registry
- GUI for server management
- Integration with more MCP clients
