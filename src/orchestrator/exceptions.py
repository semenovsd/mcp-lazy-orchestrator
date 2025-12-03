"""Custom exceptions for Docker MCP Orchestrator."""


class DockerMCPError(Exception):
    """Base exception for all Docker MCP Orchestrator errors."""

    def __init__(self, message: str, details: dict | None = None):
        """
        Initialize error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ServerNotFoundError(DockerMCPError):
    """Raised when a server is not found."""

    def __init__(self, server: str, details: dict | None = None):
        """
        Initialize error.

        Args:
            server: Server name that was not found
            details: Additional error details
        """
        message = f"Server '{server}' not found"
        super().__init__(message, details)
        self.server = server


class ToolNotFoundError(DockerMCPError):
    """Raised when a tool is not found."""

    def __init__(self, tool_name: str, server: str | None = None, details: dict | None = None):
        """
        Initialize error.

        Args:
            tool_name: Tool name that was not found
            server: Server name (if known)
            details: Additional error details
        """
        if server:
            message = f"Tool '{tool_name}' not found in server '{server}'"
        else:
            message = f"Tool '{tool_name}' not found in any active server"
        super().__init__(message, details)
        self.tool_name = tool_name
        self.server = server


class ConnectionError(DockerMCPError):
    """Raised when connection to a server fails."""

    def __init__(self, server: str, reason: str | None = None, details: dict | None = None):
        """
        Initialize error.

        Args:
            server: Server name
            reason: Reason for connection failure
            details: Additional error details
        """
        message = f"Failed to connect to server '{server}'"
        if reason:
            message += f": {reason}"
        super().__init__(message, details)
        self.server = server
        self.reason = reason


class ParseError(DockerMCPError):
    """Raised when parsing fails."""

    def __init__(self, source: str, reason: str | None = None, details: dict | None = None):
        """
        Initialize error.

        Args:
            source: Source that failed to parse
            reason: Reason for parse failure
            details: Additional error details
        """
        message = f"Failed to parse {source}"
        if reason:
            message += f": {reason}"
        super().__init__(message, details)
        self.source = source
        self.reason = reason


class CommandError(DockerMCPError):
    """Raised when a Docker MCP Toolkit command fails."""

    def __init__(
        self, command: list[str], return_code: int, stderr: str | None = None, details: dict | None = None
    ):
        """
        Initialize error.

        Args:
            command: Command that failed
            return_code: Command return code
            stderr: Error output
            details: Additional error details
        """
        cmd_str = " ".join(command)
        message = f"Command '{cmd_str}' failed with return code {return_code}"
        if stderr:
            message += f": {stderr}"
        super().__init__(message, details)
        self.command = command
        self.return_code = return_code
        self.stderr = stderr


class TimeoutError(DockerMCPError):
    """Raised when an operation times out."""

    def __init__(self, operation: str, timeout: int, details: dict | None = None):
        """
        Initialize error.

        Args:
            operation: Operation that timed out
            timeout: Timeout in seconds
            details: Additional error details
        """
        message = f"Operation '{operation}' timed out after {timeout} seconds"
        super().__init__(message, details)
        self.operation = operation
        self.timeout = timeout

