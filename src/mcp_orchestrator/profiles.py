"""
Server Profiles - готовые комбинации серверов для типичных задач
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ServerProfile:
    """Профиль серверов"""
    name: str
    description: str
    servers: list[str]
    auto_activate: bool = True
    estimated_tokens: int = 0


SERVER_PROFILES: dict[str, ServerProfile] = {
    "web-development": ServerProfile(
        name="web-development",
        description="Web development tasks: browser automation, GitHub, HTTP",
        servers=["playwright", "github", "context7", "fetch"],
        auto_activate=True,
        estimated_tokens=4000
    ),
    "data-science": ServerProfile(
        name="data-science",
        description="Data analysis: databases, caching, documentation",
        servers=["postgres", "redis", "context7"],
        auto_activate=True,
        estimated_tokens=3000
    ),
    "documentation": ServerProfile(
        name="documentation",
        description="Library documentation lookup",
        servers=["context7"],
        auto_activate=True,
        estimated_tokens=500
    ),
    "full-stack": ServerProfile(
        name="full-stack",
        description="Full stack development: all tools",
        servers=["playwright", "github", "postgres", "redis", 
                "context7", "fetch", "desktop-commander"],
        auto_activate=False,  # Требует подтверждения
        estimated_tokens=8000
    ),
    "database": ServerProfile(
        name="database",
        description="Database operations: PostgreSQL and Redis",
        servers=["postgres", "redis", "context7"],
        auto_activate=True,
        estimated_tokens=3000
    ),
    "browser-automation": ServerProfile(
        name="browser-automation",
        description="Browser automation and web scraping",
        servers=["playwright", "context7"],
        auto_activate=True,
        estimated_tokens=2000
    ),
}


def find_matching_profile(task_description: str) -> Optional[ServerProfile]:
    """Найти подходящий профиль для задачи"""
    task_lower = task_description.lower()
    
    profile_keywords = {
        "web-development": ["web", "website", "browser", "frontend", "ui", "html", "css"],
        "data-science": ["data", "analysis", "database", "sql", "query", "analytics"],
        "documentation": ["documentation", "docs", "api", "reference", "library"],
        "full-stack": ["full stack", "fullstack", "complete", "all", "everything"],
        "database": ["database", "db", "sql", "postgres", "redis", "mysql"],
        "browser-automation": ["browser", "scraping", "screenshot", "automation", "selenium"],
    }
    
    for profile_name, keywords in profile_keywords.items():
        if any(kw in task_lower for kw in keywords):
            return SERVER_PROFILES.get(profile_name)
    
    return None


def get_all_profiles() -> list[ServerProfile]:
    """Получить все профили"""
    return list(SERVER_PROFILES.values())
