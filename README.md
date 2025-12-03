# Docker MCP Orchestrator v2.0

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)

**Reduce MCP token usage by 90%+** — Smart orchestrator with automatic discovery, semantic routing, and on-demand activation.

[🇷🇺 Документация на русском](docs/README_RU.md)

---

## 🎯 The Problem

When using **Docker MCP Toolkit** with Cursor, Claude Desktop, or other MCP clients, **all tools from all enabled servers are loaded simultaneously**. With 8 servers enabled, this easily exceeds **100+ tools**, consuming **15,000-20,000 tokens per request** just for tool definitions.

```
❌ Current: All 117 tools always loaded
┌─────────────────────────────────────────────────────────┐
│                      CURSOR                              │
│  Context: ~117 tools = 15,000-20,000 tokens/request     │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Docker MCP Gateway                          │
│   Context7 ─ Playwright ─ GitHub ─ PostgreSQL           │
│   Fetch ─── Redis ─────── Desktop ─ Sequential          │
│        ALL 117 tools exposed simultaneously             │
└─────────────────────────────────────────────────────────┘
```

## ✅ The Solution v2.0

**Docker MCP Orchestrator v2.0** is a smart orchestrator that:

1. **Automatically discovers** all MCP servers from Docker MCP Toolkit
2. **Provides compact catalog** (~800-1200 tokens) instead of full tool definitions
3. **Smart recommendations** using keyword + semantic analysis
4. **On-demand activation** - only load tools you need
5. **Auto-dependencies** - automatically activates context7 for documentation
6. **Server profiles** - ready-made combinations for common tasks
7. **Usage monitoring** - tracks and optimizes server usage

```
✅ After: 8 tools + compact catalog + on-demand activation
┌─────────────────────────────────────────────────────────┐
│                      CURSOR                              │
│  Context: ~8 orchestrator tools (~500 tokens)           │
│  + Compact catalog (~1200 tokens)                       │
│  + Only activated servers (~2000 tokens)                │
│  Typical: 3,000-4,000 tokens/request (90%+ reduction)   │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Docker MCP Orchestrator v2.0                 │
│   • get_capabilities() - Compact catalog                 │
│   • suggest_servers(task) - Smart recommendations        │
│   • activate_servers([]) - On-demand activation         │
│   • activate_profile(name) - Predefined profiles        │
│   • monitor_usage() - Usage statistics                  │
│   • optimize_servers() - Auto-cleanup                   │
└─────────────────────────────────────────────────────────┘
                           │
        subprocess: docker mcp server enable/disable
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Docker MCP Gateway                          │
│   [Inactive] Most servers stay dormant                  │
│   [Active]   Only servers needed for current task       │
└─────────────────────────────────────────────────────────┘
```

## 📊 Token Savings

| Scenario | Before | After | Savings |
|----------|--------|-------|---------|
| Simple query | ~17,000 | ~1,700 | **90%** |
| 1 active server | ~17,000 | ~3,200 | **81%** |
| 3 active servers | ~17,000 | ~5,000 | **71%** |
| With optimization | ~17,000 | ~2,500 | **85%** |

## 🚀 Quick Start

### Requirements

- **Python 3.11+**
- **Docker Desktop** with MCP Toolkit enabled
- **Cursor 2.x** / Claude Desktop / any MCP client

### Installation

```bash
# Clone the repository
git clone https://github.com/semenovsd/docker-mcp-orchestrator.git
cd docker-mcp-orchestrator

# Install with pip
pip install -e .

# Or with uv
uv pip install -e .
```

### Configuration

1. **Disable servers in Docker MCP Toolkit** (recommended):

```bash
docker mcp server disable context7 playwright github fetch \
    desktop-commander postgres redis sequential-thinking
```

2. **Configure your MCP client**:

**Cursor** (`~/.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "orchestrator": {
      "command": "python",
      "args": ["-m", "mcp_orchestrator"],
      "type": "stdio"
    }
  }
}
```

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "orchestrator": {
      "command": "python",
      "args": ["-m", "mcp_orchestrator"]
    }
  }
}
```

3. **Restart your MCP client**

## 📖 Usage

### 1. Get Compact Catalog

```
User: What MCP servers can I use?
AI: [calls get_capabilities()]
    Returns: Compact catalog with metadata (~1200 tokens)
```

### 2. Smart Recommendations

```
User: I need to set up Redis cache for FastAPI
AI: [calls suggest_servers("Redis cache for FastAPI")]
    Returns: 
      - context7 (0.95) - Documentation
      - redis (0.90) - Operations
```

### 3. Activate Servers

```
AI: [calls activate_servers(["context7", "redis"])]
    Returns: Full tool definitions for activated servers
    (~2500 tokens instead of 17000!)
```

### 4. Use Profiles

```
User: I'm doing web development
AI: [calls activate_profile("web-development")]
    Activates: playwright, github, context7, fetch
```

### 5. Monitor and Optimize

```
AI: [calls monitor_usage()]
    Shows: Usage statistics and recommendations

AI: [calls optimize_servers()]
    Deactivates: Unused servers (>10 min idle)
```

## 🛠️ Available Tools

### Core Tools (v2.0)

| Tool | Description |
|------|-------------|
| `get_capabilities()` | Compact catalog of all servers (~1200 tokens) |
| `suggest_servers(task)` | Smart recommendations with confidence scores |
| `activate_servers([])` | Activate servers and get full tools |
| `activate_profile(name)` | Activate predefined profile |
| `activate_for_task(desc)` | Smart task-based activation |
| `deactivate_servers([])` | Deactivate specific servers |
| `get_status()` | Current orchestrator state |
| `monitor_usage()` | Usage statistics and recommendations |
| `optimize_servers()` | Auto-deactivate unused servers |

### Legacy Tools (for compatibility)

| Tool | Description |
|------|-------------|
| `list_available_servers()` | Legacy catalog (use get_capabilities) |
| `activate_server(name)` | Legacy single activation |
| `deactivate_server(name)` | Legacy single deactivation |
| `server_info(name)` | Detailed server information |
| `sync_state()` | Sync with Docker MCP Toolkit |

## 📦 Supported Servers

The orchestrator **automatically discovers** all servers from Docker MCP Toolkit. Popular servers include:

| Server | Category | Description |
|--------|----------|-------------|
| `context7` | Documentation | Library/framework docs |
| `playwright` | Browser | Web automation, screenshots |
| `github` | Version Control | GitHub API integration |
| `fetch` | Networking | HTTP requests |
| `desktop-commander` | System | File system, commands |
| `postgres` | Database | PostgreSQL queries |
| `redis` | Database | Redis operations |
| `sequential-thinking` | Reasoning | Multi-step analysis |

### Adding Custom Servers

Servers are **automatically discovered** from Docker MCP Toolkit. To customize metadata, edit `capabilities/base.yaml`:

```yaml
servers:
  my-server:
    purpose: "What this server does"
    covers_technologies: ["tech1", "tech2"]
    when_to_use: "When to use this server"
    related_servers: ["context7"]  # Auto-activate with
```

## 🎯 Server Profiles

Predefined profiles for common tasks:

- **web-development**: playwright, github, context7, fetch
- **data-science**: postgres, redis, context7
- **documentation**: context7
- **database**: postgres, redis, context7
- **browser-automation**: playwright, context7
- **full-stack**: all servers (requires confirmation)

## ⚠️ Known Limitations

### Cursor Hot-Reload

Cursor 2.x requires restarting the MCP connection to detect new tools. This is a Cursor limitation, not MCP protocol. After activating a server:
- The orchestrator reports available tools
- Tools work through the gateway even if not visible in Cursor UI
- Restart MCP connection in Cursor settings if needed

### Authentication

Servers requiring OAuth (like GitHub) need authentication configured in Docker MCP Toolkit before activation.

## 🔧 Troubleshooting

### "Docker MCP CLI not found"

Ensure Docker Desktop is installed with MCP Toolkit enabled:
1. Docker Desktop → Settings → Beta features
2. Enable "Docker MCP Toolkit"

### State Out of Sync

```
User: Sync the orchestrator
AI: [calls sync_state()]
```

### Server Activation Fails

Check if the server requires authentication:
```bash
docker mcp server inspect <server-name>
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) — free for non-commercial use with attribution.

**You are free to:**
- Share — copy and redistribute
- Adapt — remix, transform, and build upon

**Under the following terms:**
- Attribution — give appropriate credit
- NonCommercial — not for commercial purposes

## 🙏 Acknowledgments

- [Anthropic](https://anthropic.com) for MCP protocol
- [Docker](https://docker.com) for MCP Toolkit
- MCP community for inspiration

---

**Star ⭐ this repo if it helped reduce your token costs!**
