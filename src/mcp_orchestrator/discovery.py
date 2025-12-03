"""
Автоматическое обнаружение MCP серверов из Docker MCP Toolkit.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger("discovery")


@dataclass
class ServerMetadata:
    """Метаданные сервера (без деталей tools)"""
    name: str
    description: Optional[str] = None
    category: str = "other"
    tool_count: int = 0
    requires_auth: bool = False
    auth_type: Optional[str] = None
    status: str = "disabled"
    last_discovered: Optional[datetime] = None
    config_override: Optional[dict[str, Any]] = None


class ServerDiscovery:
    """Автоматическое обнаружение серверов из Docker MCP Toolkit"""
    
    CATEGORY_KEYWORDS = {
        "database": ["redis", "postgres", "mysql", "mongodb", "sqlite", "db"],
        "browser": ["playwright", "puppeteer", "selenium", "browser"],
        "documentation": ["context7", "docs", "readme", "documentation"],
        "version_control": ["github", "gitlab", "bitbucket", "git"],
        "networking": ["fetch", "http", "curl", "requests", "api"],
        "system": ["desktop", "commander", "file", "shell", "command"],
        "reasoning": ["thinking", "sequential", "planning", "reason"],
    }
    
    def __init__(self):
        self.logger = logger
    
    def run_docker_mcp_command(self, args: list[str], timeout: int = 60) -> tuple[bool, str]:
        """Выполнить команду docker mcp CLI"""
        import subprocess
        cmd = ["docker", "mcp"] + args
        self.logger.debug(f"Executing: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                self.logger.error(f"Command failed: {error_msg}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout}s"
        except FileNotFoundError:
            return False, ("Docker MCP CLI not found. Ensure Docker Desktop "
                          "is installed with MCP Toolkit enabled.")
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    async def discover_all_servers(self) -> dict[str, ServerMetadata]:
        """
        Обнаружить все доступные серверы из Docker MCP Toolkit.
        
        Returns:
            Словарь {server_name: ServerMetadata}
        """
        # 1. Получить список всех серверов
        servers_list = await self._list_servers()
        
        # 2. Для каждого сервера получить метаданные
        metadata_dict = {}
        for server_name in servers_list:
            try:
                metadata = await self._get_server_metadata(server_name)
                metadata_dict[server_name] = metadata
            except Exception as e:
                self.logger.warning(f"Failed to get metadata for {server_name}: {e}")
                # Fallback: минимальные метаданные
                metadata_dict[server_name] = ServerMetadata(
                    name=server_name,
                    status="unknown"
                )
        
        return metadata_dict
    
    async def _list_servers(self) -> list[str]:
        """Получить список всех серверов"""
        success, output = self.run_docker_mcp_command(["server", "ls"])
        
        if not success:
            self.logger.error(f"Failed to list servers: {output}")
            return []
        
        servers = []
        for line in output.split('\n'):
            line = line.strip()
            if line and not line.startswith('NAME') and not line.startswith('-'):
                parts = line.split()
                if parts:
                    servers.append(parts[0])
        
        return servers
    
    async def _get_server_metadata(self, server_name: str) -> ServerMetadata:
        """Получить метаданные конкретного сервера"""
        # 1. Проверить статус
        status = await self._get_server_status(server_name)
        
        # 2. Получить inspect информацию
        inspect_data = await self._inspect_server(server_name)
        
        # 3. Получить количество tools (БЕЗ деталей)
        tool_count = await self._get_tool_count(server_name)
        
        # 4. Определить категорию
        category = self._detect_category(server_name, inspect_data.get("description", ""))
        
        # 5. Проверить аутентификацию
        requires_auth, auth_type = self._check_auth_requirements(inspect_data)
        
        return ServerMetadata(
            name=server_name,
            description=inspect_data.get("description"),
            category=category,
            tool_count=tool_count,
            requires_auth=requires_auth,
            auth_type=auth_type,
            status=status,
            last_discovered=datetime.now()
        )
    
    async def _get_server_status(self, server_name: str) -> str:
        """Проверить статус сервера (enabled/disabled)"""
        success, output = self.run_docker_mcp_command(["server", "ls"])
        if not success:
            return "unknown"
        
        for line in output.split('\n'):
            if server_name in line:
                if "enabled" in line.lower() or "active" in line.lower():
                    return "enabled"
                return "disabled"
        
        return "disabled"
    
    async def _inspect_server(self, server_name: str) -> dict:
        """Получить детальную информацию о сервере"""
        success, output = self.run_docker_mcp_command(
            ["server", "inspect", server_name]
        )
        
        if not success:
            return {}
        
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            # Парсинг текстового вывода
            return {"description": output[:200]}
    
    async def _get_tool_count(self, server_name: str) -> int:
        """Получить количество tools (БЕЗ деталей)"""
        success, output = self.run_docker_mcp_command(
            ["tools", "list", "--server", server_name]
        )
        
        if not success:
            return 0
        
        try:
            # Если JSON
            data = json.loads(output)
            if isinstance(data, list):
                return len(data)
            elif isinstance(data, dict) and "tools" in data:
                return len(data["tools"])
        except json.JSONDecodeError:
            # Если текстовый вывод - считаем строки
            lines = [l for l in output.split('\n') 
                    if l.strip() and not l.startswith('TOOL') 
                    and not l.startswith('-')]
            return len(lines)
        
        return 0
    
    def _detect_category(self, server_name: str, description: str = "") -> str:
        """Автоматически определить категорию"""
        name_lower = server_name.lower()
        desc_lower = description.lower()
        combined = f"{name_lower} {desc_lower}"
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in combined for kw in keywords):
                return category
        
        return "other"
    
    def _check_auth_requirements(self, inspect_data: dict) -> tuple[bool, Optional[str]]:
        """Проверить требования к аутентификации"""
        # Проверяем в inspect_data
        if "auth" in inspect_data or "authentication" in inspect_data:
            auth_info = inspect_data.get("auth") or inspect_data.get("authentication")
            if isinstance(auth_info, dict):
                auth_type = auth_info.get("type") or auth_info.get("method")
                return True, auth_type
            return True, "oauth"  # По умолчанию
        
        # Проверяем по известным серверам
        KNOWN_AUTH_SERVERS = {
            "github": "oauth",
            "gitlab": "oauth",
        }
        
        if inspect_data.get("name") in KNOWN_AUTH_SERVERS:
            return True, KNOWN_AUTH_SERVERS[inspect_data.get("name")]
        
        return False, None
