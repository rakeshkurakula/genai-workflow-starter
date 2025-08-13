"""Cost logging for GenAI Workflow API."""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from pathlib import Path
import threading


@dataclass
class CostEntry:
    """Represents a single cost entry."""
    timestamp: str
    session_id: str
    operation: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    duration_ms: float
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


class CostLogger:
    """Simple cost logger for tracking GenAI API usage and costs."""
    
    def __init__(self, log_file: Optional[str] = None, enable_console: bool = True):
        """Initialize the cost logger.
        
        Args:
            log_file: Optional file path to log costs to
            enable_console: Whether to log to console
        """
        self.log_file = log_file
        self.enable_console = enable_console
        self._entries: List[CostEntry] = []
        self._lock = threading.Lock()
        
        # Setup logging
        self.logger = logging.getLogger("cost_logger")
        self.logger.setLevel(logging.INFO)
        
        if enable_console and not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(console_handler)
        
        # Setup file logging if specified
        if log_file and not any(isinstance(h, logging.FileHandler) for h in self.logger.handlers):
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(file_handler)
    
    def log_cost(
        self,
        session_id: str,
        operation: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        duration_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a cost entry.
        
        Args:
            session_id: Session or request ID
            operation: Type of operation (e.g., 'chat', 'completion', 'embedding')
            provider: AI provider (e.g., 'openai', 'anthropic', 'local')
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost_usd: Cost in USD
            duration_ms: Operation duration in milliseconds
            metadata: Additional metadata
        """
        entry = CostEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            operation=operation,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )
        
        with self._lock:
            self._entries.append(entry)
        
        # Log to configured outputs
        log_message = (
            f"Cost: {cost_usd:.6f} USD | "
            f"Session: {session_id} | "
            f"Operation: {operation} | "
            f"Provider: {provider} | "
            f"Model: {model} | "
            f"Tokens: {input_tokens}→{output_tokens} | "
            f"Duration: {duration_ms:.2f}ms"
        )
        
        self.logger.info(log_message)
        
        # Write to JSON file if specified
        if self.log_file:
            self._write_json_entry(entry)
    
    def _write_json_entry(self, entry: CostEntry) -> None:
        """Write entry to JSON file."""
        try:
            json_file = Path(self.log_file).with_suffix('.json')
            json_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Append to file
            with open(json_file, 'a') as f:
                f.write(json.dumps(entry.to_dict()) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write JSON entry: {e}")
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get cost summary for a specific session.
        
        Args:
            session_id: Session ID to summarize
            
        Returns:
            Dictionary with session cost summary
        """
        with self._lock:
            session_entries = [e for e in self._entries if e.session_id == session_id]
        
        if not session_entries:
            return {
                "session_id": session_id,
                "total_cost_usd": 0.0,
                "total_tokens": 0,
                "operation_count": 0,
                "operations": []
            }
        
        total_cost = sum(e.cost_usd for e in session_entries)
        total_input_tokens = sum(e.input_tokens for e in session_entries)
        total_output_tokens = sum(e.output_tokens for e in session_entries)
        
        return {
            "session_id": session_id,
            "total_cost_usd": round(total_cost, 6),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "operation_count": len(session_entries),
            "operations": [e.to_dict() for e in session_entries]
        }
    
    def get_total_summary(self) -> Dict[str, Any]:
        """Get total cost summary across all sessions.
        
        Returns:
            Dictionary with total cost summary
        """
        with self._lock:
            all_entries = self._entries.copy()
        
        if not all_entries:
            return {
                "total_cost_usd": 0.0,
                "total_tokens": 0,
                "operation_count": 0,
                "session_count": 0,
                "providers": {},
                "models": {}
            }
        
        total_cost = sum(e.cost_usd for e in all_entries)
        total_input_tokens = sum(e.input_tokens for e in all_entries)
        total_output_tokens = sum(e.output_tokens for e in all_entries)
        unique_sessions = set(e.session_id for e in all_entries)
        
        # Provider breakdown
        providers = {}
        for entry in all_entries:
            if entry.provider not in providers:
                providers[entry.provider] = {"cost": 0.0, "tokens": 0, "operations": 0}
            providers[entry.provider]["cost"] += entry.cost_usd
            providers[entry.provider]["tokens"] += entry.input_tokens + entry.output_tokens
            providers[entry.provider]["operations"] += 1
        
        # Model breakdown
        models = {}
        for entry in all_entries:
            model_key = f"{entry.provider}:{entry.model}"
            if model_key not in models:
                models[model_key] = {"cost": 0.0, "tokens": 0, "operations": 0}
            models[model_key]["cost"] += entry.cost_usd
            models[model_key]["tokens"] += entry.input_tokens + entry.output_tokens
            models[model_key]["operations"] += 1
        
        return {
            "total_cost_usd": round(total_cost, 6),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "operation_count": len(all_entries),
            "session_count": len(unique_sessions),
            "providers": providers,
            "models": models
        }
    
    def clear_session(self, session_id: str) -> None:
        """Clear all entries for a specific session.
        
        Args:
            session_id: Session ID to clear
        """
        with self._lock:
            self._entries = [e for e in self._entries if e.session_id != session_id]
    
    def clear_all(self) -> None:
        """Clear all cost entries."""
        with self._lock:
            self._entries.clear()
    
    def export_to_csv(self, file_path: str) -> None:
        """Export cost entries to CSV file.
        
        Args:
            file_path: Path to CSV file
        """
        import csv
        
        with self._lock:
            entries = self._entries.copy()
        
        if not entries:
            return
        
        with open(file_path, 'w', newline='') as csvfile:
            fieldnames = [
                'timestamp', 'session_id', 'operation', 'provider', 'model',
                'input_tokens', 'output_tokens', 'cost_usd', 'duration_ms'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for entry in entries:
                row = entry.to_dict()
                # Skip metadata for CSV simplicity
                row.pop('metadata', None)
                writer.writerow(row)


# Global instance for convenience
_global_cost_logger: Optional[CostLogger] = None


def get_cost_logger() -> CostLogger:
    """Get the global cost logger instance.
    
    Returns:
        Global CostLogger instance
    """
    global _global_cost_logger
    
    if _global_cost_logger is None:
        _global_cost_logger = CostLogger()
    
    return _global_cost_logger


def setup_cost_logger(log_file: Optional[str] = None, enable_console: bool = True) -> CostLogger:
    """Setup the global cost logger.
    
    Args:
        log_file: Optional file path to log costs to
        enable_console: Whether to log to console
        
    Returns:
        Configured CostLogger instance
    """
    global _global_cost_logger
    
    _global_cost_logger = CostLogger(log_file=log_file, enable_console=enable_console)
    return _global_cost_logger
