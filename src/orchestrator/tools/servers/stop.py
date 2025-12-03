"""Stop servers tool."""

import logging
from typing import Any

from mcp.types import Tool

from ...docker_client import DockerMCPClient
from ...exceptions import CommandError
from ...proxy import ToolProxy

logger = logging.getLogger(__name__)


def get_tool() -> Tool:
    """Get stop_servers tool definition."""
    return Tool(
        name="stop_servers",
        description="Stop specified MCP servers and disable their tools",
        inputSchema={
            "type": "object",
            "properties": {
                "servers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of server names to stop",
                }
            },
            "required": ["servers"],
        },
    )


async def handle_tool(
    arguments: dict[str, Any],
    docker_client: DockerMCPClient,
    proxy: ToolProxy,
) -> dict[str, Any]:
    """
    Handle stop_servers tool call.

    Args:
        arguments: Tool arguments
        docker_client: Docker MCP Client
        proxy: Tool proxy

    Returns:
        Result dictionary
    """
    servers = arguments.get("servers", [])
    if not servers:
        return {"status": "error", "error": "No servers specified", "servers": []}

    # Unregister from proxy first
    for server in servers:
        proxy.unregister_server(server)

    # Disable servers through Docker MCP Toolkit
    try:
        await docker_client.disable_servers(servers)
        return {"status": "success", "servers": servers}
    except CommandError as e:
        logger.error(f"Failed to disable servers: {e}")
        return {
            "status": "error",
            "error": f"Failed to disable servers: {str(e)}",
            "servers": servers,
        }
    except Exception as e:
        logger.error(f"Unexpected error disabling servers: {e}", exc_info=True)
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "servers": servers,
        }
