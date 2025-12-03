# Финальная техническая реализация

## 📁 Структура проекта

```
src/mcp_orchestrator/
├── __init__.py
├── server.py                    # Main MCP server (обновлённый)
├── discovery.py                 # Автоматическое обнаружение
├── registry.py                  # Реестр серверов
├── capabilities.py              # Capabilities registry
├── analyzer.py                  # Task analyzer (keyword + semantic)
├── router.py                    # Semantic router
├── profiles.py                  # Server profiles
├── monitor.py                   # Usage monitor
├── telemetry.py                 # Observability
└── config.py                    # Configuration
```

---

## 🔧 Реализация компонентов

### 1. capabilities.py - Capabilities Registry

```python
"""
Capabilities Registry - связь технологий с серверами
"""

import yaml
from pathlib import Path
from typing import Optional, dict, Any
from dataclasses import dataclass, field


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
        self.config_path = config_path or Path("capabilities/base.yaml")
        self._load_capabilities()
    
    def _load_capabilities(self):
        """Загрузить capabilities из YAML"""
        if self.config_path.exists():
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
        else:
            # Fallback: базовые capabilities
            self._load_default_capabilities()
    
    def _load_default_capabilities(self):
        """Загрузить дефолтные capabilities"""
        defaults = {
            "context7": ServerCapabilities(
                name="context7",
                purpose="Up-to-date library documentation",
                covers_technologies=["redis", "postgres", "fastapi", "django", 
                                    "react", "vue", "kubernetes", "sqlalchemy"],
                when_to_use="BEFORE writing code - get current API docs",
                tools_preview=["resolve-library-id", "get-library-docs"],
                auto_activate_with=["redis", "postgres", "playwright", "github"]
            ),
            "redis": ServerCapabilities(
                name="redis",
                purpose="Redis database operations",
                covers_technologies=["caching", "sessions", "pub/sub", "queues"],
                when_to_use="Direct Redis commands and data management",
                tools_preview=["redis_get", "redis_set", "redis_del"],
                related_servers=["context7"]
            ),
            # ... другие серверы
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
```

### 2. router.py - Semantic Router

```python
"""
Semantic Router - умная маршрутизация через embeddings
"""

from typing import list, tuple
import logging

# Опционально: использовать sentence-transformers для semantic matching
try:
    from sentence_transformers import SentenceTransformer
    HAS_SEMANTIC = True
except ImportError:
    HAS_SEMANTIC = False
    logging.warning("sentence-transformers not installed, using keyword matching only")


class SemanticRouter:
    """Semantic router для умного определения серверов"""
    
    def __init__(self, capabilities_registry):
        self.capabilities = capabilities_registry
        self.model = None
        
        if HAS_SEMANTIC:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                self._build_index()
            except Exception as e:
                logging.warning(f"Failed to load semantic model: {e}")
                self.model = None
    
    def _build_index(self):
        """Построить индекс embeddings для серверов"""
        if not self.model:
            return
        
        self.server_embeddings = {}
        for server_name, caps in self.capabilities.registry.items():
            # Создаём текстовое описание для embedding
            text = f"{caps.purpose} {' '.join(caps.covers_technologies)}"
            self.server_embeddings[server_name] = self.model.encode(text)
    
    def match_servers(
        self, 
        task_description: str, 
        top_k: int = 5
    ) -> list[tuple[str, float]]:
        """
        Найти релевантные серверы для задачи.
        
        Returns:
            List of (server_name, confidence_score) tuples
        """
        if self.model and hasattr(self, 'server_embeddings'):
            return self._semantic_match(task_description, top_k)
        else:
            return self._keyword_match(task_description, top_k)
    
    def _semantic_match(
        self, 
        task_description: str, 
        top_k: int
    ) -> list[tuple[str, float]]:
        """Semantic matching через embeddings"""
        task_emb = self.model.encode(task_description)
        
        similarities = []
        for server_name, server_emb in self.server_embeddings.items():
            # Cosine similarity
            import numpy as np
            similarity = np.dot(task_emb, server_emb) / (
                np.linalg.norm(task_emb) * np.linalg.norm(server_emb)
            )
            similarities.append((server_name, float(similarity)))
        
        # Сортируем и возвращаем top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def _keyword_match(
        self, 
        task_description: str, 
        top_k: int
    ) -> list[tuple[str, float]]:
        """Keyword matching (fallback)"""
        task_lower = task_description.lower()
        matches = []
        
        for server_name, caps in self.capabilities.registry.items():
            score = 0.0
            
            # Проверяем covers_technologies
            for tech in caps.covers_technologies:
                if tech.lower() in task_lower:
                    score += 0.5
            
            # Проверяем purpose
            if any(word in task_lower for word in caps.purpose.lower().split()):
                score += 0.3
            
            if score > 0:
                matches.append((server_name, min(score, 1.0)))
        
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:top_k]
```

### 3. analyzer.py - Enhanced Task Analyzer

```python
"""
Enhanced Task Analyzer - комбинация keyword и semantic анализа
"""

from dataclasses import dataclass
from typing import list
from .router import SemanticRouter
from .capabilities import CapabilitiesRegistry


@dataclass
class TaskAnalysis:
    """Результат анализа задачи"""
    required_servers: list[str]
    recommended_servers: list[str]
    activation_order: list[str]
    estimated_tokens: int
    confidence: float
    detected_technologies: list[str]


class EnhancedTaskAnalyzer:
    """Улучшенный анализатор задач"""
    
    def __init__(
        self, 
        capabilities_registry: CapabilitiesRegistry,
        semantic_router: SemanticRouter
    ):
        self.capabilities = capabilities_registry
        self.router = semantic_router
    
    def analyze_task(self, task_description: str) -> TaskAnalysis:
        """Анализирует задачу комбинированным подходом"""
        # 1. Keyword-based анализ
        keyword_servers = self._keyword_analysis(task_description)
        
        # 2. Semantic анализ
        semantic_matches = self.router.match_servers(task_description, top_k=5)
        semantic_servers = [s for s, _ in semantic_matches if s not in keyword_servers]
        
        # 3. Объединяем результаты
        all_servers = list(set(keyword_servers + semantic_servers))
        
        # 4. Определяем технологии
        detected_techs = self._detect_technologies(task_description)
        
        # 5. Добавляем зависимости (context7 для библиотек)
        required = []
        recommended = []
        
        for server in all_servers:
            caps = self.capabilities.get(server)
            if caps:
                # Если это библиотека - добавляем context7
                if caps.covers_technologies and "context7" not in all_servers:
                    if any(tech in task_description.lower() 
                           for tech in caps.covers_technologies):
                        recommended.append("context7")
                
                # Добавляем связанные серверы
                for related in caps.related_servers:
                    if related not in all_servers and related not in recommended:
                        recommended.append(related)
        
        required = all_servers
        all_servers = required + recommended
        
        # 6. Оптимизируем порядок активации
        activation_order = self._optimize_order(all_servers)
        
        # 7. Оцениваем токены
        estimated_tokens = self._estimate_tokens(all_servers)
        
        # 8. Уверенность
        confidence = self._calculate_confidence(
            task_description, 
            required, 
            semantic_matches
        )
        
        return TaskAnalysis(
            required_servers=required,
            recommended_servers=recommended,
            activation_order=activation_order,
            estimated_tokens=estimated_tokens,
            confidence=confidence,
            detected_technologies=detected_techs
        )
    
    def _keyword_analysis(self, task: str) -> list[str]:
        """Keyword-based анализ"""
        task_lower = task.lower()
        matched = []
        
        for server_name, caps in self.capabilities.registry.items():
            # Проверяем covers_technologies
            if any(tech.lower() in task_lower for tech in caps.covers_technologies):
                matched.append(server_name)
        
        return matched
    
    def _detect_technologies(self, task: str) -> list[str]:
        """Определить упомянутые технологии"""
        task_lower = task.lower()
        technologies = []
        
        # Собираем все технологии из capabilities
        all_techs = set()
        for caps in self.capabilities.registry.values():
            all_techs.update(caps.covers_technologies)
        
        # Ищем упоминания
        for tech in all_techs:
            if tech.lower() in task_lower:
                technologies.append(tech)
        
        return technologies
    
    def _optimize_order(self, servers: list[str]) -> list[str]:
        """Оптимизировать порядок активации"""
        # Сначала зависимости (context7), потом основные
        deps = [s for s in servers if s == "context7"]
        main = [s for s in servers if s != "context7"]
        return deps + main
    
    def _estimate_tokens(self, servers: list[str]) -> int:
        """Оценить количество токенов"""
        # Примерно 1000 токенов на сервер
        return len(servers) * 1000
    
    def _calculate_confidence(
        self, 
        task: str, 
        required: list[str],
        semantic_matches: list[tuple[str, float]]
    ) -> float:
        """Вычислить уверенность в анализе"""
        if not required:
            return 0.0
        
        # Берем средний confidence из semantic matches
        if semantic_matches:
            avg_confidence = sum(score for _, score in semantic_matches) / len(semantic_matches)
            return min(1.0, avg_confidence)
        
        # Fallback: базовая уверенность
        return 0.7 if required else 0.0
```

### 4. telemetry.py - Observability

```python
"""
Telemetry для observability
"""

import json
import time
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class ActivationEvent:
    """Событие активации сервера"""
    server: str
    reason: str
    success: bool
    latency_ms: float
    timestamp: float
    error: Optional[str] = None


class Telemetry:
    """Telemetry для отслеживания использования"""
    
    def __init__(self, log_file: Optional[str] = None):
        self.logger = logging.getLogger("telemetry")
        self.log_file = log_file
        self.events: list[ActivationEvent] = []
    
    def log_activation(
        self,
        server: str,
        reason: str,
        success: bool,
        latency_ms: float = 0.0,
        error: Optional[str] = None
    ):
        """Логировать активацию сервера"""
        event = ActivationEvent(
            server=server,
            reason=reason,
            success=success,
            latency_ms=latency_ms,
            timestamp=time.time(),
            error=error
        )
        
        self.events.append(event)
        
        # Логируем
        log_data = asdict(event)
        log_data["timestamp"] = datetime.fromtimestamp(event.timestamp).isoformat()
        
        self.logger.info(json.dumps(log_data))
        
        # Опционально: запись в файл
        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_data) + "\n")
    
    def get_stats(self) -> dict:
        """Получить статистику"""
        if not self.events:
            return {}
        
        total = len(self.events)
        successful = sum(1 for e in self.events if e.success)
        failed = total - successful
        
        avg_latency = sum(e.latency_ms for e in self.events) / total if total > 0 else 0
        
        server_counts = {}
        for event in self.events:
            server_counts[event.server] = server_counts.get(event.server, 0) + 1
        
        return {
            "total_activations": total,
            "successful": successful,
            "failed": failed,
            "avg_latency_ms": avg_latency,
            "server_counts": server_counts
        }
```

### 5. Обновлённый server.py - Интеграция всех компонентов

```python
# В начале файла добавить импорты
from .discovery import ServerDiscovery, ServerMetadata
from .registry import ServerRegistry
from .capabilities import CapabilitiesRegistry
from .analyzer import EnhancedTaskAnalyzer
from .router import SemanticRouter
from .profiles import find_matching_profile, get_all_profiles, SERVER_PROFILES
from .monitor import UsageMonitor
from .telemetry import Telemetry

# Глобальные объекты
discovery = ServerDiscovery()
registry = ServerRegistry(discovery)
capabilities_registry = CapabilitiesRegistry()
semantic_router = SemanticRouter(capabilities_registry)
task_analyzer = EnhancedTaskAnalyzer(capabilities_registry, semantic_router)
usage_monitor = UsageMonitor()
telemetry = Telemetry()

# Обновить существующие инструменты и добавить новые
# (см. FINAL_HYBRID_SOLUTION.md для полного кода)

# В main() добавить инициализацию
async def initialize():
    """Инициализация всех компонентов"""
    logger.info("Initializing Smart MCP Orchestrator v2.0...")
    
    # 1. Обнаружение серверов
    await registry.refresh(force=True)
    logger.info(f"Discovered {len(registry.servers)} servers")
    
    # 2. Загрузка capabilities
    logger.info(f"Loaded capabilities for {len(capabilities_registry.registry)} servers")
    
    # 3. Синхронизация состояния
    enabled = get_enabled_servers()
    state.active_servers = set(enabled) & set(registry.servers.keys())
    
    if state.active_servers:
        logger.info(f"Found active: {state.active_servers}")
        for server in state.active_servers:
            state.server_tools_cache[server] = get_server_tools(server)
            usage_monitor.track_activation(server)
    
    logger.info("Ready!")

def main():
    """Main entry point"""
    asyncio.run(initialize())
    mcp.run()
```

---

## 📊 Итоговая структура

```
Smart MCP Orchestrator v2.0
├── Dynamic Discovery (автоматическое обнаружение)
├── Capabilities Registry (технологии → серверы)
├── Smart Routing (keyword + semantic)
├── Task Analyzer (комбинированный анализ)
├── Server Profiles (готовые комбинации)
├── Usage Monitor (мониторинг)
├── Telemetry (observability)
└── 8 Core Tools
    ├── get_capabilities() - compact catalog
    ├── suggest_servers() - умные рекомендации
    ├── activate_servers() - активация с tools
    ├── activate_profile() - профили
    ├── deactivate_servers() - деактивация
    ├── get_status() - состояние
    ├── monitor_usage() - статистика
    └── optimize_servers() - оптимизация
```

**Полная автоматизация + умные рекомендации + мониторинг = Senior AI Engineer решение!** 🚀
