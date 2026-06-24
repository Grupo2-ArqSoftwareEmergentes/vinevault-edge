"""IAM domain services.

Contains authentication business rules that operate on the Device entity.
"""


class AuthService:
    """Domain service for device authentication logic.

    Encapsulates the business rule: a device can authenticate when
    it exists and has not been decommissioned in the core system.
    """

    @staticmethod
    def authenticate(device):
        """Verify that a device is allowed to authenticate.

        Args:
            device: A Device entity instance, or None if not found.

        Returns:
            True if device is not None and status is not DECOMMISSIONED.
        """
        return device is not None and device.status != "DECOMMISSIONED"
