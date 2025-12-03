"""
Docker MCP Orchestrator v2.0

Smart orchestrator with automatic discovery, semantic routing, and token optimization.
Reduces token usage by 90%+ through compact catalog and on-demand activation.

Author: semenovsd
License: CC BY-NC 4.0
Repository: https://github.com/semenovsd/docker-mcp-orchestrator
"""

import asyncio
import json
import subprocess
import logging
import time
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field

from mcp.server.fastmcp import FastMCP

# Импорты новых компонентов
from .discovery import ServerDiscovery, ServerMetadata
from .registry import ServerRegistry
from .capabilities import CapabilitiesRegistry
from .router import SemanticRouter
from .analyzer import EnhancedTaskAnalyzer
from .profiles import find_matching_profile, get_all_profiles, SERVER_PROFILES
from .monitor import UsageMonitor
from .telemetry import Telemetry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("docker-mcp-orchestrator")

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
# Initialize Components
# ============================================================================

discovery = ServerDiscovery()
registry = ServerRegistry(discovery)
capabilities_registry = CapabilitiesRegistry()
semantic_router = SemanticRouter(capabilities_registry)
task_analyzer = EnhancedTaskAnalyzer(capabilities_registry, semantic_router)
usage_monitor = UsageMonitor()
telemetry = Telemetry()

# ============================================================================
# Docker MCP CLI Helpers
# ============================================================================

def run_docker_mcp_command(args: list[str], timeout: int = 60) -> tuple[bool, str]:
    """Execute a docker mcp CLI command"""
    cmd = ["docker", "mcp"] + args
    logger.debug(f"Executing: {' '.join(cmd)}")
    
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
    name="Docker MCP Orchestrator",
    version="2.0.0",
    description=(
        "Smart orchestrator for Docker MCP servers. "
        "Reduces token usage by 90%+ through compact catalog and on-demand activation. "
        "Features automatic discovery, semantic routing, and intelligent recommendations."
    )
)


# ============================================================================
# Core Tools
# ============================================================================

@mcp.tool()
async def get_capabilities(
    category_filter: str | None = None,
    include_inactive: bool = True
) -> dict:
    """
    Get compact catalog of all available MCP servers.
    
    **CALL THIS FIRST** when starting a new task to understand 
    what tools are available before activating them.
    
    Returns lightweight summary (~800-1200 tokens) instead of
    full tool definitions (~15000+ tokens).
    
    Args:
        category_filter: Filter by category (e.g., "database", "browser")
        include_inactive: Include inactive servers
    
    Returns:
        Compact catalog with metadata, covers, when_to_use
    """
    # Обновляем реестр если нужно
    await registry.refresh(force=False)
    
    # Получаем все серверы
    servers = registry.get_catalog(
        category_filter=category_filter,
        include_inactive=include_inactive
    )
    
    # Формируем compact catalog
    catalog = {
        "servers": {},
        "categories": {},
        "quick_guide": {},
        "tips": {}
    }
    
    for server_meta in servers:
        # Получаем расширенные метаданные из capabilities registry
        capabilities = capabilities_registry.get(server_meta.name)
        
        if capabilities:
            catalog["servers"][server_meta.name] = {
                "status": "active" if server_meta.status == "enabled" else "available",
                "purpose": capabilities.purpose,
                "covers": capabilities.covers_technologies,
                "when_to_use": capabilities.when_to_use,
                "tools_preview": capabilities.tools_preview,
                "tools_count": server_meta.tool_count,
                "requires_auth": server_meta.requires_auth,
                "related_servers": capabilities.related_servers
            }
        else:
            # Fallback если нет capabilities
            catalog["servers"][server_meta.name] = {
                "status": "active" if server_meta.status == "enabled" else "available",
                "purpose": server_meta.description or "",
                "covers": [],
                "when_to_use": "",
                "tools_preview": [],
                "tools_count": server_meta.tool_count,
                "requires_auth": server_meta.requires_auth,
                "related_servers": []
            }
        
        # Группируем по категориям
        category = server_meta.category
        if category not in catalog["categories"]:
            catalog["categories"][category] = []
        catalog["categories"][category].append(server_meta.name)
    
    # Quick guide
    catalog["quick_guide"] = {
        "documentation": ["context7"],
        "databases": [s for s in catalog["servers"].keys() 
                     if any("database" in str(catalog["servers"][s].get("covers", [])).lower() 
                            or "redis" in str(catalog["servers"][s].get("covers", [])).lower()
                            for _ in [1])],
        "web": ["playwright", "fetch"],
        "version_control": ["github"],
        "system": ["desktop-commander"]
    }
    
    # Tips
    catalog["tips"] = {
        "always_with_code": "Activate 'context7' when writing code with any library",
        "web_scraping": "Use 'playwright' for JS-heavy sites, 'fetch' for simple requests",
        "documentation_first": "Get docs BEFORE writing code - use context7 first"
    }
    
    catalog["total_servers"] = len(catalog["servers"])
    catalog["active_servers"] = len([s for s in catalog["servers"].values() 
                                     if s["status"] == "active"])
    
    return catalog


@mcp.tool()
async def suggest_servers(
    task_description: str,
    auto_activate: bool = False,
    min_confidence: float = 0.5
) -> dict:
    """
    Analyze task and recommend appropriate MCP servers.
    
    Uses both keyword matching and semantic analysis for accuracy.
    
    Args:
        task_description: What you want to accomplish
        auto_activate: If True, automatically activate recommended servers
        min_confidence: Minimum confidence score (0.0-1.0)
    
    Returns:
        Recommendations with confidence scores, reasons, and optional tools
    """
    # 1. Анализ задачи
    analysis = task_analyzer.analyze_task(task_description)
    
    # 2. Формируем рекомендации
    recommended_servers = []
    
    # Required servers
    for server in analysis.required_servers:
        recommended_servers.append({
            "server": server,
            "confidence": analysis.confidence,
            "reason": f"Required for: {task_description[:50]}"
        })
    
    # Recommended servers
    for server in analysis.recommended_servers:
        recommended_servers.append({
            "server": server,
            "confidence": 0.8,  # Recommended обычно ниже
            "reason": f"Recommended for: {task_description[:50]}"
        })
    
    # Фильтруем по min_confidence
    recommended_servers = [r for r in recommended_servers if r["confidence"] >= min_confidence]
    
    # 3. Опциональная активация
    activated = []
    tools = None
    
    if auto_activate:
        servers_to_activate = [r["server"] for r in recommended_servers 
                              if r["confidence"] >= 0.7]
        result = await activate_servers(servers_to_activate, 
                                       reason=f"Auto from suggest_servers: {task_description}")
        activated = result.get("activated", [])
        tools = result.get("tools", [])
    
    return {
        "task_analysis": {
            "detected_technologies": analysis.detected_technologies,
            "confidence": analysis.confidence
        },
        "recommended": recommended_servers,
        "optional": [r for r in recommended_servers if r["confidence"] < 0.7],
        "activated": activated,
        "tools": tools,
        "estimated_tokens": analysis.estimated_tokens
    }


@mcp.tool()
async def activate_servers(
    servers: list[str],
    reason: str = "",
    auto_activate_deps: bool = True
) -> dict:
    """
    Activate specified MCP servers and return their full tool definitions.
    
    Args:
        servers: List of server names to activate
        reason: Why these servers are needed (for logging/telemetry)
        auto_activate_deps: Automatically activate dependencies (e.g., context7)
    
    Returns:
        Full tool definitions for activated servers
    """
    activated = []
    failed = []
    all_tools = []
    
    # Определяем зависимости
    servers_to_activate = list(servers)
    if auto_activate_deps:
        for server in servers:
            caps = capabilities_registry.get(server)
            if caps:
                deps = caps.related_servers
                for dep in deps:
                    if dep not in servers_to_activate:
                        servers_to_activate.append(dep)
    
    # Активируем каждый сервер
    for server_name in servers_to_activate:
        start_time = time.time()
        
        if server_name in state.active_servers:
            # Уже активен, получаем tools из кэша
            tools = state.server_tools_cache.get(server_name, [])
            all_tools.append({
                "server": server_name,
                "tools": tools,
                "status": "already_active"
            })
            continue
        
        # Активируем через Docker MCP CLI
        success, output = enable_server(server_name)
        latency_ms = (time.time() - start_time) * 1000
        
        if success:
            state.active_servers.add(server_name)
            tools = get_server_tools(server_name)
            state.server_tools_cache[server_name] = tools
            
            all_tools.append({
                "server": server_name,
                "tools": tools,
                "status": "activated"
            })
            
            activated.append(server_name)
            usage_monitor.track_activation(server_name)
            
            # Telemetry
            telemetry.log_activation(server_name, reason, success=True, latency_ms=latency_ms)
        else:
            failed.append(server_name)
            telemetry.log_activation(server_name, reason, success=False, 
                                   latency_ms=latency_ms, error=output)
    
    # Формируем ответ
    total_tools = sum(len(t["tools"]) for t in all_tools)
    estimated_tokens = total_tools * 150  # ~150 токенов на tool definition
    
    return {
        "activated": activated,
        "failed": failed,
        "tools": all_tools,
        "total_tools": total_tools,
        "estimated_tokens": estimated_tokens,
        "message": f"Activated {len(activated)} servers, {total_tools} tools available"
    }


@mcp.tool()
async def activate_profile(profile_name: str) -> dict:
    """
    Activate a predefined server profile for common task types.
    
    Profiles are optimized combinations of servers for typical workflows.
    
    Args:
        profile_name: Name of profile (web-development, data-science, etc.)
    
    Returns:
        Activation results
    """
    if profile_name not in SERVER_PROFILES:
        available = ", ".join(SERVER_PROFILES.keys())
        return {
            "error": f"Unknown profile: {profile_name}",
            "available_profiles": list(SERVER_PROFILES.keys())
        }
    
    profile = SERVER_PROFILES[profile_name]
    
    # Активируем через activate_servers
    result = await activate_servers(
        profile.servers,
        reason=f"Profile: {profile_name}",
        auto_activate_deps=True
    )
    
    result["profile"] = {
        "name": profile_name,
        "description": profile.description,
        "estimated_tokens": profile.estimated_tokens
    }
    
    return result


@mcp.tool()
async def activate_for_task(
    task_description: str,
    auto_activate_deps: bool = True,
    use_profiles: bool = True
) -> dict:
    """
    Smart activation of servers for a task.
    
    Analyzes task, determines optimal servers, and activates them.
    
    Args:
        task_description: Description of what you want to accomplish
        auto_activate_deps: Automatically activate dependencies
        use_profiles: Use predefined profiles if task matches
    
    Returns:
        Activation results with recommendations
    """
    # 1. Проверка профилей
    if use_profiles:
        matching_profile = find_matching_profile(task_description)
        if matching_profile and matching_profile.auto_activate:
            return await activate_profile(matching_profile.name)
    
    # 2. Анализ задачи
    analysis = task_analyzer.analyze_task(task_description)
    
    if not analysis.required_servers and not analysis.recommended_servers:
        return {
            "error": "No servers detected for this task",
            "suggestion": "Use get_capabilities() to see available servers"
        }
    
    # 3. Активация серверов
    all_servers = analysis.required_servers + analysis.recommended_servers
    activation_order = analysis.activation_order
    
    result = await activate_servers(
        activation_order,
        reason=f"Task: {task_description}",
        auto_activate_deps=auto_activate_deps
    )
    
    result["analysis"] = {
        "confidence": analysis.confidence,
        "detected_technologies": analysis.detected_technologies,
        "estimated_tokens": analysis.estimated_tokens
    }
    
    return result


@mcp.tool()
async def deactivate_servers(servers: list[str] | None = None) -> dict:
    """
    Deactivate MCP servers to free resources.
    
    Args:
        servers: Specific servers to deactivate, or None for all
    """
    if servers is None:
        servers = list(state.active_servers)
    
    deactivated = []
    failed = []
    
    for server in servers:
        if server not in state.active_servers:
            continue
        
        success, output = disable_server(server)
        if success:
            state.active_servers.discard(server)
            state.server_tools_cache.pop(server, None)
            deactivated.append(server)
        else:
            failed.append(server)
    
    return {
        "deactivated": deactivated,
        "failed": failed,
        "still_active": list(state.active_servers),
        "message": f"Deactivated {len(deactivated)} servers" if deactivated else "No servers to deactivate"
    }


@mcp.tool()
async def get_status() -> dict:
    """Get current orchestrator state"""
    active = state.active_servers
    total_tools = sum(len(state.server_tools_cache.get(s, [])) for s in active)
    
    all_servers_count = len(registry.servers)
    
    return {
        "active_servers": list(active),
        "active_tools_count": total_tools,
        "available_servers": all_servers_count,
        "estimated_tokens": {
            "current": total_tools * 150,
            "if_all_active": sum(
                registry.get_server(s).tool_count * 150 
                for s in registry.servers.keys()
            ) if registry.servers else 0
        },
        "last_sync": registry.last_discovery.isoformat() if registry.last_discovery else None
    }


@mcp.tool()
async def monitor_usage(show_recommendations: bool = True) -> dict:
    """Show usage statistics and recommendations"""
    stats = usage_monitor.get_usage_stats()
    active = state.active_servers
    
    result = {
        "active_servers": len(active),
        "total_tools_loaded": sum(len(state.server_tools_cache.get(s, [])) for s in active),
        "server_usage": [
            {
                "server": server,
                "uses": count,
                "status": "active" if server in active else "inactive"
            }
            for server, count in sorted(stats.items(), key=lambda x: x[1], reverse=True)
        ]
    }
    
    if show_recommendations:
        recommendations = usage_monitor.recommend_deactivation(active)
        if recommendations:
            result["recommendations"] = {
                "deactivate": recommendations,
                "reason": "Unused for >10 minutes"
            }
    
    return result


@mcp.tool()
async def optimize_servers(
    keep_active: list[str] | None = None
) -> dict:
    """Optimize active servers by deactivating unused ones"""
    recommendations = usage_monitor.recommend_deactivation(state.active_servers)
    
    if keep_active:
        recommendations = [s for s in recommendations if s not in keep_active]
    
    if not recommendations:
        return {
            "message": "No servers to optimize",
            "current_tokens": sum(
                len(state.server_tools_cache.get(s, [])) * 150 
                for s in state.active_servers
            )
        }
    
    deactivated = []
    for server in recommendations:
        result = await deactivate_servers([server])
        if server in result.get("deactivated", []):
            deactivated.append(server)
    
    current_tokens = sum(
        len(state.server_tools_cache.get(s, [])) * 150 
        for s in state.active_servers
    )
    
    return {
        "deactivated": deactivated,
        "current_active": len(state.active_servers),
        "estimated_tokens": current_tokens,
        "savings": len(deactivated) * 1000  # Примерная экономия
    }


# ============================================================================
# Legacy Tools (для обратной совместимости)
# ============================================================================

@mcp.tool()
async def list_available_servers() -> str:
    """
    List all available MCP servers (legacy, use get_capabilities for compact catalog).
    
    Returns:
        Formatted catalog of available MCP servers
    """
    await registry.refresh(force=False)
    servers = registry.get_catalog(include_inactive=True)
    
    result = ["# 📦 Available MCP Servers\n"]
    
    # Group by category
    categories: dict[str, list[ServerMetadata]] = {}
    for server in servers:
        if server.category not in categories:
            categories[server.category] = []
        categories[server.category].append(server)
    
    total_tools = 0
    for category, category_servers in sorted(categories.items()):
        result.append(f"\n## {category.replace('_', ' ').title()}\n")
        for server in category_servers:
            status = "🟢 ACTIVE" if server.status == "enabled" else "⚪"
            auth = f" 🔐 {server.auth_type}" if server.requires_auth else ""
            total_tools += server.tool_count
            
            result.append(f"**{server.name}** [{status}]{auth}")
            if server.description:
                result.append(f"  {server.description}")
            result.append(f"  _~{server.tool_count} tools_")
            result.append("")
    
    result.append(f"\n---\n**Total available**: {len(servers)} servers, "
                  f"~{total_tools} tools")
    result.append(f"**Currently active**: {len(state.active_servers)} servers")
    result.append("\n💡 Use `get_capabilities()` for compact catalog with technology coverage.")
    
    return "\n".join(result)


@mcp.tool()
async def activate_server(server_name: str, reason: str = "") -> str:
    """
    Activate a single MCP server (legacy, use activate_servers for multiple).
    
    Args:
        server_name: Server to activate
        reason: Why this server is needed
    
    Returns:
        Status message
    """
    result = await activate_servers([server_name], reason=reason, auto_activate_deps=True)
    
    if result.get("activated"):
        server = result["activated"][0]
        tools_info = result["tools"][0] if result["tools"] else {}
        tools = tools_info.get("tools", [])
        
        lines = [
            f"✅ **{server}** activated!",
            f"",
            f"**Available tools ({len(tools)})**:"
        ]
        
        for t in tools[:12]:
            desc = t.get('description', '')[:60]
            lines.append(f"- `{t.get('name')}`: {desc}")
        if len(tools) > 12:
            lines.append(f"- _...and {len(tools) - 12} more_")
        
        lines.append(f"\n📌 Tools from '{server}' are now available via MCP gateway.")
        return "\n".join(lines)
    else:
        return f"❌ Failed to activate '{server_name}': {result.get('failed', ['unknown error'])}"


@mcp.tool()
async def deactivate_server(server_name: str) -> str:
    """Deactivate a single server (legacy)"""
    result = await deactivate_servers([server_name])
    if server_name in result.get("deactivated", []):
        return f"✅ Server '{server_name}' deactivated."
    else:
        return f"❌ Failed to deactivate '{server_name}'"


@mcp.tool()
async def deactivate_all() -> str:
    """Deactivate all servers (legacy)"""
    result = await deactivate_servers()
    deactivated = result.get("deactivated", [])
    if deactivated:
        return f"✅ Deactivated {len(deactivated)} servers: {', '.join(deactivated)}"
    else:
        return "ℹ️ No servers to deactivate."


@mcp.tool()
async def server_info(server_name: str) -> str:
    """Get detailed information about a server"""
    await registry.refresh(force=False)
    server_meta = registry.get_server(server_name)
    
    if not server_meta:
        available = ", ".join(sorted(registry.servers.keys()))
        return f"❌ Server '{server_name}' not found.\n\nAvailable: {available}"
    
    caps = capabilities_registry.get(server_name)
    is_active = server_name in state.active_servers
    
    lines = [
        f"# {server_name}",
        "",
        f"**Status**: {'🟢 Active' if is_active else '⚪ Inactive'}",
        f"**Category**: {server_meta.category}",
        f"**Tool Count**: ~{server_meta.tool_count} tools",
    ]
    
    if caps:
        if caps.purpose:
            lines.append(f"\n**Purpose**: {caps.purpose}")
        if caps.covers_technologies:
            lines.append(f"\n**Covers Technologies**: {', '.join(caps.covers_technologies[:10])}")
            if len(caps.covers_technologies) > 10:
                lines.append(f"  _...and {len(caps.covers_technologies) - 10} more_")
        if caps.when_to_use:
            lines.append(f"\n**When to Use**: {caps.when_to_use}")
    elif server_meta.description:
        lines.append(f"\n**Description**: {server_meta.description}")
    
    if server_meta.requires_auth:
        lines.append(f"\n**Authentication**: 🔐 {server_meta.auth_type or 'Required'}")
    
    if is_active:
        tools = state.server_tools_cache.get(server_name, [])
        if tools:
            lines.append(f"\n## Active Tools ({len(tools)})")
            for t in tools[:10]:
                lines.append(f"- **{t.get('name', '?')}**: {t.get('description', 'No description')[:80]}")
            if len(tools) > 10:
                lines.append(f"- _...and {len(tools) - 10} more_")
    
    lines.append("\n---")
    lines.append(f"💡 Use `activate_servers([\"{server_name}\"])` to activate and get tools.")
    
    return "\n".join(lines)


@mcp.tool()
async def sync_state() -> str:
    """Synchronize orchestrator state with Docker MCP Toolkit"""
    await registry.refresh(force=True)
    enabled = set(get_enabled_servers())
    known = set(registry.servers.keys())
    
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

async def initialize():
    """Инициализация всех компонентов"""
    logger.info("Initializing Smart MCP Orchestrator v2.0...")
    
    # 1. Обнаружение серверов
    await registry.refresh(force=True)
    logger.info(f"Discovered {len(registry.servers)} servers")
    
    # 2. Загрузка capabilities
    logger.info(f"Loaded capabilities for {len(capabilities_registry.registry)} servers")
    
    # 3. Синхронизация состояния
    enabled = get_enabled_servers()
    state.active_servers = set(enabled) & set(registry.servers.keys())
    
    if state.active_servers:
        logger.info(f"Found active: {state.active_servers}")
        for server in state.active_servers:
            state.server_tools_cache[server] = get_server_tools(server)
            usage_monitor.track_activation(server)
    
    logger.info("Ready!")


def main():
    """Main entry point"""
    asyncio.run(initialize())
    mcp.run()


if __name__ == "__main__":
    main()
