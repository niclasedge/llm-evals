"""
Data models for unified CLI evaluation
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from pathlib import Path


class EvaluationType(Enum):
    """Supported evaluation types"""
    CODING = "coding"
    VISION = "vision"
    TOOLS = "tools"
    INTELLIGENCE = "intelligence"
    ALL = "all"


class OutputFormat(Enum):
    """Output format options"""
    JSON = "json"
    MARKDOWN = "markdown"
    CSV = "csv"
    CONSOLE = "console"


@dataclass
class ModelSelection:
    """Model selection and filtering configuration"""
    models: List[str] = field(default_factory=list)
    providers: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    free_only: bool = False
    enabled_only: bool = True
    
    def __post_init__(self):
        """Validate model selection"""
        if not self.models and not self.providers:
            self.models = ["llama3"]  # Default model


@dataclass
class OutputConfig:
    """Output configuration"""
    format: OutputFormat = OutputFormat.CONSOLE
    file_path: Optional[Path] = None
    verbose: bool = False
    progress: bool = True
    
    def __post_init__(self):
        """Validate output configuration"""
        if self.file_path and isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)


@dataclass
class EvaluationRequest:
    """Request configuration for evaluation"""
    evaluation_type: EvaluationType
    model_selection: ModelSelection
    output_config: OutputConfig
    
    # Type-specific configurations
    problems: Optional[List[str]] = None  # For coding evaluation
    languages: Optional[List[str]] = None  # For coding evaluation
    difficulty: Optional[str] = None  # For coding evaluation
    images: Optional[List[str]] = None  # For vision evaluation
    categories: Optional[List[str]] = None  # For intelligence evaluation
    scenarios: Optional[List[str]] = None  # For tool evaluation
    
    # Common options
    timeout: int = 300  # seconds
    max_retries: int = 3
    parallel: bool = True
    
    def __post_init__(self):
        """Validate request configuration"""
        if not isinstance(self.model_selection, ModelSelection):
            raise ValueError("model_selection must be ModelSelection instance")
        if not isinstance(self.output_config, OutputConfig):
            raise ValueError("output_config must be OutputConfig instance")


@dataclass
class EvaluationMetrics:
    """Evaluation metrics and scoring"""
    accuracy: Optional[float] = None
    success_rate: Optional[float] = None
    average_time: Optional[float] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error_tests: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "accuracy": self.accuracy,
            "success_rate": self.success_rate,
            "average_time": self.average_time,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "error_tests": self.error_tests
        }


@dataclass
class ModelResult:
    """Results for a single model"""
    model_name: str
    provider: str
    model_id: str
    metrics: EvaluationMetrics
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    duration: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model result to dictionary"""
        return {
            "model_name": self.model_name,
            "provider": self.provider,
            "model_id": self.model_id,
            "metrics": self.metrics.to_dict(),
            "details": self.details,
            "errors": self.errors,
            "duration": self.duration
        }


@dataclass
class EvaluationResult:
    """Complete evaluation result"""
    evaluation_type: EvaluationType
    request: EvaluationRequest
    model_results: List[ModelResult]
    summary: Dict[str, Any]
    started_at: datetime
    completed_at: datetime
    
    @property
    def duration(self) -> float:
        """Total evaluation duration in seconds"""
        return (self.completed_at - self.started_at).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "evaluation_type": self.evaluation_type.value,
            "model_results": [result.to_dict() for result in self.model_results],
            "summary": self.summary,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration": self.duration
        }
    
    def get_best_model(self) -> Optional[ModelResult]:
        """Get the best performing model"""
        if not self.model_results:
            return None
        
        return max(self.model_results, 
                  key=lambda r: r.metrics.success_rate or 0)
    
    def get_average_metrics(self) -> EvaluationMetrics:
        """Get average metrics across all models"""
        if not self.model_results:
            return EvaluationMetrics()
        
        total_accuracy = sum(r.metrics.accuracy or 0 for r in self.model_results)
        total_success_rate = sum(r.metrics.success_rate or 0 for r in self.model_results)
        total_time = sum(r.metrics.average_time or 0 for r in self.model_results)
        total_tests = sum(r.metrics.total_tests for r in self.model_results)
        passed_tests = sum(r.metrics.passed_tests for r in self.model_results)
        failed_tests = sum(r.metrics.failed_tests for r in self.model_results)
        error_tests = sum(r.metrics.error_tests for r in self.model_results)
        
        count = len(self.model_results)
        
        return EvaluationMetrics(
            accuracy=total_accuracy / count if count > 0 else 0,
            success_rate=total_success_rate / count if count > 0 else 0,
            average_time=total_time / count if count > 0 else 0,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            error_tests=error_tests
        )


@dataclass
class ProgressUpdate:
    """Progress update for long-running evaluations"""
    current_step: int
    total_steps: int
    current_model: str
    current_test: str
    message: str
    
    @property
    def progress_percent(self) -> float:
        """Progress as percentage"""
        if self.total_steps == 0:
            return 0
        return (self.current_step / self.total_steps) * 100
    
    def __str__(self) -> str:
        """String representation of progress"""
        return f"[{self.current_step}/{self.total_steps}] {self.current_model}: {self.message}"