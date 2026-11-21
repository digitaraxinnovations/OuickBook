"""
Delivering webhook events (EXT).

WebhookSender is the interface. The app picks one from the WEBHOOK_DELIVERY
setting:

- "log"  -> LogWebhookSender: sends nothing; each delivery is recorded as
            LOGGED so you can see exactly what would be sent.
- "http" -> HttpWebhookSender: POSTs the event as JSON to the webhook URL,
            signed with HMAC-SHA256 in the X-<AppName>-Signature header
            (X-DigiBooks-Signature with the default APP_NAME).
"""

import hashlib
import hmac
import json
import re
import urllib.request
from abc import ABC, abstractmethod

from app.core.config import Settings
from app.core.exceptions import BusinessRuleError


class DeliveryResult:
    def __init__(self, status: str, response_code: int | None = None, error: str | None = None):
        self.status = status
        self.response_code = response_code
        self.error = error


def sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class WebhookSender(ABC):
    mode = ""

    @abstractmethod
    def deliver(self, url: str, secret: str, payload: dict) -> DeliveryResult:
        """Send one event to one webhook."""


class LogWebhookSender(WebhookSender):
    mode = "log"

    def deliver(self, url: str, secret: str, payload: dict) -> DeliveryResult:
        return DeliveryResult("LOGGED")


class HttpWebhookSender(WebhookSender):
    mode = "http"

    def __init__(self, timeout_seconds: int, signature_header: str):
        self.timeout_seconds = timeout_seconds
        self.signature_header = signature_header

    def deliver(self, url: str, secret: str, payload: dict) -> DeliveryResult:
        body = json.dumps(payload, default=str).encode()
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", self.signature_header: sign(secret, body)},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return DeliveryResult("SENT", response.status)
        except Exception as error:  # the receiver being down must never break saving
            return DeliveryResult("FAILED", getattr(error, "code", None), str(error)[:500])


def signature_header(app_name: str) -> str:
    """X-<app name>-Signature, e.g. X-DigiBooks-Signature (spaces and symbols removed)."""
    return "X-" + re.sub(r"[^A-Za-z0-9]", "", app_name) + "-Signature"


def build_webhook_sender(settings: Settings) -> WebhookSender:
    if settings.webhook_delivery == "log":
        return LogWebhookSender()
    if settings.webhook_delivery == "http":
        return HttpWebhookSender(settings.webhook_timeout_seconds, signature_header(settings.app_name))
    raise BusinessRuleError('WEBHOOK_DELIVERY must be "log" or "http".')
