"""Location value object — represents device geographical location.

Immutable value object containing location information.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    """Device location information.

    Attributes:
        country: Country name where the device is located (e.g., "Peru")
    """
    country: str = ""

    def __post_init__(self):
        """Validate location data."""
        # country is optional, so no validation needed for empty string

    @classmethod
    def from_dict(cls, data: dict) -> "Location":
        """Create Location from dictionary payload."""
        return cls(
            country=str(data.get("country", ""))
        )
