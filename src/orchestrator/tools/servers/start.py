"""Start servers tool."""

import logging
from typing import Any

from mcp.types import Tool

from ...cache import MetadataCache
from ...docker_client import DockerMCPClient
from ...exceptions import CommandError, ServerNotFoundError
from ...models import StartServersResult
from ...prompt_manager import PromptManager
from ...proxy import ToolProxy

logger = logging.getLogger(__name__)


def get_tool() -> Tool:
    """Get start_servers tool definition."""
    return Tool(
        name="start_servers",
        description="Start specified MCP servers and enable their tools. Returns list of available tools and prompts.",
        inputSchema={
            "type": "object",
            "properties": {
                "servers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of server names to start",
                }
            },
            "required": ["servers"],
        },
    )


async def handle_tool(
    arguments: dict[str, Any],
    docker_client: DockerMCPClient,
    cache: MetadataCache,
    proxy: ToolProxy,
    prompt_manager: PromptManager,
) -> dict[str, Any]:
    """
    Handle start_servers tool call.

    Args:
        arguments: Tool arguments
        docker_client: Docker MCP Client
        cache: Metadata cache
        proxy: Tool proxy
        prompt_manager: Prompt manager

    Returns:
        StartServersResult as dictionary
    """
    servers = arguments.get("servers", [])
    if not servers:
        return {
            "status": "error",
            "error": "No servers specified",
            "servers": [],
            "tools": [],
            "prompts": {},
        }

    # Enable servers through Docker MCP Toolkit
    try:
        await docker_client.enable_servers(servers)
    except CommandError as e:
        return {
            "status": "error",
            "error": f"Failed to enable servers: {str(e)}",
            "servers": [],
            "tools": [],
            "prompts": {},
        }
    except Exception as e:
        logger.error(f"Unexpected error enabling servers: {e}", exc_info=True)
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "servers": [],
            "tools": [],
            "prompts": {},
        }

    # Get tools for each server and register in proxy
    all_tools = []
    errors = {}
    successful_servers = []

    for server in servers:
        try:
            # Get tools from server
            async def fetch_tools():
                return await docker_client.get_server_tools(server)

            tools = await cache.get_server_tools(server, fetch_tools)

            if tools:
                # Register tools in proxy
                proxy.register_tools(server, tools)
                all_tools.extend(tools)
                successful_servers.append(server)
            else:
                errors[server] = "No tools found or server not responding"
        except ServerNotFoundError as e:
            errors[server] = f"Server not found: {str(e)}"
            logger.error(f"Server not found: {server}")
        except CommandError as e:
            errors[server] = f"Command error: {str(e)}"
            logger.error(f"Command error for server {server}: {e}")
        except Exception as e:
            errors[server] = f"Unexpected error: {str(e)}"
            logger.error(f"Error starting server {server}: {e}", exc_info=True)

    # Get prompts for successful servers
    prompts = await prompt_manager.get_prompts_for_servers(successful_servers)

    # Format tools for response
    tools_data = [
        {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.inputSchema,
        }
        for tool in all_tools
    ]

    result = {
        "status": "success" if successful_servers else "partial",
        "servers": successful_servers,
        "tools": tools_data,
        "prompts": prompts,
    }

    if errors:
        result["errors"] = errors

    return result
