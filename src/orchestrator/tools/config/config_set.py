"""Config set tool."""

import logging
from typing import Any

from mcp.types import Tool

from ...docker_client import DockerMCPClient
from ...exceptions import CommandError

logger = logging.getLogger(__name__)


def get_tool() -> Tool:
    """Get config_set tool definition."""
    return Tool(
        name="config_set",
        description="Set configuration for MCP servers (e.g., database URLs, API endpoints)",
        inputSchema={
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "description": "Server name (optional, for server-specific config)",
                },
                "config": {
                    "type": "object",
                    "description": "Configuration dictionary (key-value pairs)",
                },
            },
            "required": ["config"],
        },
    )


async def handle_tool(
    arguments: dict[str, Any],
    docker_client: DockerMCPClient,
) -> dict[str, Any]:
    """
    Handle config_set tool call.

    Args:
        arguments: Tool arguments
        docker_client: Docker MCP Client

    Returns:
        Result dictionary
    """
    config = arguments.get("config", {})
    server = arguments.get("server")

    if not config:
        return {"status": "error", "error": "Config is required"}

    # Note: Docker MCP config write may need server-specific handling
    # For now, we'll write to global config
    try:
        await docker_client.config_write(config)
        return {
            "status": "success",
            "server": server,
            "config": config,
        }
    except CommandError as e:
        logger.error(f"Failed to write configuration: {e}")
        return {
            "status": "error",
            "error": f"Failed to write configuration: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Unexpected error writing configuration: {e}", exc_info=True)
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
        }
