from dataclasses import dataclass
from typing import Any


@dataclass
class ServiceResult:
    success: bool
    data: dict[str, Any] | None = None
    error_type: str | None = None
    request: str | None = None
    response: str | None = None


@dataclass
class RequestMeta:
    trace_id: str
    provider: str
    capability: str
