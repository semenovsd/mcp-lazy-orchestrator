"""MCP Connection Pool for managing server state and CLI tool calls."""

import asyncio
import logging
from typing import Any, Dict, Optional

from .docker_client import DockerMCPClient
from .exceptions import ConnectionError, ServerNotFoundError, ToolNotFoundError

logger = logging.getLogger(__name__)


class ServerInfo:
    """Information about a server."""

    def __init__(self, name: str, is_active: bool = False):
        """
        Initialize server info.

        Args:
            name: Server name
            is_active: Whether server is active
        """
        self.name = name
        self.is_active = is_active
        self.last_checked: Optional[float] = None


class MCPConnectionPool:
    """Pool for managing server state and CLI tool calls."""

    def __init__(
        self,
        docker_client: DockerMCPClient,
        connection_timeout: int = 30,
        reconnect_attempts: int = 3,
        reconnect_delay: int = 1,
        status_check_ttl: int = 30,
    ):
        """
        Initialize connection pool.

        Args:
            docker_client: DockerMCPClient instance
            connection_timeout: Connection timeout in seconds
            reconnect_attempts: Number of reconnection attempts
            reconnect_delay: Delay between reconnection attempts in seconds
            status_check_ttl: TTL for server status cache in seconds
        """
        self.docker_client = docker_client
        self.connection_timeout = connection_timeout
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.status_check_ttl = status_check_ttl

        # Cache server status information
        self._server_info: Dict[str, ServerInfo] = {}
        self._lock = asyncio.Lock()

    async def get_server_info(self, server: str) -> Optional[ServerInfo]:
        """
        Get information about a server, checking status if needed.

        Args:
            server: Server name

        Returns:
            ServerInfo or None if server not found

        Raises:
            ServerNotFoundError: If server is not found
        """
        async with self._lock:
            # Check cache first
            if server in self._server_info:
                info = self._server_info[server]
                # Check if cache is still valid
                import time

                if info.last_checked and (time.time() - info.last_checked) < self.status_check_ttl:
                    return info

            # Check server status
            is_active = await self._check_server_status(server)
            if is_active is None:
                # Server not found
                if server in self._server_info:
                    # Remove from cache
                    self._server_info.pop(server, None)
                raise ServerNotFoundError(server)

            # Update cache
            import time

            info = ServerInfo(server, is_active=is_active)
            info.last_checked = time.time()
            self._server_info[server] = info

            return info

    async def _check_server_status(self, server: str) -> Optional[bool]:
        """
        Check if a server is active.

        Args:
            server: Server name

        Returns:
            True if active, False if inactive, None if not found
        """
        try:
            active_servers = await self.docker_client.get_active_servers()
            return server in active_servers
        except Exception as e:
            logger.error(f"Error checking server status for {server}: {e}")
            return None

    async def call_tool_via_cli(self, tool_name: str, arguments: Dict[str, Any], server: str) -> Any:
        """
        Call a tool through CLI.

        Args:
            tool_name: Tool name
            arguments: Tool arguments
            server: Server name (for validation)

        Returns:
            Tool result

        Raises:
            ConnectionError: If server is not active
            ToolNotFoundError: If tool is not found
        """
        # Check server status first
        server_info = await self.get_server_info(server)
        if not server_info or not server_info.is_active:
            raise ConnectionError(
                server,
                reason="Server is not active. Use start_servers() to enable it.",
            )

        # Call tool through CLI
        try:
            result = await self.docker_client.call_tool(tool_name, arguments)
            return result
        except ToolNotFoundError:
            raise
        except Exception as e:
            # Check if server became inactive
            is_active = await self._check_server_status(server)
            if not is_active:
                raise ConnectionError(
                    server,
                    reason="Server became inactive during tool call",
                ) from e
            raise

    async def invalidate_server_cache(self, server: str):
        """
        Invalidate cache for a server.

        Args:
            server: Server name
        """
        async with self._lock:
            self._server_info.pop(server, None)

    async def invalidate_all_cache(self):
        """Invalidate all server caches."""
        async with self._lock:
            self._server_info.clear()

    def is_server_active(self, server: str) -> bool:
        """
        Check if server is active (from cache, may be stale).

        Args:
            server: Server name

        Returns:
            True if active (cached), False otherwise
        """
        if server not in self._server_info:
            return False
        return self._server_info[server].is_active

    async def ensure_server_active(self, server: str) -> bool:
        """
        Ensure server is active, checking status if needed.

        Args:
            server: Server name

        Returns:
            True if active, False otherwise

        Raises:
            ServerNotFoundError: If server is not found
        """
        server_info = await self.get_server_info(server)
        return server_info.is_active if server_info else False
