"""
Capabilities Registry - связь технологий с серверами
"""

import yaml
from pathlib import Path
from typing import Optional, dict, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger("capabilities")


@dataclass
class ServerCapabilities:
    """Capabilities сервера"""
    name: str
    purpose: str
    covers_technologies: list[str] = field(default_factory=list)
    when_to_use: str = ""
    tools_preview: list[str] = field(default_factory=list)
    related_servers: list[str] = field(default_factory=list)
    auto_activate_with: list[str] = field(default_factory=list)


class CapabilitiesRegistry:
    """Реестр capabilities серверов"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.registry: dict[str, ServerCapabilities] = {}
        if config_path is None:
            # Пробуем найти в разных местах
            possible_paths = [
                Path("capabilities/base.yaml"),
                Path(__file__).parent.parent.parent / "capabilities" / "base.yaml",
                Path(__file__).parent / "capabilities" / "base.yaml",
            ]
            for path in possible_paths:
                if path.exists():
                    config_path = path
                    break
        
        self.config_path = config_path
        self._load_capabilities()
    
    def _load_capabilities(self):
        """Загрузить capabilities из YAML"""
        if self.config_path and self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    data = yaml.safe_load(f)
                    for server_name, config in data.get("servers", {}).items():
                        self.registry[server_name] = ServerCapabilities(
                            name=server_name,
                            purpose=config.get("purpose", ""),
                            covers_technologies=config.get("covers_technologies", []),
                            when_to_use=config.get("when_to_use", ""),
                            tools_preview=config.get("tools_preview", []),
                            related_servers=config.get("related_servers", []),
                            auto_activate_with=config.get("auto_activate_with", [])
                        )
                logger.info(f"Loaded capabilities from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load capabilities from YAML: {e}")
                self._load_default_capabilities()
        else:
            # Fallback: базовые capabilities
            logger.info("Using default capabilities (YAML not found)")
            self._load_default_capabilities()
    
    def _load_default_capabilities(self):
        """Загрузить дефолтные capabilities"""
        defaults = {
            "context7": ServerCapabilities(
                name="context7",
                purpose="Up-to-date library documentation",
                covers_technologies=[
                    "redis", "postgres", "fastapi", "django", "react", "vue",
                    "kubernetes", "sqlalchemy", "pytest", "celery", "docker",
                    "nginx", "python", "javascript", "typescript", "node",
                    "express", "flask", "tornado", "aiohttp", "requests",
                    "pandas", "numpy", "tensorflow", "pytorch", "opencv"
                ],
                when_to_use="BEFORE writing code - get current API docs",
                tools_preview=["resolve-library-id", "get-library-docs"],
                auto_activate_with=["redis", "postgres", "playwright", "github"]
            ),
            "redis": ServerCapabilities(
                name="redis",
                purpose="Redis database operations",
                covers_technologies=["caching", "sessions", "pub/sub", "queues", "locks"],
                when_to_use="Direct Redis commands and data management",
                tools_preview=["redis_get", "redis_set", "redis_del", "redis_keys"],
                related_servers=["context7"]
            ),
            "postgres": ServerCapabilities(
                name="postgres",
                purpose="PostgreSQL database access",
                covers_technologies=["sql", "database", "queries", "postgresql"],
                when_to_use="Database queries and schema operations",
                tools_preview=["query"],
                related_servers=["context7"]
            ),
            "playwright": ServerCapabilities(
                name="playwright",
                purpose="Browser automation",
                covers_technologies=["browser", "screenshots", "scraping", "testing", "e2e"],
                when_to_use="Web interaction, JS-heavy sites, E2E testing",
                tools_preview=["browser_navigate", "browser_screenshot", "browser_click"],
                related_servers=["context7"]
            ),
            "github": ServerCapabilities(
                name="github",
                purpose="GitHub integration",
                covers_technologies=["git", "github", "repository", "issues", "prs"],
                when_to_use="GitHub API operations, issues, PRs, code search",
                tools_preview=["create_issue", "create_pull_request", "search_repositories"],
                related_servers=["context7"]
            ),
            "fetch": ServerCapabilities(
                name="fetch",
                purpose="HTTP client for web requests",
                covers_technologies=["http", "api", "fetch", "download", "requests"],
                when_to_use="Simple HTTP requests, API calls",
                tools_preview=["fetch"],
                related_servers=["context7"]
            ),
            "desktop-commander": ServerCapabilities(
                name="desktop-commander",
                purpose="Desktop automation and file system",
                covers_technologies=["file", "folder", "directory", "command", "shell"],
                when_to_use="File management, command execution, process control",
                tools_preview=["read_file", "write_file", "execute_command"],
                related_servers=[]
            ),
            "sequential-thinking": ServerCapabilities(
                name="sequential-thinking",
                purpose="Structured problem-solving through sequential reasoning",
                covers_technologies=["reasoning", "planning", "analysis", "thinking"],
                when_to_use="Complex multi-step analysis and planning",
                tools_preview=["think", "analyze", "plan"],
                related_servers=[]
            ),
        }
        self.registry.update(defaults)
    
    def get(self, server_name: str) -> Optional[ServerCapabilities]:
        """Получить capabilities сервера"""
        return self.registry.get(server_name)
    
    def find_by_technology(self, technology: str) -> list[str]:
        """Найти серверы которые покрывают технологию"""
        technology_lower = technology.lower()
        matching = []
        
        for server_name, caps in self.registry.items():
            if any(tech.lower() == technology_lower 
                   for tech in caps.covers_technologies):
                matching.append(server_name)
        
        return matching
    
    def get_related_servers(self, server_name: str) -> list[str]:
        """Получить связанные серверы"""
        caps = self.get(server_name)
        if caps:
            return caps.related_servers
        return []
