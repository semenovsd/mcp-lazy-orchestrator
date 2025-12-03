"""Main MCP Server for Orchestrator."""

import asyncio
import logging
from typing import Any, Dict

import yaml
from mcp.server import Server
from mcp.types import Tool

from .cache import MetadataCache
from .connection_pool import MCPConnectionPool
from .docker_client import DockerMCPClient
from .exceptions import DockerMCPError
from .prompt_manager import PromptManager
from .proxy import ToolProxy

# Import all tools
from .tools.config.config_get import get_tool as config_get_tool, handle_tool as handle_config_get
from .tools.config.config_set import get_tool as config_set_tool, handle_tool as handle_config_set
from .tools.config.secret_list import get_tool as secret_list_tool, handle_tool as handle_secret_list
from .tools.config.secret_remove import (
    get_tool as secret_remove_tool,
    handle_tool as handle_secret_remove,
)
from .tools.config.secret_set import get_tool as secret_set_tool, handle_tool as handle_secret_set
from .tools.info.get_info import get_tool as get_info_tool, handle_tool as handle_get_info
from .tools.info.get_tools import get_tool as get_tools_tool, handle_tool as handle_get_tools
from .tools.proxy.call_tool import get_tool as call_tool_tool, handle_tool as handle_call_tool
from .tools.proxy.list_active_tools import (
    get_tool as list_active_tools_tool,
    handle_tool as handle_list_active_tools,
)
from .tools.servers.get_active import (
    get_tool as get_active_tool,
    handle_tool as handle_get_active,
)
from .tools.servers.list_catalog import (
    get_tool as list_catalog_tool,
    handle_tool as handle_list_catalog,
)
from .tools.servers.list_installed import (
    get_tool as list_installed_tool,
    handle_tool as handle_list_installed,
)
from .tools.servers.start import get_tool as start_tool, handle_tool as handle_start
from .tools.servers.stop import get_tool as stop_tool, handle_tool as handle_stop

logger = logging.getLogger(__name__)


class OrchestratorServer:
    """Main Orchestrator MCP Server."""

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize Orchestrator Server.

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = self._load_config(config_path)

        # Initialize components
        cache_config = self.config.get("orchestrator", {}).get("cache", {})
        self.cache = MetadataCache(
            servers_ttl=cache_config.get("servers_ttl", 300),
            tools_ttl=cache_config.get("tools_ttl", 600),
            prompts_ttl=cache_config.get("prompts_ttl", 0),
        )

        docker_config = self.config.get("orchestrator", {}).get("docker_mcp", {})
        self.docker_client = DockerMCPClient(
            catalog=docker_config.get("catalog", "docker-mcp"),
            command_timeout=docker_config.get("command_timeout", 30),
        )

        proxy_config = self.config.get("orchestrator", {}).get("proxy", {})
        self.connection_pool = MCPConnectionPool(
            docker_client=self.docker_client,
            connection_timeout=proxy_config.get("connection_timeout", 30),
            reconnect_attempts=proxy_config.get("reconnect_attempts", 3),
            reconnect_delay=proxy_config.get("reconnect_delay", 1),
            status_check_ttl=proxy_config.get("status_check_ttl", 30),
        )

        self.proxy = ToolProxy(self.connection_pool)
        self.prompt_manager = PromptManager(self.cache, self.docker_client)

        # Initialize MCP Server
        self.server = Server("docker-mcp-orchestrator")

        # Register tools
        self._register_tools()

        # Register handlers
        self._register_handlers()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def _register_tools(self):
        """Register all tools with MCP server."""
        # Tools will be registered via handlers
        pass

    def _register_handlers(self):
        """Register tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available tools."""
            return [
                # Server management
                list_installed_tool(),
                list_catalog_tool(),
                start_tool(),
                stop_tool(),
                get_active_tool(),
                # Information
                get_tools_tool(),
                get_info_tool(),
                # Configuration
                config_set_tool(),
                config_get_tool(),
                secret_set_tool(),
                secret_list_tool(),
                secret_remove_tool(),
                # Proxy
                call_tool_tool(),
                list_active_tools_tool(),
            ]

        @self.server.call_tool()
        async def handle_tool_call(name: str, arguments: Dict[str, Any]) -> list[dict[str, Any]]:
            """Handle tool calls."""
            try:
                # Route to appropriate handler
                if name == "list_installed_servers":
                    result = await handle_list_installed(
                        arguments, self.docker_client, self.cache
                    )
                elif name == "list_catalog_servers":
                    result = await handle_list_catalog(
                        arguments, self.docker_client, self.cache
                    )
                elif name == "start_servers":
                    result = await handle_start(
                        arguments,
                        self.docker_client,
                        self.cache,
                        self.proxy,
                        self.prompt_manager,
                    )
                elif name == "stop_servers":
                    result = await handle_stop(arguments, self.docker_client, self.proxy)
                elif name == "get_active_servers":
                    result = await handle_get_active(
                        arguments, self.docker_client, self.proxy
                    )
                elif name == "get_server_tools":
                    result = await handle_get_tools(
                        arguments, self.docker_client, self.cache
                    )
                elif name == "get_server_info":
                    result = await handle_get_info(
                        arguments, self.docker_client, self.cache
                    )
                elif name == "config_set":
                    result = await handle_config_set(arguments, self.docker_client)
                elif name == "config_get":
                    result = await handle_config_get(arguments, self.docker_client)
                elif name == "secret_set":
                    result = await handle_secret_set(arguments, self.docker_client)
                elif name == "secret_list":
                    result = await handle_secret_list(arguments, self.docker_client)
                elif name == "secret_remove":
                    result = await handle_secret_remove(arguments, self.docker_client)
                elif name == "call_tool":
                    result = await handle_call_tool(arguments, self.proxy)
                elif name == "list_active_tools":
                    result = await handle_list_active_tools(arguments, self.proxy)
                else:
                    return [
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Unknown tool: {name}",
                                }
                            ],
                            "isError": True,
                        }
                    ]

                # Format result for MCP
                import json
                from mcp.types import TextContent

                # MCP expects list of CallToolResult with content array
                if isinstance(result, list):
                    # Convert list items to JSON strings
                    formatted = []
                    for item in result:
                        text = json.dumps(item, indent=2) if isinstance(item, (dict, list)) else str(item)
                        formatted.append(
                            {
                                "content": [{"type": "text", "text": text}],
                                "isError": False,
                            }
                        )
                    return formatted
                elif isinstance(result, dict):
                    # Convert dict to JSON string
                    text = json.dumps(result, indent=2)
                    return [
                        {
                            "content": [{"type": "text", "text": text}],
                            "isError": False,
                        }
                    ]
                else:
                    return [
                        {
                            "content": [{"type": "text", "text": str(result)}],
                            "isError": False,
                        }
                    ]

            except DockerMCPError as e:
                # Custom exceptions with details
                error_msg = str(e)
                if e.details:
                    error_msg += f"\nDetails: {json.dumps(e.details, indent=2)}"
                logger.error(f"Error handling tool {name}: {error_msg}", exc_info=True)
                return [
                    {
                        "content": [{"type": "text", "text": error_msg}],
                        "isError": True,
                    }
                ]
            except Exception as e:
                logger.error(f"Error handling tool {name}: {e}", exc_info=True)
                return [
                    {
                        "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                        "isError": True,
                    }
                ]

    async def run(self):
        """Run the server."""
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
            )


async def main():
    """Main entry point."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create and run server
    server = OrchestratorServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
