"""
Docker MCP Orchestrator v2.0

Smart orchestrator with automatic discovery, semantic routing, and token optimization.
"""

from .server import mcp, main

__version__ = "2.0.0"
__author__ = "semenovsd"
__license__ = "CC BY-NC 4.0"
__all__ = ["mcp", "main"]
