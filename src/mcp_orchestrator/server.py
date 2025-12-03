"""
MCP Lazy Orchestrator

A lightweight MCP server that manages Docker MCP servers on-demand,
reducing token usage by only exposing orchestration tools and dynamically
loading/unloading individual MCP server tools as needed.

This solves the "too many tools" problem where Docker MCP Toolkit
exposes 100+ tools from all enabled servers, consuming excessive
context window tokens.

Author: semenovsd
License: CC BY-NC 4.0
Repository: https://github.com/semenovsd/mcp-lazy-orchestrator
"""

import asyncio
import json
import subprocess
import logging
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field

from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp-lazy-orchestrator")

# ============================================================================
# Configuration
# ============================================================================

@dataclass
class MCPServerConfig:
    """Configuration for an MCP server in Docker MCP Toolkit"""
    name: str
    description: str
    tools_summary: str
    category: str
    requires_auth: bool = False
    auth_type: str | None = None
    estimated_tools: int = 10


# Registry of available MCP servers with descriptions
# Add or modify entries to match your Docker MCP Toolkit setup
MCP_SERVER_REGISTRY: dict[str, MCPServerConfig] = {
    "context7": MCPServerConfig(
        name="context7",
        description="Up-to-date documentation for libraries and frameworks. "
                    "Use for current API docs, examples, library-specific info.",
        tools_summary="resolve-library-id, get-library-docs",
        category="documentation",
        estimated_tools=2
    ),
    "playwright": MCPServerConfig(
        name="playwright",
        description="Browser automation and web scraping. Screenshots, "
                    "navigation, form filling, clicking, data extraction.",
        tools_summary="browser_navigate, browser_screenshot, browser_click, "
                      "browser_fill, browser_evaluate, browser_get_text, etc.",
        category="browser",
        estimated_tools=15
    ),
    "github": MCPServerConfig(
        name="github",
        description="GitHub integration. Issues, PRs, repos, code search, "
                    "file contents, commits, GitHub API operations.",
        tools_summary="create_issue, create_pull_request, search_repositories, "
                      "get_file_contents, push_files, list_commits, etc.",
        category="version_control",
        requires_auth=True,
        auth_type="oauth",
        estimated_tools=20
    ),
    "fetch": MCPServerConfig(
        name="fetch",
        description="HTTP client for web requests. Fetch pages, APIs, "
                    "download content.",
        tools_summary="fetch",
        category="networking",
        estimated_tools=1
    ),
    "desktop-commander": MCPServerConfig(
        name="desktop-commander",
        description="Desktop automation and file system. File management, "
                    "command execution, process control.",
        tools_summary="read_file, write_file, execute_command, list_directory, etc.",
        category="system",
        estimated_tools=12
    ),
    "postgres": MCPServerConfig(
        name="postgres",
        description="PostgreSQL read-only database access. Queries, "
                    "schema exploration, data analysis.",
        tools_summary="query",
        category="database",
        estimated_tools=1
    ),
    "redis": MCPServerConfig(
        name="redis",
        description="Redis cache and data store. Caching, sessions, "
                    "pub/sub, data structures.",
        tools_summary="get, set, del, keys, hget, hset, lpush, rpush, etc.",
        category="database",
        estimated_tools=15
    ),
    "sequential-thinking": MCPServerConfig(
        name="sequential-thinking",
        description="Structured problem-solving through sequential reasoning. "
                    "Complex multi-step analysis and planning.",
        tools_summary="think, analyze, plan",
        category="reasoning",
        estimated_tools=3
    ),
}


# ============================================================================
# State Management
# ============================================================================

@dataclass
class OrchestratorState:
    """Tracks the state of the orchestrator"""
    active_servers: set[str] = field(default_factory=set)
    server_tools_cache: dict[str, list[dict]] = field(default_factory=dict)
    last_error: str | None = None


state = OrchestratorState()


# ============================================================================
# Docker MCP CLI Helpers
# ============================================================================

def run_docker_mcp_command(args: list[str], timeout: int = 60) -> tuple[bool, str]:
    """
    Execute a docker mcp CLI command.
    
    Args:
        args: Command arguments (after 'docker mcp')
        timeout: Command timeout in seconds
    
    Returns:
        Tuple of (success: bool, output: str)
    """
    cmd = ["docker", "mcp"] + args
    logger.info(f"Executing: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            logger.error(f"Command failed: {error_msg}")
            return False, error_msg
            
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout}s"
    except FileNotFoundError:
        return False, ("Docker MCP CLI not found. Ensure Docker Desktop "
                      "is installed with MCP Toolkit enabled.")
    except Exception as e:
        return False, f"Error: {str(e)}"


def get_enabled_servers() -> list[str]:
    """Get list of currently enabled MCP servers"""
    success, output = run_docker_mcp_command(["server", "ls"])
    
    if not success:
        logger.error(f"Failed to list servers: {output}")
        return []
    
    servers = []
    for line in output.split('\n'):
        line = line.strip()
        if line and not line.startswith('NAME') and not line.startswith('-'):
            parts = line.split()
            if parts:
                servers.append(parts[0])
    
    return servers


def enable_server(server_name: str) -> tuple[bool, str]:
    """Enable an MCP server"""
    return run_docker_mcp_command(["server", "enable", server_name])


def disable_server(server_name: str) -> tuple[bool, str]:
    """Disable an MCP server"""
    return run_docker_mcp_command(["server", "disable", server_name])


def get_server_tools(server_name: str) -> list[dict]:
    """Get tools provided by a specific server"""
    success, output = run_docker_mcp_command(
        ["tools", "list", "--server", server_name],
        timeout=30
    )
    
    if not success:
        return []
    
    tools = []
    try:
        data = json.loads(output)
        if isinstance(data, list):
            tools = data
        elif isinstance(data, dict) and "tools" in data:
            tools = data["tools"]
    except json.JSONDecodeError:
        for line in output.split('\n'):
            line = line.strip()
            if line and not line.startswith('TOOL') and not line.startswith('-'):
                parts = line.split(maxsplit=1)
                if parts:
                    tools.append({
                        "name": parts[0],
                        "description": parts[1] if len(parts) > 1 else ""
                    })
    
    return tools


# ============================================================================
# MCP Server Definition
# ============================================================================

mcp = FastMCP(
    name="MCP Lazy Orchestrator",
    version="1.0.0",
    description=(
        "Lightweight orchestrator for Docker MCP servers. "
        "Reduces token usage by loading servers on-demand instead of "
        "exposing all 100+ tools simultaneously."
    )
)


# ============================================================================
# Orchestrator Tools
# ============================================================================

@mcp.tool()
async def list_available_servers() -> str:
    """
    List all available MCP servers that can be activated.
    
    Shows a catalog with descriptions, categories, and estimated tool counts.
    Use this to discover servers before activating them.
    
    Returns:
        Formatted catalog of available MCP servers
    """
    result = ["# 📦 Available MCP Servers\n"]
    
    # Group by category
    categories: dict[str, list[MCPServerConfig]] = {}
    for config in MCP_SERVER_REGISTRY.values():
        if config.category not in categories:
            categories[config.category] = []
        categories[config.category].append(config)
    
    total_tools = 0
    for category, servers in sorted(categories.items()):
        result.append(f"\n## {category.replace('_', ' ').title()}\n")
        for server in servers:
            status = "🟢 ACTIVE" if server.name in state.active_servers else "⚪"
            auth = f" 🔐 {server.auth_type}" if server.requires_auth else ""
            total_tools += server.estimated_tools
            
            result.append(f"**{server.name}** [{status}]{auth}")
            result.append(f"  {server.description}")
            result.append(f"  _~{server.estimated_tools} tools: {server.tools_summary}_")
            result.append("")
    
    result.append(f"\n---\n**Total available**: {len(MCP_SERVER_REGISTRY)} servers, "
                  f"~{total_tools} tools")
    result.append(f"**Currently active**: {len(state.active_servers)} servers")
    
    return "\n".join(result)


@mcp.tool()
async def get_active_servers() -> str:
    """
    Get list of currently active MCP servers with their tools.
    
    Returns:
        List of active servers and their available tools
    """
    if not state.active_servers:
        return ("ℹ️ No MCP servers are currently active.\n\n"
                "Use `activate_server(name)` to enable one, or "
                "`activate_for_task(description)` for automatic selection.")
    
    result = ["# 🟢 Active MCP Servers\n"]
    
    for name in sorted(state.active_servers):
        config = MCP_SERVER_REGISTRY.get(name)
        if config:
            result.append(f"## {name}")
            result.append(f"**Category**: {config.category}")
            result.append(f"**Description**: {config.description}")
            
            tools = state.server_tools_cache.get(name, [])
            if tools:
                result.append(f"\n**Tools ({len(tools)}):**")
                for tool in tools[:10]:
                    result.append(f"  - `{tool.get('name', '?')}`")
                if len(tools) > 10:
                    result.append(f"  - _...and {len(tools) - 10} more_")
            result.append("")
    
    return "\n".join(result)


@mcp.tool()
async def activate_server(server_name: str, reason: str = "") -> str:
    """
    Activate (enable) an MCP server in Docker MCP Toolkit.
    
    This starts the server container and makes its tools available
    through the MCP gateway.
    
    Args:
        server_name: Server to activate (e.g., "playwright", "github")
        reason: Brief explanation why this server is needed
    
    Returns:
        Status message with available tools
    
    Examples:
        activate_server("playwright", "Need to screenshot a website")
        activate_server("github", "Creating an issue")
    """
    # Validate
    if server_name not in MCP_SERVER_REGISTRY:
        available = ", ".join(sorted(MCP_SERVER_REGISTRY.keys()))
        return f"❌ Unknown server: '{server_name}'\n\nAvailable: {available}"
    
    if server_name in state.active_servers:
        config = MCP_SERVER_REGISTRY[server_name]
        return (f"ℹ️ Server '{server_name}' is already active.\n\n"
                f"**Tools**: {config.tools_summary}")
    
    config = MCP_SERVER_REGISTRY[server_name]
    logger.info(f"Activating: {server_name} (reason: {reason})")
    
    success, output = enable_server(server_name)
    
    if success:
        state.active_servers.add(server_name)
        tools = get_server_tools(server_name)
        state.server_tools_cache[server_name] = tools
        
        lines = [
            f"✅ **{server_name}** activated!",
            f"",
            f"**Description**: {config.description}",
        ]
        
        if tools:
            lines.append(f"\n**Available tools ({len(tools)})**:")
            for t in tools[:12]:
                desc = t.get('description', '')[:60]
                lines.append(f"- `{t.get('name')}`: {desc}")
            if len(tools) > 12:
                lines.append(f"- _...and {len(tools) - 12} more_")
        
        if config.requires_auth:
            lines.append(f"\n⚠️ Requires {config.auth_type} auth. "
                        "Configure in Docker MCP Toolkit.")
        
        lines.append(f"\n📌 Tools from '{server_name}' are now available "
                    "via MCP gateway.")
        
        return "\n".join(lines)
    else:
        state.last_error = output
        return f"❌ Failed to activate '{server_name}': {output}"


@mcp.tool()
async def deactivate_server(server_name: str) -> str:
    """
    Deactivate (disable) an MCP server to free resources.
    
    Args:
        server_name: Server to deactivate
    
    Returns:
        Status message
    """
    if server_name not in state.active_servers:
        return f"ℹ️ Server '{server_name}' is not active."
    
    logger.info(f"Deactivating: {server_name}")
    success, output = disable_server(server_name)
    
    if success:
        state.active_servers.discard(server_name)
        state.server_tools_cache.pop(server_name, None)
        return f"✅ Server '{server_name}' deactivated."
    else:
        state.last_error = output
        return f"❌ Failed to deactivate '{server_name}': {output}"


@mcp.tool()
async def activate_for_task(task_description: str) -> str:
    """
    Automatically recommend and activate servers for a task.
    
    Analyzes the task and suggests appropriate MCP servers.
    
    Args:
        task_description: What you want to accomplish
    
    Returns:
        Recommendations and activation results
    
    Examples:
        activate_for_task("scrape website and create GitHub issue")
        activate_for_task("query PostgreSQL database")
    """
    task_lower = task_description.lower()
    recommendations: list[tuple[str, str]] = []
    
    # Keyword-based matching
    keyword_map = {
        "context7": ["documentation", "docs", "api reference", "library", 
                     "framework", "package", "sdk"],
        "playwright": ["browser", "screenshot", "scrape", "website", "click", 
                       "form", "web page", "navigate", "automation"],
        "github": ["github", "repository", "repo", "issue", "pull request", 
                   "pr", "commit", "code search", "gist"],
        "fetch": ["http", "api", "fetch", "download", "request", "url", "curl"],
        "desktop-commander": ["file", "folder", "directory", "command", 
                              "execute", "process", "terminal", "shell"],
        "postgres": ["database", "sql", "query", "postgres", "postgresql", 
                     "table", "db"],
        "redis": ["cache", "redis", "session", "pub/sub", "key-value"],
        "sequential-thinking": ["analyze", "think", "reason", "plan", 
                                "complex", "multi-step", "decision"],
    }
    
    for server, keywords in keyword_map.items():
        for kw in keywords:
            if kw in task_lower:
                config = MCP_SERVER_REGISTRY[server]
                recommendations.append((server, f"Keyword '{kw}': {config.description}"))
                break
    
    if not recommendations:
        return ("🤔 No servers auto-detected for this task.\n\n"
                "Use `list_available_servers()` to see options, or be more "
                "specific (e.g., 'browser', 'github', 'database').")
    
    result = [f"# 🔍 Task: {task_description[:80]}{'...' if len(task_description) > 80 else ''}\n"]
    result.append("## Recommended Servers:\n")
    
    activated = []
    for server, reason in recommendations:
        if server in state.active_servers:
            result.append(f"- **{server}**: Already active ✅")
        else:
            success, _ = enable_server(server)
            if success:
                state.active_servers.add(server)
                tools = get_server_tools(server)
                state.server_tools_cache[server] = tools
                activated.append(server)
                result.append(f"- **{server}**: Activated ✅")
            else:
                result.append(f"- **{server}**: Failed ❌")
        result.append(f"  _{reason}_")
    
    if activated:
        result.append(f"\n📌 **Activated**: {', '.join(activated)}")
        result.append("Tools are now available via MCP gateway.")
    
    return "\n".join(result)


@mcp.tool()
async def deactivate_all() -> str:
    """
    Deactivate all currently active MCP servers.
    
    Use this to clean up after completing tasks.
    
    Returns:
        Deactivation results
    """
    if not state.active_servers:
        return "ℹ️ No servers are currently active."
    
    results = []
    servers = list(state.active_servers)
    
    for server in servers:
        success, output = disable_server(server)
        if success:
            state.active_servers.discard(server)
            state.server_tools_cache.pop(server, None)
            results.append(f"✅ {server}")
        else:
            results.append(f"❌ {server}: {output}")
    
    return "# Deactivation Results\n\n" + "\n".join(results)


@mcp.tool()
async def server_info(server_name: str) -> str:
    """
    Get detailed information about a specific MCP server.
    
    Args:
        server_name: Server to get info about
    
    Returns:
        Detailed server information
    """
    if server_name not in MCP_SERVER_REGISTRY:
        available = ", ".join(sorted(MCP_SERVER_REGISTRY.keys()))
        return f"❌ Unknown server: '{server_name}'\n\nAvailable: {available}"
    
    config = MCP_SERVER_REGISTRY[server_name]
    is_active = server_name in state.active_servers
    
    lines = [
        f"# {server_name}",
        "",
        f"**Status**: {'🟢 Active' if is_active else '⚪ Inactive'}",
        f"**Category**: {config.category}",
        f"**Description**: {config.description}",
        f"**Auth**: {config.auth_type if config.requires_auth else 'None'}",
        f"**Estimated tools**: ~{config.estimated_tools}",
        "",
        f"## Tools Overview",
        f"{config.tools_summary}",
    ]
    
    if is_active:
        tools = state.server_tools_cache.get(server_name, [])
        if tools:
            lines.append(f"\n## Active Tools ({len(tools)})")
            for t in tools:
                lines.append(f"- **{t.get('name', '?')}**: "
                           f"{t.get('description', 'No description')[:80]}")
    else:
        lines.append("\n_Activate to see detailed tool list_")
    
    return "\n".join(lines)


@mcp.tool()
async def sync_state() -> str:
    """
    Synchronize orchestrator state with Docker MCP Toolkit.
    
    Use if state seems out of sync (servers enabled/disabled externally).
    
    Returns:
        Sync results
    """
    enabled = set(get_enabled_servers())
    known = set(MCP_SERVER_REGISTRY.keys())
    
    previous = state.active_servers.copy()
    state.active_servers = enabled & known
    
    # Update caches
    for server in state.active_servers:
        if server not in state.server_tools_cache:
            state.server_tools_cache[server] = get_server_tools(server)
    
    for server in list(state.server_tools_cache.keys()):
        if server not in state.active_servers:
            del state.server_tools_cache[server]
    
    added = state.active_servers - previous
    removed = previous - state.active_servers
    
    lines = ["# 🔄 Sync Complete\n"]
    if added:
        lines.append(f"**Detected**: {', '.join(sorted(added))}")
    if removed:
        lines.append(f"**Removed**: {', '.join(sorted(removed))}")
    lines.append(f"\n**Active**: {', '.join(sorted(state.active_servers)) or 'None'}")
    
    return "\n".join(lines)


# ============================================================================
# Entry Point
# ============================================================================

def main():
    """Main entry point"""
    logger.info("Starting MCP Lazy Orchestrator...")
    
    # Initial sync
    enabled = get_enabled_servers()
    state.active_servers = set(enabled) & set(MCP_SERVER_REGISTRY.keys())
    
    if state.active_servers:
        logger.info(f"Found active: {state.active_servers}")
        for server in state.active_servers:
            state.server_tools_cache[server] = get_server_tools(server)
    
    logger.info("Ready!")
    mcp.run()


if __name__ == "__main__":
    main()
