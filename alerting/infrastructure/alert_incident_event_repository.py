"""AlertIncidentEventRepository.

Maps ORM models to plain dicts suitable for API responses.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from peewee import DoesNotExist

from alerting.infrastructure.models import AlertIncidentEventModel


class AlertIncidentEventRepository:
    """Repository for alert incident events stored on edge."""

    @staticmethod
    def create_or_update_from_integration_payload(
        payload: dict,
        received_at: datetime,
    ) -> AlertIncidentEventModel:
        """Insert a new incident or update the existing local copy.

        The edge keeps one local record per `alert_id` + `hardware_id` so the
        same incident can move from ACTIVE to RESOLVED without duplicating rows.
        """
        alert_id = str(payload.get("alert_id") or payload.get("alertId"))
        hardware_id = str(payload["hardware_id"])
        existing = AlertIncidentEventRepository.find_by_alert_id_and_hardware_id(
            alert_id=alert_id,
            hardware_id=hardware_id,
        )

        if existing is None:
            return AlertIncidentEventModel.create(
                hardware_id=hardware_id,
                alert_id=alert_id,
                device_id=str(payload.get("device_id") or payload.get("deviceId")),
                space_id=str(payload.get("space_id") or payload.get("spaceId")) if (payload.get("space_id") or payload.get("spaceId")) else None,
                metric=str(payload.get("metric")),
                threshold_metric=str(payload.get("threshold_metric") or payload.get("thresholdMetric")) if (payload.get("threshold_metric") or payload.get("thresholdMetric")) else None,
                status=str(payload.get("status")),
                message=payload.get("message"),
                threshold_value=str(payload.get("threshold_value")) if payload.get("threshold_value") is not None else None,
                actual_value=str(payload.get("actual_value")) if payload.get("actual_value") is not None else None,
                occurred_at=payload["occurred_at"],
                resolved_at=payload.get("resolved_at"),
                received_at=received_at,
                delivered_at=None,
                acknowledged_at=None,
            )

        previous_status = existing.status
        existing.device_id = str(payload.get("device_id") or payload.get("deviceId"))
        existing.space_id = str(payload.get("space_id") or payload.get("spaceId")) if (payload.get("space_id") or payload.get("spaceId")) else None
        existing.metric = str(payload.get("metric"))
        existing.threshold_metric = (
            str(payload.get("threshold_metric") or payload.get("thresholdMetric"))
            if (payload.get("threshold_metric") or payload.get("thresholdMetric"))
            else None
        )
        existing.status = str(payload.get("status"))
        existing.message = payload.get("message")
        existing.threshold_value = str(payload.get("threshold_value")) if payload.get("threshold_value") is not None else None
        existing.actual_value = str(payload.get("actual_value")) if payload.get("actual_value") is not None else None
        existing.occurred_at = payload["occurred_at"]
        existing.received_at = received_at

        if existing.status == "RESOLVED":
            existing.resolved_at = payload.get("resolved_at") or received_at
        else:
            existing.resolved_at = None

        # Any status transition should become visible to the embedded device again.
        # That lets ACTIVE -> RESOLVED and RESOLVED -> ACTIVE both re-enter the pull queue.
        if previous_status != existing.status:
            existing.delivered_at = None

        existing.save()
        return existing

    @staticmethod
    def find_by_alert_id_and_hardware_id(alert_id: str, hardware_id: str) -> AlertIncidentEventModel | None:
        try:
            return AlertIncidentEventModel.get(
                (AlertIncidentEventModel.alert_id == str(alert_id))
                & (AlertIncidentEventModel.hardware_id == str(hardware_id))
            )
        except DoesNotExist:
            return None

    @staticmethod
    def find_pending_for_hardware_id(hardware_id: str, limit: int = 50) -> list[AlertIncidentEventModel]:
        return list(
            AlertIncidentEventModel.select()
            .where(
                (AlertIncidentEventModel.hardware_id == hardware_id)
                & (AlertIncidentEventModel.status.in_(["ACTIVE", "RESOLVED"]))
                & (AlertIncidentEventModel.delivered_at.is_null(True))
            )
            .order_by(AlertIncidentEventModel.received_at.asc())
            .limit(limit)
        )

    @staticmethod
    def mark_delivered(event: AlertIncidentEventModel, delivered_at: Optional[datetime] = None) -> None:
        event.delivered_at = delivered_at or datetime.now(timezone.utc)
        event.save()

    @staticmethod
    def acknowledge(event_id: int, hardware_id: str, acknowledged_at: Optional[datetime] = None) -> AlertIncidentEventModel:
        try:
            event = AlertIncidentEventModel.get(
                (AlertIncidentEventModel.id == event_id) & (AlertIncidentEventModel.hardware_id == hardware_id)
            )
        except DoesNotExist as exc:
            raise ValueError("Unknown alert incident event") from exc

        event.acknowledged_at = acknowledged_at or datetime.now(timezone.utc)
        event.save()
        return event
