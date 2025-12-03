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
        # Ограничиваем размер истории
        self.max_events = 1000
    
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
        
        # Ограничиваем размер
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # Логируем
        log_data = asdict(event)
        log_data["timestamp"] = datetime.fromtimestamp(event.timestamp).isoformat()
        
        self.logger.info(json.dumps(log_data))
        
        # Опционально: запись в файл
        if self.log_file:
            try:
                with open(self.log_file, "a") as f:
                    f.write(json.dumps(log_data) + "\n")
            except Exception as e:
                self.logger.warning(f"Failed to write telemetry to file: {e}")
    
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
