# Docker MCP Orchestrator

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)

**Reduce MCP token usage by 90%+** — Load Docker MCP servers on-demand instead of exposing all tools at once.

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

## ✅ The Solution

**Docker MCP Orchestrator** acts as a lightweight meta-server that:

1. **Exposes only 8 orchestration tools** (instead of 100+)
2. **Enables/disables servers on-demand** via Docker MCP CLI
3. **Provides a server catalog** so the LLM knows what's available
4. **Supports hot-reload** through Docker MCP Gateway

```
✅ After: 8 tools + on-demand loading
┌─────────────────────────────────────────────────────────┐
│                      CURSOR                              │
│  Context: ~8 orchestrator tools                         │
│  Typical: 500-2,000 tokens/request (90%+ reduction)     │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Docker MCP Orchestrator                       │
│   • list_available_servers()                            │
│   • activate_server(name)                               │
│   • deactivate_server(name)                             │
│   • activate_for_task(description)                      │
│   • get_active_servers()                                │
│   • deactivate_all()                                    │
│   • server_info(name)                                   │
│   • sync_state()                                        │
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
| Simple query | ~17,000 | ~800 | **95%** |
| 1 active server | ~17,000 | ~2,500 | **85%** |
| 3 active servers | ~17,000 | ~6,000 | **65%** |

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

### List Available Servers

```
User: What MCP servers can I use?
AI: [calls list_available_servers()]
```

### Activate a Server

```
User: I need to take a screenshot of a website
AI: [calls activate_server("playwright", "Screenshot capture")]
    [uses browser_navigate, browser_screenshot tools]
```

### Auto-Select Servers for Task

```
User: Research React docs and create a GitHub issue with findings
AI: [calls activate_for_task("research docs and create GitHub issue")]
    # Auto-activates: context7, github
```

### Cleanup

```
User: Done with browser tasks
AI: [calls deactivate_server("playwright")]

User: Clean up all servers
AI: [calls deactivate_all()]
```

## 🛠️ Available Tools

| Tool | Description |
|------|-------------|
| `list_available_servers()` | Catalog of all MCP servers with descriptions |
| `get_active_servers()` | Currently enabled servers and their tools |
| `activate_server(name, reason)` | Enable a specific MCP server |
| `deactivate_server(name)` | Disable a specific MCP server |
| `activate_for_task(desc)` | Auto-detect and activate servers for a task |
| `deactivate_all()` | Disable all active servers |
| `server_info(name)` | Detailed info about a specific server |
| `sync_state()` | Sync state with Docker MCP Toolkit |

## 📦 Supported Servers

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

Edit `src/mcp_orchestrator/server.py`:

```python
MCP_SERVER_REGISTRY["my-server"] = MCPServerConfig(
    name="my-server",
    description="What this server does",
    tools_summary="tool1, tool2, tool3",
    category="custom",
    estimated_tools=5
)
```

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
