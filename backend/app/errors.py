from __future__ import annotations

import uuid
from typing import Any


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        action: str,
        **extra: Any,
    ) -> None:
        self.status_code = status_code
        self.payload = {
            "code": code,
            "message": message,
            "action": action,
            "request_id": str(uuid.uuid4()),
            **extra,
        }
        super().__init__(message)
