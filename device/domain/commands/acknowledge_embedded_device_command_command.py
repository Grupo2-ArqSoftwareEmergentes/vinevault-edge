"""Command for acknowledging embedded command execution."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AcknowledgeEmbeddedDeviceCommandCommand:
    hardware_id: str
    command_id: str
    status: str
    failure_reason: Optional[str] = None

    def __post_init__(self):
        if not self.hardware_id:
            raise ValueError("hardware_id is required")
        if not self.command_id:
            raise ValueError("command_id is required")
        if self.status not in ("EXECUTED", "FAILED"):
            raise ValueError("status must be EXECUTED or FAILED")
