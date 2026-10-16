"""
Monitoring and Logging System for LLM Evaluations
"""

import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field
from contextlib import contextmanager
from functools import wraps
import asyncio


@dataclass
class PerformanceMetrics:
    """Performance metrics for evaluation runs"""
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    requests_count: int = 0
    errors_count: int = 0
    success_rate: float = 0.0
    throughput: float = 0.0
    average_response_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationEvent:
    """Event data for evaluation monitoring"""
    event_type: str
    timestamp: datetime
    model_provider: str
    model_name: str
    test_name: str
    duration: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class StructuredLogger:
    """Structured logging with JSON output"""
    
    def __init__(self, name: str, log_file: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def log_event(self, event: EvaluationEvent):
        """Log an evaluation event"""
        event_data = {
            'event_type': event.event_type,
            'timestamp': event.timestamp.isoformat(),
            'model_provider': event.model_provider,
            'model_name': event.model_name,
            'test_name': event.test_name,
            'duration': event.duration,
            'success': event.success,
            'error_message': event.error_message,
            'metadata': event.metadata
        }
        
        if event.success:
            self.logger.info(json.dumps(event_data))
        else:
            self.logger.error(json.dumps(event_data))
    
    def log_performance(self, metrics: PerformanceMetrics, context: str = ""):
        """Log performance metrics"""
        perf_data = {
            'context': context,
            'duration': metrics.duration,
            'memory_usage': metrics.memory_usage,
            'cpu_usage': metrics.cpu_usage,
            'requests_count': metrics.requests_count,
            'errors_count': metrics.errors_count,
            'success_rate': metrics.success_rate,
            'throughput': metrics.throughput,
            'average_response_time': metrics.average_response_time,
            'metadata': metrics.metadata
        }
        self.logger.info(f"PERFORMANCE: {json.dumps(perf_data)}")
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log info message"""
        if extra:
            self.logger.info(f"{message} - {json.dumps(extra)}")
        else:
            self.logger.info(message)
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log error message"""
        if extra:
            self.logger.error(f"{message} - {json.dumps(extra)}")
        else:
            self.logger.error(message)
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log warning message"""
        if extra:
            self.logger.warning(f"{message} - {json.dumps(extra)}")
        else:
            self.logger.warning(message)


class PerformanceMonitor:
    """Monitor performance metrics during evaluation runs"""
    
    def __init__(self):
        self.current_metrics = PerformanceMetrics()
        self.events: List[EvaluationEvent] = []
        self.active_timers: Dict[str, float] = {}
    
    def start_timer(self, name: str):
        """Start a named timer"""
        self.active_timers[name] = time.time()
    
    def stop_timer(self, name: str) -> float:
        """Stop a named timer and return duration"""
        if name in self.active_timers:
            duration = time.time() - self.active_timers[name]
            del self.active_timers[name]
            return duration
        return 0.0
    
    @contextmanager
    def timer(self, name: str):
        """Context manager for timing operations"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.record_operation(name, duration)
    
    def record_operation(self, operation_name: str, duration: float, success: bool = True):
        """Record an operation with its duration"""
        self.current_metrics.requests_count += 1
        if not success:
            self.current_metrics.errors_count += 1
        
        # Update average response time
        if self.current_metrics.requests_count > 0:
            total_time = self.current_metrics.average_response_time * (self.current_metrics.requests_count - 1)
            self.current_metrics.average_response_time = (total_time + duration) / self.current_metrics.requests_count
    
    def add_event(self, event: EvaluationEvent):
        """Add an evaluation event"""
        self.events.append(event)
    
    def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics"""
        if self.current_metrics.requests_count > 0:
            self.current_metrics.success_rate = (
                (self.current_metrics.requests_count - self.current_metrics.errors_count) / 
                self.current_metrics.requests_count
            )
            
            if self.current_metrics.duration > 0:
                self.current_metrics.throughput = self.current_metrics.requests_count / self.current_metrics.duration
        
        return self.current_metrics
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.current_metrics = PerformanceMetrics()
        self.events.clear()
        self.active_timers.clear()


class EvaluationMonitor:
    """Main monitoring system for LLM evaluations"""
    
    def __init__(self, log_file: Optional[str] = None):
        self.logger = StructuredLogger("llm_evaluation", log_file)
        self.performance_monitor = PerformanceMonitor()
        self.session_start_time = time.time()
        
        # LLM CLI specific tracking
        self.llm_cli_operations = []
        self.provider_performance = {}
    
    def start_session(self, session_id: str, config: Dict[str, Any]):
        """Start a new evaluation session"""
        self.logger.info("Starting evaluation session", {
            'session_id': session_id,
            'config': config
        })
        self.session_start_time = time.time()
        self.performance_monitor.reset_metrics()
    
    def end_session(self, session_id: str):
        """End evaluation session"""
        duration = time.time() - self.session_start_time
        metrics = self.performance_monitor.get_metrics()
        
        self.logger.info("Ending evaluation session", {
            'session_id': session_id,
            'duration': duration,
            'metrics': {
                'requests_count': metrics.requests_count,
                'errors_count': metrics.errors_count,
                'success_rate': metrics.success_rate,
                'average_response_time': metrics.average_response_time
            }
        })
        
        self.logger.log_performance(metrics, f"Session {session_id}")
    
    def log_evaluation_start(self, model_provider: str, model_name: str, test_name: str):
        """Log start of individual evaluation"""
        event = EvaluationEvent(
            event_type="evaluation_start",
            timestamp=datetime.now(),
            model_provider=model_provider,
            model_name=model_name,
            test_name=test_name,
            duration=0.0,
            success=True
        )
        self.logger.log_event(event)
        self.performance_monitor.add_event(event)
    
    def log_evaluation_end(self, model_provider: str, model_name: str, test_name: str, 
                          duration: float, success: bool, error_message: Optional[str] = None):
        """Log end of individual evaluation"""
        event = EvaluationEvent(
            event_type="evaluation_end",
            timestamp=datetime.now(),
            model_provider=model_provider,
            model_name=model_name,
            test_name=test_name,
            duration=duration,
            success=success,
            error_message=error_message
        )
        self.logger.log_event(event)
        self.performance_monitor.add_event(event)
        self.performance_monitor.record_operation(f"{model_provider}/{model_name}/{test_name}", duration, success)
    
    def log_error(self, error_message: str, context: Dict[str, Any]):
        """Log an error with context"""
        self.logger.error(error_message, context)
    
    def log_warning(self, warning_message: str, context: Dict[str, Any]):
        """Log a warning with context"""
        self.logger.warning(warning_message, context)
    
    def log_info(self, info_message: str, context: Optional[Dict[str, Any]] = None):
        """Log an info message"""
        self.logger.info(info_message, context)
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics"""
        return self.performance_monitor.get_metrics()
    
    def get_events(self) -> List[EvaluationEvent]:
        """Get all recorded events"""
        return self.performance_monitor.events.copy()
    
    def log_llm_cli_operation(self, operation: str, model: str, duration: float, success: bool, metadata: Dict[str, Any] = None):
        """
        Log LLM CLI-specific operation metrics
        
        Args:
            operation: Operation type (generate, vision_query, etc.)
            model: Model name
            duration: Operation duration
            success: Whether operation succeeded
            metadata: Additional metadata
        """
        operation_data = {
            'operation': operation,
            'model': model,
            'duration': duration,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        self.llm_cli_operations.append(operation_data)
        
        # Log to main logger
        self.logger.info(f"LLM CLI operation: {operation}", {
            'model': model,
            'duration': duration,
            'success': success,
            'operation_type': 'llm_cli'
        })
        
        # Record in performance monitor
        self.performance_monitor.record_operation(f"llm_cli_{operation}", duration, success)
    
    def track_provider_performance(self, provider: str, model: str, metrics: Dict[str, Any]):
        """
        Track performance metrics for specific provider/model combinations
        
        Args:
            provider: Provider name (llm_cli, openrouter, ollama)
            model: Model name
            metrics: Performance metrics dictionary
        """
        if provider not in self.provider_performance:
            self.provider_performance[provider] = {}
        
        if model not in self.provider_performance[provider]:
            self.provider_performance[provider][model] = []
        
        metrics['timestamp'] = datetime.now().isoformat()
        self.provider_performance[provider][model].append(metrics)
        
        self.logger.info(f"Provider performance tracked: {provider}/{model}", {
            'provider': provider,
            'model': model,
            'metrics': metrics
        })
    
    def log_subprocess_error(self, command: List[str], error: str, context: Dict[str, Any]):
        """
        Log subprocess-related errors (mainly for LLM CLI)
        
        Args:
            command: The command that failed
            error: Error message
            context: Additional context
        """
        self.logger.error(f"Subprocess error: {' '.join(command)}", {
            'command': command,
            'error': error,
            'context': context,
            'operation_type': 'subprocess'
        })
    
    def get_llm_cli_metrics(self) -> Dict[str, Any]:
        """Get LLM CLI-specific metrics"""
        if not self.llm_cli_operations:
            return {}
        
        total_operations = len(self.llm_cli_operations)
        successful_operations = sum(1 for op in self.llm_cli_operations if op['success'])
        
        durations = [op['duration'] for op in self.llm_cli_operations]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            'total_operations': total_operations,
            'successful_operations': successful_operations,
            'success_rate': successful_operations / total_operations if total_operations > 0 else 0,
            'average_duration': avg_duration,
            'operations_by_type': self._group_operations_by_type(),
            'recent_operations': self.llm_cli_operations[-10:]  # Last 10 operations
        }
    
    def _group_operations_by_type(self) -> Dict[str, Dict[str, Any]]:
        """Group LLM CLI operations by type for analysis"""
        operations_by_type = {}
        
        for op in self.llm_cli_operations:
            op_type = op['operation']
            if op_type not in operations_by_type:
                operations_by_type[op_type] = {
                    'count': 0,
                    'success_count': 0,
                    'total_duration': 0,
                    'models': set()
                }
            
            operations_by_type[op_type]['count'] += 1
            operations_by_type[op_type]['models'].add(op['model'])
            operations_by_type[op_type]['total_duration'] += op['duration']
            
            if op['success']:
                operations_by_type[op_type]['success_count'] += 1
        
        # Convert sets to lists for JSON serialization
        for op_type in operations_by_type:
            operations_by_type[op_type]['models'] = list(operations_by_type[op_type]['models'])
            operations_by_type[op_type]['average_duration'] = (
                operations_by_type[op_type]['total_duration'] / 
                operations_by_type[op_type]['count']
            )
            operations_by_type[op_type]['success_rate'] = (
                operations_by_type[op_type]['success_count'] / 
                operations_by_type[op_type]['count']
            )
        
        return operations_by_type
    
    def get_provider_performance_summary(self) -> Dict[str, Any]:
        """Get summary of provider performance"""
        return {
            'providers': list(self.provider_performance.keys()),
            'provider_metrics': self.provider_performance.copy(),
            'llm_cli_metrics': self.get_llm_cli_metrics()
        }


def timed_operation(monitor: EvaluationMonitor, operation_name: str):
    """Decorator to time operations"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                monitor.performance_monitor.record_operation(operation_name, duration, True)
                return result
            except Exception as e:
                duration = time.time() - start_time
                monitor.performance_monitor.record_operation(operation_name, duration, False)
                monitor.log_error(f"Operation {operation_name} failed: {str(e)}", {
                    'operation': operation_name,
                    'duration': duration,
                    'args': str(args),
                    'kwargs': str(kwargs)
                })
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                monitor.performance_monitor.record_operation(operation_name, duration, True)
                return result
            except Exception as e:
                duration = time.time() - start_time
                monitor.performance_monitor.record_operation(operation_name, duration, False)
                monitor.log_error(f"Operation {operation_name} failed: {str(e)}", {
                    'operation': operation_name,
                    'duration': duration,
                    'args': str(args),
                    'kwargs': str(kwargs)
                })
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Global monitor instance
_monitor = None


def get_monitor() -> EvaluationMonitor:
    """Get global monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = EvaluationMonitor("logs/evaluation.log")
    return _monitor