"""Database models for test results and evaluations."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlmodel import SQLModel, Field, JSON, Column, Relationship
from sqlalchemy import DateTime, Text
from enum import Enum


class TestStatus(str, Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class EvaluationStatus(str, Enum):
    """Evaluation status."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class TestRun(SQLModel, table=True):
    """Test execution session."""

    __tablename__ = "test_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None

    # Configuration
    test_config_ids: List[int] = Field(default=[], sa_column=Column(JSON))
    model_ids: List[int] = Field(default=[], sa_column=Column(JSON))

    # Status tracking
    status: TestStatus = TestStatus.PENDING
    total_tests: int = 0
    completed_tests: int = 0
    failed_tests: int = 0

    # Timing
    started_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    completed_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    duration: Optional[float] = None  # seconds

    # Metadata
    metadata_: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), alias="metadata")

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))

    # Relationships
    test_results: List["TestResult"] = Relationship(back_populates="test_run")


class TestResult(SQLModel, table=True):
    """Individual test result."""

    __tablename__ = "test_results"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(foreign_key="test_runs.id")
    test_config_id: int = Field(foreign_key="test_configs.id")
    model_id: int = Field(foreign_key="models.id")

    # Test execution
    status: TestStatus = TestStatus.PENDING
    prompt: str = Field(sa_column=Column(Text))
    response: Optional[str] = Field(default=None, sa_column=Column(Text))
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Performance metrics
    response_time: Optional[float] = None  # seconds
    tokens_used: Optional[int] = None
    cost: Optional[float] = None

    # Timing
    started_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))
    completed_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))

    # Raw response data
    raw_response: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))

    # Relationships
    test_run: TestRun = Relationship(back_populates="test_results")
    evaluations: List["Evaluation"] = Relationship(back_populates="test_result")


class Evaluation(SQLModel, table=True):
    """LLM-based evaluation of test results."""

    __tablename__ = "evaluations"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_result_id: int = Field(foreign_key="test_results.id")
    evaluator_model_id: int = Field(foreign_key="models.id")

    # Evaluation details
    status: EvaluationStatus = EvaluationStatus.PENDING
    evaluation_prompt: str = Field(sa_column=Column(Text))
    evaluation_response: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Scores (0.0 to 1.0)
    overall_score: Optional[float] = None
    accuracy_score: Optional[float] = None
    relevance_score: Optional[float] = None
    creativity_score: Optional[float] = None
    coherence_score: Optional[float] = None

    # Detailed evaluation
    strengths: List[str] = Field(default=[], sa_column=Column(JSON))
    weaknesses: List[str] = Field(default=[], sa_column=Column(JSON))
    suggestions: List[str] = Field(default=[], sa_column=Column(JSON))

    # Evaluation metadata
    evaluation_criteria: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    metadata_: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), alias="metadata")

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))

    # Relationships
    test_result: TestResult = Relationship(back_populates="evaluations")