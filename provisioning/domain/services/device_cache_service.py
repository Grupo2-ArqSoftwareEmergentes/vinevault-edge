class DeviceCacheService:
    """Domain service for validating device cache records."""

    @staticmethod
    def validate_device_record(device):
        """Validate the minimum core system fields needed by the edge cache."""
        for field in ("device_id", "hardware_id", "api_key", "status"):
            if not device.get(field):
                raise ValueError(f"{field} is required")
