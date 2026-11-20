"""
API keys and webhooks.

API keys start with "lk_". A program sends one as its Bearer token and acts
as the user who made the key, with that user's role. Only a SHA-256 hash is
stored, so a lost key cannot be shown again - make a new one.
"""

import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.exceptions import AuthenticationError, BusinessRuleError, NotFoundError
from app.models import ApiKey, Company, User, Webhook, WebhookDelivery
from app.services.base import BaseService

API_KEY_PREFIX = "lk_"


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


class IntegrationService(BaseService):
    # ---------- API keys ----------

    def api_keys(self, company_id: int) -> list[ApiKey]:
        query = select(ApiKey).where(ApiKey.company_id == company_id).order_by(ApiKey.id.desc())
        return list(self.session.scalars(query))

    def create_api_key(self, company_id: int, user: User, name: str) -> tuple[ApiKey, str]:
        """Returns the key record and the key itself (shown to the user only this once)."""
        key = API_KEY_PREFIX + secrets.token_urlsafe(32)
        record = ApiKey(company_id=company_id, user_id=user.id, name=name, prefix=key[:10], key_hash=hash_key(key), is_active=True)
        self.session.add(record)
        self.commit()
        return record, key

    def revoke_api_key(self, company_id: int, key_id: int) -> None:
        record = self.session.get(ApiKey, key_id)
        if record is None or record.company_id != company_id:
            raise NotFoundError("API key not found.")
        record.is_active = False
        self.commit()

    def user_for_key(self, key: str) -> User:
        """The user an API key acts as, working in the key's company."""
        record = self.session.scalar(select(ApiKey).where(ApiKey.key_hash == hash_key(key)))
        if record is None or not record.is_active:
            raise AuthenticationError("This API key is not valid.")
        user = self.session.get(User, record.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("The user of this API key has been deactivated.")
        record.last_used_at = datetime.now(timezone.utc)
        self.session.commit()

        # The key always works in its own company. The user is detached first so this
        # never changes (and saves) the company the person has open in their browser.
        company = self.session.get(Company, record.company_id)
        self.session.expunge(user)
        user.company_id = record.company_id
        user.company = company
        return user

    # ---------- webhooks ----------

    def webhooks(self, company_id: int) -> list[Webhook]:
        query = select(Webhook).where(Webhook.company_id == company_id).order_by(Webhook.id)
        return list(self.session.scalars(query))

    def save_webhook(self, company_id: int, url: str, events: list[str], is_active: bool, webhook_id: int | None = None) -> Webhook:
        if not (url.startswith("https://") or url.startswith("http://")):
            raise BusinessRuleError("The webhook URL must start with https:// (or http:// for testing).")
        if not events:
            raise BusinessRuleError('Choose at least one event (or "*" for all).')
        if webhook_id is None:
            webhook = Webhook(company_id=company_id, secret=secrets.token_hex(24))
            self.session.add(webhook)
        else:
            webhook = self.session.get(Webhook, webhook_id)
            if webhook is None or webhook.company_id != company_id:
                raise NotFoundError("Webhook not found.")
        webhook.url = url
        webhook.events = events
        webhook.is_active = is_active
        self.commit()
        return webhook

    def delete_webhook(self, company_id: int, webhook_id: int) -> None:
        webhook = self.session.get(Webhook, webhook_id)
        if webhook is None or webhook.company_id != company_id:
            raise NotFoundError("Webhook not found.")
        self.session.delete(webhook)
        self.commit()

    def deliveries(self, company_id: int, limit: int = 50) -> list[WebhookDelivery]:
        query = (
            select(WebhookDelivery)
            .where(WebhookDelivery.company_id == company_id)
            .order_by(WebhookDelivery.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(query))
