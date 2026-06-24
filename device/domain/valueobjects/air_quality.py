"""AirQuality value object — represents SCD41 sensor readings.

Immutable value object containing CO2, temperature and humidity measurements.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AirQuality:
    """SCD41 air quality sensor readings.

    Attributes:
        co2: CO2 concentration in parts per million (ppm)
        temperature: Temperature in Celsius
        humidity: Relative humidity percentage (0-100)
    """
    co2: float
    temperature: float
    humidity: float

    def __post_init__(self):
        """Validate air quality values."""
        if self.co2 < 0 or self.co2 > 10000:
            raise ValueError(f"CO2 must be between 0 and 10000 ppm, got {self.co2}")
        if self.temperature < -40 or self.temperature > 85:
            raise ValueError(f"Temperature must be between -40 and 85°C, got {self.temperature}")
        if self.humidity < 0 or self.humidity > 100:
            raise ValueError(f"Humidity must be between 0 and 100%, got {self.humidity}")

    @classmethod
    def from_dict(cls, data: dict) -> "AirQuality":
        """Create AirQuality from dictionary payload."""
        return cls(
            co2=float(data.get("co2", 0)),
            temperature=float(data.get("temperature", 0)),
            humidity=float(data.get("humidity", 0)),
        )
