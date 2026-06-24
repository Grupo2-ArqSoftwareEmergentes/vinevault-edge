"""OutboxRepository — infrastructure layer for reliable outbound delivery.

Provides data access operations for OutboxEntry persistence and retrieval,
mapping between Peewee models and domain entities.
"""

from datetime import datetime, timezone
from typing import List

from device.domain.outbox_entry import OutboxEntry
from device.infrastructure.outbox.outbox_record_model import OutboxRecordModel


class OutboxRepository:
    """Repository for OutboxEntry aggregate root persistence."""

    def save(self, entry: OutboxEntry) -> OutboxEntry:
        """Persist an outbox entry to the database.

        Args:
            entry: OutboxEntry domain entity to persist.

        Returns:
            A new OutboxEntry domain entity with the database-assigned ID.
        """
        model = OutboxRecordModel.create(
            aggregate_type=entry.aggregate_type,
            aggregate_id=entry.aggregate_id,
            event_type=entry.event_type,
            status=entry.status,
            retry_count=entry.retry_count,
            next_retry_at=entry.next_retry_at,
            created_at=entry.created_at,
        )
        return self._model_to_entity(model)

    def find_pending(self, limit: int = 10) -> List[OutboxEntry]:
        """Find pending outbox entries eligible for retry.

        Args:
            limit: Maximum number of entries to fetch.

        Returns:
            List of OutboxEntry entities ordered by creation time.
        """
        now = datetime.now(timezone.utc)
        query = (
            OutboxRecordModel.select()
            .where(
                (OutboxRecordModel.status == "pending")
                & (OutboxRecordModel.next_retry_at <= now)
            )
            .order_by(OutboxRecordModel.created_at)
            .limit(limit)
        )
        return [self._model_to_entity(m) for m in query]

    def mark_sent(self, entry_id: int) -> None:
        """Mark an outbox entry as successfully sent."""
        OutboxRecordModel.update(
            status="sent",
            sent_at=datetime.now(timezone.utc),
            error_message=None,
        ).where(OutboxRecordModel.id == entry_id).execute()

    def mark_retry(
        self, entry_id: int, next_retry_at: datetime, error: str
    ) -> None:
        """Mark an outbox entry for retry with updated schedule."""
        OutboxRecordModel.update(
            status="pending",
            retry_count=OutboxRecordModel.retry_count + 1,
            next_retry_at=next_retry_at,
            error_message=error,
        ).where(OutboxRecordModel.id == entry_id).execute()

    def mark_dead_letter(self, entry_id: int, error: str) -> None:
        """Mark an outbox entry as dead letter after exhausting retries."""
        OutboxRecordModel.update(
            status="dead_letter",
            error_message=error,
        ).where(OutboxRecordModel.id == entry_id).execute()

    def delete_sent_older_than(self, before: datetime) -> int:
        """Delete sent outbox records older than the cutoff.

        Args:
            before: UTC cutoff datetime.

        Returns:
            Number of deleted rows.
        """
        return (
            OutboxRecordModel.delete()
            .where(
                (OutboxRecordModel.status == "sent")
                & (OutboxRecordModel.sent_at <= before)
            )
            .execute()
        )

    def _model_to_entity(self, model: OutboxRecordModel) -> OutboxEntry:
        """Convert a Peewee model instance to an OutboxEntry domain entity."""
        return OutboxEntry(
            id=model.id,
            aggregate_type=model.aggregate_type,
            aggregate_id=model.aggregate_id,
            event_type=model.event_type,
            status=model.status,
            retry_count=model.retry_count,
            next_retry_at=model.next_retry_at,
            created_at=model.created_at,
            sent_at=model.sent_at,
            error_message=model.error_message,
        )
