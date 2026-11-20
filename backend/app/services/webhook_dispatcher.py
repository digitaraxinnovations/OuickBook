"""
Sends committed change events to the company's webhooks and records each delivery.

Runs after a save is committed, on its own database connection, so a slow
or failing receiver never undoes or blocks the save itself.
"""

from datetime import datetime, timezone

from sqlalchemy import insert, select

from app.core.config import settings
from app.integrations.webhooks import build_webhook_sender
from app.models import Webhook, WebhookDelivery


def wants(webhook_events: list, event: str) -> bool:
    return "*" in webhook_events or event in webhook_events


def dispatch_events(engine, events: list[dict]) -> None:
    company_ids = {item["company_id"] for item in events}
    sender = build_webhook_sender(settings)
    with engine.begin() as connection:
        hooks = connection.execute(
            select(Webhook.id, Webhook.company_id, Webhook.url, Webhook.secret, Webhook.events).where(
                Webhook.company_id.in_(company_ids), Webhook.is_active.is_(True)
            )
        ).all()
        if not hooks:
            return
        deliveries = []
        for item in events:
            for hook_id, company_id, url, secret, wanted in hooks:
                if company_id != item["company_id"] or not wants(wanted, item["event"]):
                    continue
                result = sender.deliver(url, secret, item)
                deliveries.append(
                    {
                        "company_id": company_id,
                        "webhook_id": hook_id,
                        "event": item["event"],
                        "payload": item,
                        "status": result.status,
                        "response_code": result.response_code,
                        "error": result.error,
                        "created_at": datetime.now(timezone.utc),
                    }
                )
        if deliveries:
            connection.execute(insert(WebhookDelivery.__table__), deliveries)
