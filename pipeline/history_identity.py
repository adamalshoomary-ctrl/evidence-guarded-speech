"""Stable durable identity helpers for longitudinal history records."""


def durable_history_scope(record):
    """Return the account and declared context scope, or None for legacy data."""
    if not isinstance(record, dict):
        return None
    account_id = record.get("account_id")
    context_id = record.get("context_id")
    if not account_id or not context_id:
        return None
    return account_id, context_id


def records_for_scope(records, current_record):
    """Select only records for the same durable account and context."""
    scope = durable_history_scope(current_record)
    if scope is None:
        return []
    return [
        record for record in records
        if durable_history_scope(record) == scope
    ]
