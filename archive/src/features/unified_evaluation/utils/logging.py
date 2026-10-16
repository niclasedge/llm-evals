"""
Logging utilities for unified evaluation

This module provides logging setup and utilities for the unified evaluation system.
"""

import logging
import sys
from typing import Optional
from pathlib import Path
from datetime import datetime


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    verbose: bool = False,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up logging for unified evaluation
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        verbose: Whether to enable verbose logging
        format_string: Custom format string for log messages
        
    Returns:
        Configured logger instance
    """
    # Convert level string to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger('unified_evaluation')
    logger.setLevel(numeric_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Default format
    if format_string is None:
        if verbose:
            format_string = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        else:
            format_string = '%(asctime)s - %(levelname)s - %(message)s'
    
    formatter = logging.Formatter(format_string)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = 'unified_evaluation') -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class EvaluationLogger:
    """
    Specialized logger for evaluation operations
    
    This class provides convenient logging methods for evaluation-specific
    operations with structured logging support.
    """
    
    def __init__(self, name: str = 'unified_evaluation', log_file: Optional[str] = None):
        """
        Initialize evaluation logger
        
        Args:
            name: Logger name
            log_file: Optional log file path
        """
        self.logger = setup_logging(log_file=log_file)
        self.name = name
        
    def log_evaluation_start(self, eval_type: str, models: list, config: dict):
        """Log evaluation start"""
        self.logger.info(f"Starting {eval_type} evaluation")
        self.logger.info(f"Models: {', '.join(models)}")
        self.logger.debug(f"Configuration: {config}")
    
    def log_evaluation_complete(self, eval_type: str, duration: float, results: dict):
        """Log evaluation completion"""
        self.logger.info(f"Completed {eval_type} evaluation in {duration:.2f}s")
        self.logger.info(f"Results summary: {results}")
    
    def log_model_start(self, model_name: str, provider: str):
        """Log model evaluation start"""
        self.logger.info(f"Starting evaluation for {model_name} ({provider})")
    
    def log_model_complete(self, model_name: str, duration: float, success_rate: float):
        """Log model evaluation completion"""
        self.logger.info(f"Completed {model_name} evaluation in {duration:.2f}s - Success rate: {success_rate:.1%}")
    
    def log_model_error(self, model_name: str, error: str):
        """Log model evaluation error"""
        self.logger.error(f"Error evaluating {model_name}: {error}")
    
    def log_test_result(self, test_name: str, model_name: str, result: dict):
        """Log individual test result"""
        status = result.get('status', 'unknown')
        score = result.get('score', 0)
        self.logger.debug(f"Test {test_name} on {model_name}: {status} (score: {score})")
    
    def log_progress(self, current: int, total: int, message: str):
        """Log progress update"""
        percentage = (current / total) * 100 if total > 0 else 0
        self.logger.debug(f"Progress: {current}/{total} ({percentage:.1f}%) - {message}")
    
    def log_warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
    
    def log_error(self, message: str, exception: Optional[Exception] = None):
        """Log error message"""
        self.logger.error(message)
        if exception:
            self.logger.exception(exception)
    
    def log_debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
    
    def log_info(self, message: str):
        """Log info message"""
        self.logger.info(message)


class StructuredLogger:
    """
    Structured logger for JSON-formatted logs
    
    This class provides structured logging with JSON format,
    useful for log analysis and monitoring.
    """
    
    def __init__(self, name: str = 'unified_evaluation_structured'):
        """
        Initialize structured logger
        
        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # JSON formatter
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
        )
        
        # Console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_structured(self, event_type: str, data: dict):
        """
        Log structured event
        
        Args:
            event_type: Type of event
            data: Event data
        """
        import json
        
        structured_data = {
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        self.logger.info(json.dumps(structured_data))
    
    def log_evaluation_event(self, event_type: str, model_name: str, eval_type: str, data: dict):
        """Log evaluation-specific event"""
        self.log_structured(event_type, {
            'model_name': model_name,
            'evaluation_type': eval_type,
            **data
        })
    
    def log_performance_metric(self, metric_name: str, value: float, model_name: str, eval_type: str):
        """Log performance metric"""
        self.log_structured('performance_metric', {
            'metric_name': metric_name,
            'value': value,
            'model_name': model_name,
            'evaluation_type': eval_type
        })
    
    def log_error_event(self, error_type: str, error_message: str, model_name: str, eval_type: str):
        """Log error event"""
        self.log_structured('error', {
            'error_type': error_type,
            'error_message': error_message,
            'model_name': model_name,
            'evaluation_type': eval_type
        })


def create_timestamped_log_file(base_name: str = "evaluation", extension: str = "log") -> str:
    """
    Create a timestamped log file name
    
    Args:
        base_name: Base name for the log file
        extension: File extension
        
    Returns:
        Timestamped log file path
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"logs/{base_name}_{timestamp}.{extension}"


def configure_evaluation_logging(verbose: bool = False, log_file: Optional[str] = None) -> EvaluationLogger:
    """
    Configure logging for evaluation operations
    
    Args:
        verbose: Whether to enable verbose logging
        log_file: Optional log file path
        
    Returns:
        Configured evaluation logger
    """
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    # Create timestamped log file if none provided
    if log_file is None:
        log_file = create_timestamped_log_file()
    
    # Setup logging
    level = "DEBUG" if verbose else "INFO"
    setup_logging(level=level, log_file=log_file, verbose=verbose)
    
    return EvaluationLogger(log_file=log_file)