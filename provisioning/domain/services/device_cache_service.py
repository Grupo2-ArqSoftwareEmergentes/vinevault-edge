class DeviceCacheService:
    """Domain service for validating device cache records."""

    @staticmethod
    def validate_device_record(device, require_api_key: bool = True):
        """Validate the minimum core system fields needed by the edge cache."""
        required_fields = ["device_id", "hardware_id", "status"]
        if require_api_key:
            required_fields.append("api_key")

        for field in required_fields:
            if not device.get(field):
                raise ValueError(f"{field} is required")
