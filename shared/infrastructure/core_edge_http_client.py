"""HTTP client for edge -> core communication.

This client speaks the contract defined by the edge roadmap:

- POST /api/v1/edges/devices/presence
- POST /api/v1/edges/devices/commands/ack
- POST /api/v1/edges/devices/telemetry
"""

from __future__ import annotations

import json
import logging
from urllib import error, request

from shared.infrastructure.environment import (
    get_core_base_url,
    get_edge_core_api_key,
    get_edge_core_http_timeout_seconds,
)

logger = logging.getLogger(__name__)


class CoreEdgeHttpClient:
    """Best-effort HTTP client for reporting edge events to the core."""

    def __init__(self) -> None:
        self.base_url = get_core_base_url().rstrip("/")
        self.api_key = get_edge_core_api_key()
        self.timeout_seconds = get_edge_core_http_timeout_seconds()

    def is_configured(self) -> bool:
        """Return True when the client has the minimum data to call the core."""
        return bool(self.base_url and self.api_key)

    def publish_presence(self, payload: dict) -> bool:
        """POST a device presence update to the core."""
        return self._post_json("/api/v1/edges/devices/presence", payload)

    def publish_command_ack(self, payload: dict) -> bool:
        """POST a command acknowledgement to the core."""
        return self._post_json("/api/v1/edges/devices/commands/ack", payload)

    def publish_telemetry(self, payload: dict) -> bool:
        """POST telemetry to the core."""
        return self._post_json("/api/v1/edges/devices/telemetry", payload)

    def _post_json(self, path: str, payload: dict) -> bool:
        if not self.is_configured():
            logger.debug("Core HTTP client skipped because CORE_BASE_URL or EDGE_CORE_API_KEY is missing")
            return False

        url = f"{self.base_url}{path}"
        body = json.dumps(payload, default=str).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                status = getattr(response, "status", response.getcode())
                if 200 <= int(status) < 300:
                    return True

                logger.warning(
                    "Core HTTP %s returned unexpected status %s",
                    path,
                    status,
                )
                return False
        except error.HTTPError as exc:
            logger.warning(
                "Core HTTP %s failed with status %s",
                path,
                exc.code,
            )
            return False
        except error.URLError as exc:
            logger.warning("Core HTTP %s unavailable: %s", path, exc)
            return False
        except Exception as exc:
            logger.warning("Unexpected core HTTP error on %s: %s", path, exc)
            return False
