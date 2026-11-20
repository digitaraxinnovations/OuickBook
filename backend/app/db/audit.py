"""
The audit log: every time a main record (customer, invoice, bill, account,
setting...) is created, changed or deleted, a row is written to audit_log
with who did it and which fields changed.

It hooks into SQLAlchemy's "after flush" event, so no service has to call
it - nothing can be saved without being logged. Detail rows (invoice
lines, journal lines...) are not logged on their own; their parent is.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import event, inspect, insert
from sqlalchemy.orm import Session

from app.core.request_context import current_user_id

# Model class name -> (label shown in the log, attribute used as its name)
AUDITED = {
    "Account": ("Account", "name"),
    "Customer": ("Customer", "display_name"),
    "Vendor": ("Vendor", "display_name"),
    "Employee": ("Employee", "display_name"),
    "Product": ("Product or service", "name"),
    "Invoice": ("Invoice", "invoice_number"),
    "SalesDocument": ("Sales form", "doc_number"),
    "Payment": ("Payment", "reference_no"),
    "BankDeposit": ("Bank deposit", None),
    "Expense": ("Expense", "reference_no"),
    "PurchaseDocument": ("Vendor form", "doc_number"),
    "BillPayment": ("Bill payment", "check_number"),
    "JournalEntry": ("Journal entry", "memo"),
    "Transfer": ("Transfer", "memo"),
    "BankRule": ("Bank rule", "name"),
    "Reconciliation": ("Reconciliation", None),
    "TaxAgency": ("Tax agency", "name"),
    "TaxRate": ("Tax rate", "name"),
    "SalesTaxPayment": ("Sales tax payment", None),
    "InventoryAdjustment": ("Inventory adjustment", "adjustment_number"),
    "PayrollRun": ("Payroll", None),
    "PayItem": ("Pay item", "name"),
    "TimeEntry": ("Time entry", None),
    "Project": ("Project", "name"),
    "Budget": ("Budget", "name"),
    "RecurringSchedule": ("Recurring transaction", "name"),
    "Company": ("Company settings", "name"),
    "CompanyMember": ("User access", None),
    "Invitation": ("Invitation", "email"),
}

# Fields not worth logging.
IGNORED_FIELDS = {"updated_at", "created_at", "password_hash", "closing_password_hash", "logo", "public_token"}


def plain(value):
    """A JSON-friendly copy of a value."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "value"):  # enums
        return value.value
    if isinstance(value, (bytes, bytearray)):
        return "(file)"
    return value


def changed_fields(record) -> dict:
    changes = {}
    state = inspect(record)
    for attribute in state.mapper.column_attrs:
        name = attribute.key
        if name in IGNORED_FIELDS:
            continue
        history = state.attrs[name].history
        if history.has_changes():
            old = history.deleted[0] if history.deleted else None
            new = history.added[0] if history.added else None
            if old != new:
                changes[name] = [plain(old), plain(new)]
    return changes


def company_of(record) -> int | None:
    if record.__class__.__name__ == "Company":
        return record.id
    return getattr(record, "company_id", None)


def entry_for(record, action: str, user_id: int | None) -> dict | None:
    class_name = record.__class__.__name__
    if class_name not in AUDITED:
        return None
    company_id = company_of(record)
    if company_id is None:
        return None
    label, name_field = AUDITED[class_name]
    name = getattr(record, name_field, None) if name_field else None
    changes = changed_fields(record) if action == "CHANGED" else None
    if action == "CHANGED" and not changes:
        return None
    verb = {"CREATED": "Added", "CHANGED": "Changed", "DELETED": "Deleted"}[action]
    summary = f"{verb} {label.lower()}"
    if name:
        summary += f" {name}"
    elif record.id:
        summary += f" #{record.id}"
    if changes:
        summary += ": " + ", ".join(sorted(changes))[:300]
    return {
        "company_id": company_id,
        "user_id": user_id,
        "action": action,
        "entity_type": label,
        "entity_id": record.id,
        "summary": summary[:500],
        "changes": changes,
    }


@event.listens_for(Session, "after_flush")
def write_audit_log(session: Session, flush_context) -> None:
    from app.models import AuditLog

    user_id = current_user_id(session)
    rows = []
    for record in session.new:
        rows.append(entry_for(record, "CREATED", user_id))
    for record in session.dirty:
        if session.is_modified(record, include_collections=False):
            rows.append(entry_for(record, "CHANGED", user_id))
    for record in session.deleted:
        rows.append(entry_for(record, "DELETED", user_id))
    rows = [row for row in rows if row is not None]
    queue_webhook_events(session, rows)
    if rows:
        # Written straight through the connection: adding objects to the
        # session while it is flushing is not allowed.
        session.connection().execute(insert(AuditLog.__table__), rows)


# ---------- webhook events ----------
#
# Each logged change is also an event for webhooks, e.g. "invoice.created".
# Events wait until the save is committed (a failed save sends nothing).

EVENTS_KEY = "webhook_events"


def event_name(entity_type: str, action: str) -> str:
    """("Product or service", "CREATED") -> "product_or_service.created"."""
    return entity_type.lower().replace(" ", "_") + "." + action.lower()


def queue_webhook_events(session: Session, rows: list[dict]) -> None:
    queue = session.info.setdefault(EVENTS_KEY, [])
    for row in rows:
        queue.append(
            {
                "event": event_name(row["entity_type"], row["action"]),
                "company_id": row["company_id"],
                "entity_id": row["entity_id"],
                "summary": row["summary"],
                "changes": row["changes"],
                "occurred_at": datetime.now().isoformat(timespec="seconds"),
            }
        )


@event.listens_for(Session, "after_commit")
def send_webhook_events(session: Session) -> None:
    events = session.info.pop(EVENTS_KEY, [])
    if events:
        from app.services.webhook_dispatcher import dispatch_events

        dispatch_events(session.get_bind(), events)


@event.listens_for(Session, "after_rollback")
def forget_webhook_events(session: Session) -> None:
    session.info.pop(EVENTS_KEY, None)

