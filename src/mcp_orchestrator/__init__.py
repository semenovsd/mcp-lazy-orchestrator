"""
Docker MCP Orchestrator

A lightweight MCP server that manages Docker MCP servers on-demand,
reducing token usage by loading servers only when needed.

Repository: https://github.com/semenovsd/docker-mcp-orchestrator
License: CC BY-NC 4.0
"""

from .server import mcp, main

__version__ = "1.0.0"
__author__ = "semenovsd"
__license__ = "CC BY-NC 4.0"
__all__ = ["mcp", "main"]
