"""Database models for test configurations."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlmodel import SQLModel, Field, JSON, Column, Relationship
from sqlalchemy import DateTime, Text
from enum import Enum


class TestType(str, Enum):
    """Test type enumeration."""
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"
    VISION = "vision"
    MATH = "math"
    CREATIVE = "creative"


class DifficultyLevel(str, Enum):
    """Test difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class TestCategory(SQLModel, table=True):
    """Test category for organizing tests."""

    __tablename__ = "test_categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: str
    test_type: TestType
    is_active: bool = True

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))

    # Relationships
    test_configs: List["TestConfig"] = Relationship(back_populates="category")


class TestConfig(SQLModel, table=True):
    """Individual test configuration."""

    __tablename__ = "test_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    category_id: int = Field(foreign_key="test_categories.id")

    # Test content
    prompt: str = Field(sa_column=Column(Text))
    system_prompt: Optional[str] = Field(default=None, sa_column=Column(Text))
    expected_output: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Test metadata
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    tags: List[str] = Field(default=[], sa_column=Column(JSON))
    timeout: int = 30  # seconds
    max_tokens: Optional[int] = None
    temperature: float = 0.7

    # Evaluation criteria
    evaluation_prompt: Optional[str] = Field(default=None, sa_column=Column(Text))
    evaluation_criteria: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    is_active: bool = True

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))

    # Relationships
    category: TestCategory = Relationship(back_populates="test_configs")