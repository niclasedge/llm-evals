"""
Data models for coding evaluations
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

class ProgrammingLanguage(Enum):
    """Supported programming languages"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    CPP = "cpp"
    C = "c"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"

class ProblemDifficulty(Enum):
    """Problem difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class TestStatus(Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"

@dataclass
class TestCase:
    """Represents a test case for code evaluation"""
    id: str
    input_data: str
    expected_output: str
    time_limit: float = 5.0  # seconds
    memory_limit: int = 128  # MB
    description: Optional[str] = None
    hidden: bool = False  # Hidden test cases not shown to user

@dataclass
class TestResult:
    """Result of running a single test case"""
    test_case_id: str
    status: TestStatus
    actual_output: Optional[str] = None
    execution_time: Optional[float] = None
    memory_usage: Optional[int] = None
    error_message: Optional[str] = None
    passed: bool = False

@dataclass
class ExecutionResult:
    """Result of code execution"""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    memory_usage: Optional[int] = None
    exit_code: Optional[int] = None

@dataclass
class CodeSubmission:
    """Represents a code submission for evaluation"""
    id: str
    code: str
    language: ProgrammingLanguage
    problem_id: str
    user_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EvaluationResult:
    """Result of code evaluation"""
    submission_id: str
    score: float  # 0.0 to 1.0
    passed_tests: int
    total_tests: int
    test_results: List[TestResult] = field(default_factory=list)
    execution_time: Optional[float] = None
    memory_usage: Optional[int] = None
    error_message: Optional[str] = None
    feedback: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class CodingProblem:
    """Represents a coding problem"""
    id: str
    title: str
    description: str
    difficulty: ProblemDifficulty
    languages: List[ProgrammingLanguage]
    test_cases: List[TestCase]
    starter_code: Dict[str, str] = field(default_factory=dict)  # language -> code
    solution: Dict[str, str] = field(default_factory=dict)  # language -> solution
    tags: List[str] = field(default_factory=list)
    time_limit: float = 5.0
    memory_limit: int = 128
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class LanguageConfig:
    """Configuration for a programming language"""
    language: ProgrammingLanguage
    executor_type: str  # 'browser', 'server', 'sandbox'
    file_extension: str
    compile_command: Optional[str] = None
    run_command: str = ""
    timeout: float = 10.0
    memory_limit: int = 256
    supported_features: List[str] = field(default_factory=list)

@dataclass
class EvaluationSession:
    """Represents an evaluation session"""
    id: str
    user_id: Optional[str] = None
    problem_id: str = ""
    language: Optional[ProgrammingLanguage] = None
    submissions: List[CodeSubmission] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed: bool = False
    best_score: float = 0.0