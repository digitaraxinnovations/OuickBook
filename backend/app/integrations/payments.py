"""
Online invoice payments (EXT) - the "Pay now" button customers see.

PaymentProcessor is the interface. The app picks one from the
PAYMENT_PROVIDER setting. Today only "none" exists, which keeps online
payments switched off.

To connect a real card processor later (e.g. Stripe):
  1. Write a class that inherits from PaymentProcessor.
     - create_checkout(): ask the provider for a hosted checkout page and return its URL.
  2. Add a webhook route that receives the provider's "payment succeeded" message
     and records it with PaymentService.receive().
  3. Return the new class from build_payment_processor() when PAYMENT_PROVIDER matches.
"""

from abc import ABC, abstractmethod
from decimal import Decimal

from app.core.config import Settings
from app.core.exceptions import BusinessRuleError
from app.models import Invoice


class PaymentProcessor(ABC):
    provider_name = ""

    @abstractmethod
    def is_enabled(self) -> bool:
        """True when customers can pay online."""

    @abstractmethod
    def create_checkout(self, invoice: Invoice, amount: Decimal, return_url: str) -> str:
        """Start an online payment and return the URL to send the customer to."""


class DisabledPaymentProcessor(PaymentProcessor):
    provider_name = "none"

    def is_enabled(self) -> bool:
        return False

    def create_checkout(self, invoice: Invoice, amount: Decimal, return_url: str) -> str:
        raise BusinessRuleError("Online payments are not set up yet. Please pay by bank transfer or check.")


def build_payment_processor(settings: Settings) -> PaymentProcessor:
    if settings.payment_provider == "none":
        return DisabledPaymentProcessor()
    raise BusinessRuleError(
        f'The payment provider "{settings.payment_provider}" is not supported yet. Set PAYMENT_PROVIDER=none.'
    )
