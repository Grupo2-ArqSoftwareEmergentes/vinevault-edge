"""HTTP client for fetching devices from the core service."""

from __future__ import annotations

import json
from urllib import parse, request

from shared.infrastructure.environment import get_core_base_url, get_edge_core_api_key


class CoreDevicesClient:
    """Client for the core /api/v1/edges/devices endpoint."""

    def __init__(self) -> None:
        self.base_url = get_core_base_url().rstrip("/")
        self.api_key = get_edge_core_api_key()

    def is_configured(self) -> bool:
        """Return True when the client can authenticate against the core."""
        return bool(self.base_url and self.api_key)

    def fetch_page(self, page: int, size: int) -> tuple[list[dict], dict]:
        """Fetch a single paginated page from the core."""
        query = parse.urlencode({"page": page, "size": size})
        url = f"{self.base_url}/api/v1/edges/devices?{query}"
        req = request.Request(
            url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            method="GET",
        )

        with request.urlopen(req, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))

        return self._extract_items(payload), self._extract_meta(payload)

    @staticmethod
    def _extract_items(payload) -> list[dict]:
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []

        for key in ("content", "items", "results", "data"):
            items = payload.get(key)
            if isinstance(items, list):
                return items

        return []

    @staticmethod
    def _extract_meta(payload) -> dict:
        if isinstance(payload, dict):
            return payload
        return {}
