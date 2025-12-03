"""Docker MCP Toolkit client."""

import json
import logging
from typing import Any, Dict, List, Optional

from .exceptions import CommandError, ParseError, ServerNotFoundError, ToolNotFoundError
from .models import Server, ServerMetadata, Tool
from .utils import parse_json_output, run_command

logger = logging.getLogger(__name__)


class DockerMCPClient:
    """Client for interacting with Docker MCP Toolkit."""

    def __init__(self, catalog: str = "docker-mcp", command_timeout: int = 30):
        """
        Initialize Docker MCP Client.

        Args:
            catalog: Default catalog name
            command_timeout: Command timeout in seconds
        """
        self.catalog = catalog
        self.command_timeout = command_timeout

    async def get_catalog_servers(self, catalog: Optional[str] = None) -> List[ServerMetadata]:
        """
        Get list of servers from catalog.

        Args:
            catalog: Catalog name (uses default if None)

        Returns:
            List of server metadata

        Raises:
            CommandError: If command fails
            ParseError: If parsing fails
        """
        catalog_name = catalog or self.catalog
        cmd = ["docker", "mcp", "catalog", "show", catalog_name, "--format=json"]
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            error_msg = stdout if stdout else "Unknown error"
            raise CommandError(
                cmd,
                return_code,
                stderr=error_msg,
                details={"catalog": catalog_name},
            )

        data = parse_json_output(stdout)
        if not data:
            raise ParseError(
                f"catalog show output for {catalog_name}",
                reason="Empty or invalid JSON",
                details={"stdout": stdout},
            )

        servers = []
        # Parse catalog structure (structure may vary)
        try:
            if isinstance(data, dict):
                if "servers" in data:
                    for server_name, server_data in data["servers"].items():
                        if isinstance(server_data, dict):
                            servers.append(self._parse_server_metadata(server_name, server_data))
                elif "items" in data:
                    # Alternative structure with items array
                    for item in data["items"]:
                        if isinstance(item, dict):
                            name = item.get("name", item.get("id", ""))
                            servers.append(self._parse_server_metadata(name, item))
                else:
                    # Try to parse as flat structure
                    for key, value in data.items():
                        if isinstance(value, dict):
                            servers.append(self._parse_server_metadata(key, value))
            elif isinstance(data, list):
                # Direct list of servers
                for item in data:
                    if isinstance(item, dict):
                        name = item.get("name", item.get("id", ""))
                        servers.append(self._parse_server_metadata(name, item))
        except Exception as e:
            raise ParseError(
                f"catalog show output for {catalog_name}",
                reason=str(e),
                details={"data": data},
            ) from e

        return servers

    async def get_installed_servers(self) -> List[str]:
        """
        Get list of installed server names.

        Returns:
            List of installed server names
        """
        # Get servers from catalog (installed servers are in catalog)
        servers = await self.get_catalog_servers()
        return [s.name for s in servers]

    async def get_active_servers(self) -> List[str]:
        """
        Get list of active (enabled) servers.

        Returns:
            List of active server names

        Raises:
            CommandError: If command fails
            ParseError: If parsing fails
        """
        cmd = ["docker", "mcp", "server", "ls", "--json"]
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            error_msg = stdout if stdout else "Unknown error"
            raise CommandError(cmd, return_code, stderr=error_msg)

        data = parse_json_output(stdout)
        if not data:
            # Empty list is valid - no active servers
            return []

        # Parse server list structure
        try:
            if isinstance(data, list):
                servers = []
                for s in data:
                    if isinstance(s, dict):
                        # Try different possible keys
                        name = s.get("name") or s.get("id") or s.get("server")
                        if name:
                            servers.append(name)
                    elif isinstance(s, str):
                        servers.append(s)
                return servers
            elif isinstance(data, dict):
                if "servers" in data:
                    servers = []
                    for s in data["servers"]:
                        if isinstance(s, dict):
                            name = s.get("name") or s.get("id") or s.get("server")
                            if name:
                                servers.append(name)
                        elif isinstance(s, str):
                            servers.append(s)
                    return servers
                elif "enabled" in data:
                    enabled = data["enabled"]
                    if isinstance(enabled, list):
                        return enabled
                    elif isinstance(enabled, dict):
                        return list(enabled.keys())
                elif "active" in data:
                    active = data["active"]
                    if isinstance(active, list):
                        return active
        except Exception as e:
            raise ParseError("server ls output", reason=str(e), details={"data": data}) from e

        return []

    async def enable_servers(self, servers: List[str]) -> bool:
        """
        Enable (start) servers.

        Args:
            servers: List of server names to enable

        Returns:
            True if successful

        Raises:
            CommandError: If command fails
        """
        if not servers:
            return True

        cmd = ["docker", "mcp", "server", "enable"] + servers
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            error_msg = stdout if stdout else "Unknown error"
            raise CommandError(
                cmd,
                return_code,
                stderr=error_msg,
                details={"servers": servers},
            )

        return True

    async def disable_servers(self, servers: List[str]) -> bool:
        """
        Disable (stop) servers.

        Args:
            servers: List of server names to disable

        Returns:
            True if successful

        Raises:
            CommandError: If command fails
        """
        if not servers:
            return True

        cmd = ["docker", "mcp", "server", "disable"] + servers
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            error_msg = stdout if stdout else "Unknown error"
            raise CommandError(
                cmd,
                return_code,
                stderr=error_msg,
                details={"servers": servers},
            )

        return True

    async def get_server_tools(self, server: str) -> List[Tool]:
        """
        Get tools from a specific server.

        Args:
            server: Server name

        Returns:
            List of tools

        Raises:
            CommandError: If command fails
            ParseError: If parsing fails
        """
        cmd = ["docker", "mcp", "tools", "ls", "--format=json"]
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            error_msg = stdout if stdout else "Unknown error"
            raise CommandError(cmd, return_code, stderr=error_msg, details={"server": server})

        data = parse_json_output(stdout)
        if not data:
            # Empty list is valid - no tools
            return []

        tools = []
        try:
            # Filter tools by server
            if isinstance(data, list):
                for tool_data in data:
                    if isinstance(tool_data, dict):
                        # Try different possible keys for server name
                        tool_server = (
                            tool_data.get("server")
                            or tool_data.get("serverName")
                            or tool_data.get("server_name")
                        )
                        if tool_server == server:
                            tools.append(self._parse_tool(tool_data))
            elif isinstance(data, dict):
                if "tools" in data:
                    for tool_data in data["tools"]:
                        if isinstance(tool_data, dict):
                            tool_server = (
                                tool_data.get("server")
                                or tool_data.get("serverName")
                                or tool_data.get("server_name")
                            )
                            if tool_server == server:
                                tools.append(self._parse_tool(tool_data))
                elif "items" in data:
                    for tool_data in data["items"]:
                        if isinstance(tool_data, dict):
                            tool_server = (
                                tool_data.get("server")
                                or tool_data.get("serverName")
                                or tool_data.get("server_name")
                            )
                            if tool_server == server:
                                tools.append(self._parse_tool(tool_data))
        except Exception as e:
            raise ParseError(
                "tools ls output",
                reason=str(e),
                details={"server": server, "data": data},
            ) from e

        return tools

    async def get_server_info(self, server: str) -> Optional[ServerMetadata]:
        """
        Get detailed information about a server.

        Args:
            server: Server name

        Returns:
            Server metadata or None if not found

        Raises:
            CommandError: If command fails
            ParseError: If parsing fails
        """
        # Try inspect command first
        cmd = ["docker", "mcp", "server", "inspect", server]
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code == 0:
            data = parse_json_output(stdout)
            if data:
                try:
                    return self._parse_server_metadata(server, data)
                except Exception as e:
                    raise ParseError(
                        f"server inspect output for {server}",
                        reason=str(e),
                        details={"data": data},
                    ) from e

        # Fallback to catalog (don't raise error if inspect fails, try catalog)
        try:
            servers = await self.get_catalog_servers()
            for s in servers:
                if s.name == server:
                    return s
        except Exception:
            # If catalog lookup also fails, return None
            pass

        return None

    async def config_read(self) -> Dict[str, Any]:
        """
        Read MCP configuration.

        Returns:
            Configuration dictionary

        Raises:
            CommandError: If command fails
            ParseError: If parsing fails
        """
        cmd = ["docker", "mcp", "config", "read"]
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            error_msg = stdout if stdout else "Unknown error"
            raise CommandError(cmd, return_code, stderr=error_msg)

        data = parse_json_output(stdout)
        if data is None:
            raise ParseError("config read output", reason="Empty or invalid JSON", details={"stdout": stdout})

        return data if data else {}

    async def config_write(self, config: Dict[str, Any]) -> bool:
        """
        Write MCP configuration.

        Args:
            config: Configuration dictionary

        Returns:
            True if successful

        Raises:
            CommandError: If command fails
        """
        import asyncio

        # Docker MCP config write expects input from stdin
        config_json = json.dumps(config)
        cmd = ["docker", "mcp", "config", "write"]
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=config_json.encode()), timeout=self.command_timeout
            )

            if process.returncode == 0:
                return True
            else:
                error_msg = stderr.decode() if stderr else stdout.decode() if stdout else "Unknown error"
                raise CommandError(
                    cmd,
                    process.returncode,
                    stderr=error_msg,
                    details={"config_keys": list(config.keys())},
                )
        except asyncio.TimeoutError:
            raise CommandError(
                cmd,
                -1,
                stderr=f"Timeout after {self.command_timeout} seconds",
                details={"timeout": self.command_timeout},
            )
        except Exception as e:
            raise CommandError(
                cmd,
                -1,
                stderr=str(e),
                details={"error_type": type(e).__name__},
            ) from e

    async def secret_set(self, key: str, value: str) -> bool:
        """
        Set a secret.

        Args:
            key: Secret key
            value: Secret value

        Returns:
            True if successful

        Raises:
            CommandError: If command fails
        """
        cmd = ["docker", "mcp", "secret", "set", f"{key}={value}"]
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            error_msg = stdout if stdout else "Unknown error"
            raise CommandError(cmd, return_code, stderr=error_msg, details={"key": key})

        return True

    async def secret_list(self) -> List[str]:
        """
        List all secrets.

        Returns:
            List of secret keys

        Raises:
            CommandError: If command fails
            ParseError: If parsing fails
        """
        cmd = ["docker", "mcp", "secret", "ls", "--json"]
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            error_msg = stdout if stdout else "Unknown error"
            raise CommandError(cmd, return_code, stderr=error_msg)

        data = parse_json_output(stdout)
        if not data:
            # Empty list is valid - no secrets
            return []

        try:
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                if "secrets" in data:
                    secrets = data["secrets"]
                    if isinstance(secrets, list):
                        return secrets
                    elif isinstance(secrets, dict):
                        return list(secrets.keys())
                elif "items" in data:
                    return data["items"]
        except Exception as e:
            raise ParseError("secret ls output", reason=str(e), details={"data": data}) from e

        return []

    async def secret_remove(self, key: str) -> bool:
        """
        Remove a secret.

        Args:
            key: Secret key to remove

        Returns:
            True if successful

        Raises:
            CommandError: If command fails
        """
        cmd = ["docker", "mcp", "secret", "rm", key]
        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            error_msg = stdout if stdout else "Unknown error"
            raise CommandError(cmd, return_code, stderr=error_msg, details={"key": key})

        return True

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool through Docker MCP Toolkit CLI.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments as dictionary

        Returns:
            Tool result as dictionary

        Raises:
            CommandError: If command fails
            ParseError: If parsing fails
            ToolNotFoundError: If tool is not found
        """
        # Prepare arguments as JSON string
        arguments_json = json.dumps(arguments)

        # Build command: docker mcp tools call <tool_name> --arguments <json>
        cmd = ["docker", "mcp", "tools", "call", tool_name, "--arguments", arguments_json]

        stdout, return_code = await run_command(cmd, timeout=self.command_timeout)

        if return_code != 0:
            error_msg = stdout if stdout else "Unknown error"
            # Check if tool not found
            if "not found" in error_msg.lower() or "unknown tool" in error_msg.lower():
                raise ToolNotFoundError(
                    tool_name,
                    details={"command": cmd, "stderr": error_msg},
                )
            raise CommandError(
                cmd,
                return_code,
                stderr=error_msg,
                details={"tool_name": tool_name, "arguments": arguments},
            )

        # Parse JSON response
        data = parse_json_output(stdout)
        if data is None:
            # Try to parse as plain text if JSON parsing fails
            if stdout.strip():
                # Return as text result
                return {"result": stdout.strip(), "type": "text"}
            raise ParseError(
                f"tools call output for {tool_name}",
                reason="Empty or invalid JSON",
                details={"stdout": stdout},
            )

        # Handle different response formats
        if isinstance(data, dict):
            # Check for error in response
            if "error" in data:
                error_msg = data.get("error", "Unknown error")
                if "not found" in str(error_msg).lower():
                    raise ToolNotFoundError(
                        tool_name,
                        details={"response": data},
                    )
                raise CommandError(
                    cmd,
                    -1,
                    stderr=str(error_msg),
                    details={"tool_name": tool_name, "response": data},
                )
            # Return result
            return data
        elif isinstance(data, list):
            # List of results
            return {"results": data, "type": "list"}
        else:
            # Primitive value
            return {"result": data, "type": "primitive"}

    def _parse_server_metadata(self, name: str, data: Dict[str, Any]) -> ServerMetadata:
        """Parse server metadata from catalog data."""
        return ServerMetadata(
            name=name,
            description=data.get("description"),
            version=data.get("version"),
            keywords=data.get("keywords", []),
            tools_count=data.get("tools_count", 0),
            tools_preview=data.get("tools_preview", []),
            catalog_source=data.get("catalog_source"),
            prompt=data.get("prompt"),
            config_requirements=data.get("config_requirements", {}),
        )

    def _parse_tool(self, data: Dict[str, Any]) -> Tool:
        """Parse tool from data."""
        return Tool(
            name=data.get("name", ""),
            description=data.get("description"),
            inputSchema=data.get("inputSchema"),
        )


