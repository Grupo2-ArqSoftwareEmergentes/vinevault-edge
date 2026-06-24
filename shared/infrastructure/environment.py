"""Shared environment configuration.

All integration with the core system is now via Kafka. Environment helpers
are stateless and context-agnostic.
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
