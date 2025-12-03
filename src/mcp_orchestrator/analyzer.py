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
                        if "context7" not in recommended:
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
