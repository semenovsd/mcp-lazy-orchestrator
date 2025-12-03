"""
Мониторинг использования серверов.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import dict, Optional
from collections import defaultdict


@dataclass
class ServerUsage:
    """Использование сервера"""
    last_used: datetime
    access_count: int = 0
    tool_usage: dict[str, int] = field(default_factory=lambda: defaultdict(int))


class UsageMonitor:
    """Мониторинг использования серверов"""
    
    def __init__(self, idle_timeout_minutes: int = 10):
        self.idle_timeout = timedelta(minutes=idle_timeout_minutes)
        self.usage: dict[str, ServerUsage] = {}
    
    def track_activation(self, server_name: str):
        """Отслеживает активацию сервера"""
        now = datetime.now()
        if server_name not in self.usage:
            self.usage[server_name] = ServerUsage(last_used=now)
        else:
            self.usage[server_name].last_used = now
    
    def track_tool_usage(self, server_name: str, tool_name: str):
        """Отслеживает использование инструмента"""
        now = datetime.now()
        if server_name not in self.usage:
            self.usage[server_name] = ServerUsage(last_used=now)
        
        usage = self.usage[server_name]
        usage.last_used = now
        usage.access_count += 1
        usage.tool_usage[tool_name] += 1
    
    def get_usage_stats(self) -> dict[str, int]:
        """Получить статистику использования"""
        return {
            name: usage.access_count
            for name, usage in self.usage.items()
        }
    
    def recommend_deactivation(self, active_servers: set[str]) -> list[str]:
        """Рекомендует серверы для деактивации"""
        now = datetime.now()
        recommendations = []
        
        for server in active_servers:
            usage = self.usage.get(server)
            if usage:
                idle_time = now - usage.last_used
                if idle_time > self.idle_timeout:
                    recommendations.append(server)
            else:
                # Сервер активирован, но не использовался
                recommendations.append(server)
        
        return recommendations
    
    def get_server_stats(self, server_name: str) -> Optional[ServerUsage]:
        """Получить статистику конкретного сервера"""
        return self.usage.get(server_name)
