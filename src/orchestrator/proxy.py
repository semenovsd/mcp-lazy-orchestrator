"""Proxy layer for routing tool calls to MCP servers."""

import logging
from typing import Any, Dict, List, Optional

from .exceptions import ConnectionError, ToolNotFoundError
from .models import Tool

logger = logging.getLogger(__name__)


class ToolProxy:
    """Proxy for routing tool calls to appropriate MCP servers."""

    def __init__(self, connection_pool):
        """
        Initialize tool proxy.

        Args:
            connection_pool: MCPConnectionPool instance
        """
        self._pool = connection_pool
        self._tool_to_server: Dict[str, str] = {}
        self._server_tools: Dict[str, List[Tool]] = {}

    def register_tools(self, server: str, tools: List[Tool]):
        """
        Register tools for a server.

        Args:
            server: Server name
            tools: List of tools provided by the server
        """
        self._server_tools[server] = tools
        for tool in tools:
            self._tool_to_server[tool.name] = server
        logger.info(f"Registered {len(tools)} tools for server {server}")

    def unregister_server(self, server: str):
        """
        Unregister all tools for a server.

        Args:
            server: Server name
        """
        if server in self._server_tools:
            tools = self._server_tools[server]
            for tool in tools:
                self._tool_to_server.pop(tool.name, None)
            self._server_tools.pop(server, None)
            # Invalidate server cache
            self._pool.invalidate_server_cache(server)
            logger.info(f"Unregistered server {server}")

    def get_server_for_tool(self, tool_name: str) -> Optional[str]:
        """
        Get server that provides a specific tool.

        Args:
            tool_name: Tool name

        Returns:
            Server name or None if not found
        """
        return self._tool_to_server.get(tool_name)

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> tuple[Any, Optional[str]]:
        """
        Call a tool through proxy.

        Args:
            tool_name: Tool name
            arguments: Tool arguments

        Returns:
            Tuple of (result, error_message)
        """
        server = self.get_server_for_tool(tool_name)
        if not server:
            error = f"Tool {tool_name} not found in any active server"
            logger.error(error)
            return None, error

        try:
            # Call tool through CLI via connection pool
            result = await self._pool.call_tool_via_cli(tool_name, arguments, server)
            return result, None
        except ToolNotFoundError as e:
            error = str(e)
            logger.error(error)
            return None, error
        except ConnectionError as e:
            error = str(e)
            logger.error(error)
            # Invalidate server cache on connection error
            await self._pool.invalidate_server_cache(server)
            return None, error
        except Exception as e:
            error = f"Error calling tool {tool_name} on server {server}: {str(e)}"
            logger.error(error, exc_info=True)
            return None, error

    def list_active_tools(self) -> List[Tool]:
        """
        List all active tools from all registered servers.

        Returns:
            List of all active tools
        """
        all_tools = []
        for tools in self._server_tools.values():
            all_tools.extend(tools)
        return all_tools

    def get_server_tools(self, server: str) -> List[Tool]:
        """
        Get tools for a specific server.

        Args:
            server: Server name

        Returns:
            List of tools
        """
        return self._server_tools.get(server, [])

    def list_servers(self) -> List[str]:
        """
        List all registered servers.

        Returns:
            List of server names
        """
        return list(self._server_tools.keys())
