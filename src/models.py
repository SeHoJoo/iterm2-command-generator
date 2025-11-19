"""Data models for iTerm2 AI Command Generator."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid


class RiskLevel(Enum):
    """Risk level for generated commands."""
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"


@dataclass
class RiskResult:
    """Result of risk analysis."""
    level: RiskLevel
    reasons: List[str] = field(default_factory=list)


@dataclass
class PromptRequest:
    """User's natural language request."""
    user_input: str
    working_directory: str
    shell_type: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.user_input or len(self.user_input) > 500:
            raise ValueError("user_input must be 1-500 characters")
        if self.shell_type not in ("bash", "zsh", "sh", "fish"):
            raise ValueError(f"Invalid shell_type: {self.shell_type}")


@dataclass
class GeneratedCommand:
    """AI-generated shell command."""
    command: str
    request_id: str
    risk_level: RiskLevel = RiskLevel.SAFE
    explanation: Optional[str] = None
    risk_reasons: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.command:
            raise ValueError("command cannot be empty")


@dataclass
class CommandHistory:
    """Stored command history entry."""
    prompt: str
    command: str
    alias: Optional[str] = None
    use_count: int = 1
    last_used: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "prompt": self.prompt,
            "command": self.command,
            "alias": self.alias,
            "use_count": self.use_count,
            "last_used": self.last_used.isoformat(),
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CommandHistory":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            prompt=data["prompt"],
            command=data["command"],
            alias=data.get("alias"),
            use_count=data.get("use_count", 1),
            last_used=datetime.fromisoformat(data["last_used"]),
            created_at=datetime.fromisoformat(data["created_at"])
        )


@dataclass
class AppConfig:
    """Application configuration."""
    api_key_service: str = "iterm2-ai-generator"
    api_key_account: str = "gemini-api-key"
    shortcut_key: str = "Ctrl+Shift+A"
    max_history: int = 50
    max_input_length: int = 500
