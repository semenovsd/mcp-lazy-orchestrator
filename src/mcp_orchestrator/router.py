"""
Semantic Router - умная маршрутизация через embeddings
"""

import logging
from typing import list, tuple

logger = logging.getLogger("router")

# Опционально: использовать sentence-transformers для semantic matching
HAS_SEMANTIC = False
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    HAS_SEMANTIC = True
except ImportError:
    logger.info("sentence-transformers not installed, using keyword matching only")


class SemanticRouter:
    """Semantic router для умного определения серверов"""
    
    def __init__(self, capabilities_registry):
        self.capabilities = capabilities_registry
        self.model = None
        self.server_embeddings = {}
        
        if HAS_SEMANTIC:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                self._build_index()
            except Exception as e:
                logger.warning(f"Failed to load semantic model: {e}")
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
        if self.model and self.server_embeddings:
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
