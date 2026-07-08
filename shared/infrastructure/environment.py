"""Shared environment configuration.

Environment helpers for Kafka, local storage, and the HTTP fallback
sync used when the device cache remains empty after startup.
"""

from __future__ import annotations

import os


def _optional(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value if value else default


def get_edge_database_path() -> str:
    return os.getenv("EDGE_DATABASE_PATH", "vinevault_edge.db").strip() or "vinevault_edge.db"


def get_edge_public_base_url() -> str:
    # Only used for docs. Do not require.
    return os.getenv("EDGE_PUBLIC_BASE_URL", "http://127.0.0.1:5000").strip() or "http://127.0.0.1:5000"


def get_core_base_url() -> str:
    """Return the core service base URL used for HTTP fallback sync."""
    return os.getenv("CORE_BASE_URL", "http://localhost:8000").strip() or "http://localhost:8000"


def get_edge_core_api_key() -> str:
    """Return the edge API key used to authenticate against the core."""
    return os.getenv("EDGE_CORE_API_KEY", "").strip()


def _clamp_int(value: str, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def get_edge_core_devices_page_size() -> int:
    """Return the page size used when syncing devices from the core."""
    raw = os.getenv("EDGE_CORE_DEVICES_PAGE_SIZE", "50").strip()
    return _clamp_int(raw, 50, 1, 500)


def get_edge_core_devices_sync_grace_seconds() -> int:
    """Return how long to wait before falling back to the core HTTP sync."""
    raw = os.getenv("EDGE_CORE_DEVICES_SYNC_GRACE_SECONDS", "15").strip()
    return _clamp_int(raw, 15, 0, 3600)


def get_edge_core_devices_sync_retry_seconds() -> int:
    """Return the interval for retrying the core HTTP fallback while empty."""
    raw = os.getenv("EDGE_CORE_DEVICES_SYNC_RETRY_SECONDS", "30").strip()
    return _clamp_int(raw, 30, 5, 3600)


def get_edge_cors_allowed_origins() -> list[str]:
    """Return allowed CORS origins.

    Use "*" for development or embedded clients with many origins. In production,
    prefer a comma-separated allowlist such as "https://admin.example.com".
    """
    value = os.getenv("EDGE_CORS_ALLOWED_ORIGINS", "*").strip()
    if not value:
        return ["*"]
    return [origin.strip() for origin in value.split(",") if origin.strip()]


def get_edge_cors_allowed_headers() -> str:
    return os.getenv(
        "EDGE_CORS_ALLOWED_HEADERS",
        "Content-Type,X-Hardware-Id,X-API-Key",
    ).strip()


def get_kafka_bootstrap_servers() -> list[str]:
    """Return Kafka bootstrap servers as a list of host:port strings.

    Defaults to localhost:9092 for development.
    """
    raw = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").strip()
    if not raw:
        return ["localhost:9092"]
    return [s.strip() for s in raw.split(",") if s.strip()]
