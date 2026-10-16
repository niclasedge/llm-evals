"""Database models for LLM providers and models."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from sqlalchemy import DateTime
from enum import Enum


class ProviderType(str, Enum):
    """Provider type enumeration."""
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    OPENAI = "openai"


class Provider(SQLModel, table=True):
    """LLM provider configuration."""

    __tablename__ = "providers"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    type: ProviderType
    base_url: str
    api_key_env: Optional[str] = None
    is_active: bool = True
    config: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))

    # Relationships
    models: List["Model"] = Relationship(back_populates="provider")


class Model(SQLModel, table=True):
    """LLM model configuration."""

    __tablename__ = "models"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    model_id: str = Field(index=True)  # Provider-specific model ID
    provider_id: int = Field(foreign_key="providers.id")

    # Model metadata
    aliases: List[str] = Field(default=[], sa_column=Column(JSON))
    capabilities: List[str] = Field(default=[], sa_column=Column(JSON))  # text, vision, code, reasoning
    is_free: bool = True
    is_enabled: bool = True
    context_length: Optional[int] = None
    description: Optional[str] = None

    # Performance tracking
    avg_response_time: Optional[float] = None
    success_rate: Optional[float] = None
    last_tested: Optional[datetime] = Field(default=None, sa_column=Column(DateTime))

    metadata_: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), alias="metadata")

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime))

    # Relationships
    provider: Provider = Relationship(back_populates="models")

    def __str__(self) -> str:
        return f"{self.provider.name}/{self.name}"