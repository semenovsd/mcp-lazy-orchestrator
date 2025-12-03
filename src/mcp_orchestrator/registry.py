"""
Реестр обнаруженных серверов с кэшированием.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .discovery import ServerDiscovery, ServerMetadata

logger = logging.getLogger("registry")


class ServerRegistry:
    """Реестр серверов с автоматическим обновлением"""
    
    def __init__(self, discovery: ServerDiscovery):
        self.discovery = discovery
        self.servers: dict[str, ServerMetadata] = {}
        self.last_discovery: Optional[datetime] = None
        self.discovery_interval = timedelta(minutes=5)
        self.config_overrides: dict[str, dict] = {}
        self._load_config_overrides()
    
    def _load_config_overrides(self):
        """Загрузить переопределения из config/servers.json (если есть)"""
        config_path = Path("config/servers.json")
        if not config_path.exists():
            config_path = Path(__file__).parent.parent.parent / "config" / "servers.json"
        
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    self.config_overrides = config.get("servers", {})
            except Exception as e:
                logger.warning(f"Failed to load server config: {e}")
    
    async def refresh(self, force: bool = False) -> dict[str, ServerMetadata]:
        """
        Обновить реестр серверов.
        
        Args:
            force: Принудительное обновление даже если недавно обновляли
        
        Returns:
            Обновленный словарь серверов
        """
        now = datetime.now()
        
        # Проверяем нужно ли обновление
        if not force and self.last_discovery:
            if (now - self.last_discovery) < self.discovery_interval:
                logger.debug("Using cached server registry")
                return self.servers
        
        logger.info("Refreshing server registry...")
        
        # Обнаруживаем серверы
        discovered = await self.discovery.discover_all_servers()
        
        # Применяем переопределения из конфига
        for name, metadata in discovered.items():
            if name in self.config_overrides:
                override = self.config_overrides[name]
                if "category" in override:
                    metadata.category = override["category"]
                if "description" in override:
                    metadata.description = override["description"]
                metadata.config_override = override
        
        self.servers = discovered
        self.last_discovery = now
        
        logger.info(f"Discovered {len(self.servers)} servers")
        return self.servers
    
    def get_catalog(
        self, 
        category_filter: Optional[str] = None,
        include_inactive: bool = True
    ) -> list[ServerMetadata]:
        """
        Получить каталог серверов для list_available_servers().
        
        Args:
            category_filter: Фильтр по категории
            include_inactive: Включать неактивные серверы
        
        Returns:
            Список метаданных серверов
        """
        servers = list(self.servers.values())
        
        # Фильтр по категории
        if category_filter:
            servers = [s for s in servers if s.category == category_filter]
        
        # Фильтр по статусу
        if not include_inactive:
            servers = [s for s in servers if s.status == "enabled"]
        
        return sorted(servers, key=lambda s: (s.category, s.name))
    
    def get_server(self, name: str) -> Optional[ServerMetadata]:
        """Получить метаданные конкретного сервера"""
        return self.servers.get(name)
    
    def get_by_category(self, category: str) -> list[ServerMetadata]:
        """Получить все серверы категории"""
        return [s for s in self.servers.values() if s.category == category]
    
    def get_categories(self) -> set[str]:
        """Получить все категории"""
        return {s.category for s in self.servers.values()}
