"""
Currencies and exchange rates.

A customer can use a foreign currency. Their invoices, sales forms and
payments are in that currency; the books are kept in the home currency:

    home amount = foreign amount x exchange rate (home currency per 1 unit)

When a payment's rate differs from the invoice's rate, the difference is an
exchange gain or loss (see PaymentService).
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.money import ZERO, to_money
from app.integrations.exchange_rates import ExchangeRateProvider
from app.models import Company, Currency, ExchangeRate
from app.repositories.company_repository import CompanyRepository
from app.schemas.platform import CurrencyRead, CurrencyWrite, ExchangeRateWrite
from app.services.base import BaseService
from app.services.ledger_service import LedgerLine

ONE = Decimal("1")


class CurrencyService(BaseService):
    def __init__(self, session, company_repository: CompanyRepository, provider: ExchangeRateProvider):
        super().__init__(session)
        self.company_repository = company_repository
        self.provider = provider

    # ---------- currencies ----------

    def list(self, company_id: int) -> list[CurrencyRead]:
        query = select(Currency).where(Currency.company_id == company_id).order_by(Currency.code)
        result = []
        for currency in self.session.scalars(query):
            latest = self.latest_rate(company_id, currency.code, date.today())
            result.append(
                CurrencyRead(
                    id=currency.id,
                    code=currency.code,
                    name=currency.name,
                    latest_rate=latest.rate if latest else None,
                    latest_rate_date=latest.rate_date if latest else None,
                )
            )
        return result

    def add(self, company_id: int, data: CurrencyWrite) -> CurrencyRead:
        company = self.company_repository.get(company_id)
        if not company.multicurrency_enabled:
            raise BusinessRuleError("Turn on multicurrency in Settings -> Advanced first.")
        if data.code == company.currency:
            raise BusinessRuleError(f"{data.code} is your home currency.")
        if self.find(company_id, data.code) is not None:
            raise ConflictError("That currency is already in the list.")
        currency = Currency(company_id=company_id, code=data.code, name=data.name)
        self.session.add(currency)
        self.commit()
        return CurrencyRead(id=currency.id, code=currency.code, name=currency.name)

    def find(self, company_id: int, code: str) -> Currency | None:
        query = select(Currency).where(Currency.company_id == company_id, Currency.code == code)
        return self.session.scalar(query)

    def check_customer_currency(self, company_id: int, code: str | None) -> str | None:
        """None or the home currency = home. Anything else must be in the currency list."""
        if not code:
            return None
        company = self.company_repository.get(company_id)
        if code == company.currency:
            return None
        if self.find(company_id, code) is None:
            raise BusinessRuleError(f"Add {code} under Settings -> Currencies first.")
        return code

    # ---------- rates ----------

    def rates(self, company_id: int, code: str | None = None) -> list[ExchangeRate]:
        query = select(ExchangeRate).where(ExchangeRate.company_id == company_id)
        if code:
            query = query.where(ExchangeRate.currency_code == code)
        return list(self.session.scalars(query.order_by(ExchangeRate.rate_date.desc(), ExchangeRate.currency_code)))

    def set_rate(self, company_id: int, data: ExchangeRateWrite) -> ExchangeRate:
        if self.find(company_id, data.currency_code) is None:
            raise NotFoundError("Add the currency first.")
        query = select(ExchangeRate).where(
            ExchangeRate.company_id == company_id,
            ExchangeRate.currency_code == data.currency_code,
            ExchangeRate.rate_date == data.rate_date,
        )
        rate = self.session.scalar(query)
        if rate is None:
            rate = ExchangeRate(company_id=company_id, currency_code=data.currency_code, rate_date=data.rate_date)
            self.session.add(rate)
        rate.rate = data.rate
        self.commit()
        return rate

    def refresh_from_provider(self, company_id: int, on_date: date) -> int:
        """Download today's rate for every currency (EXT). Returns how many were saved."""
        company = self.company_repository.get(company_id)
        saved = 0
        for currency in self.list(company_id):
            rate = self.provider.rate_for(company.currency, currency.code, on_date)
            self.set_rate(company_id, ExchangeRateWrite(currency_code=currency.code, rate_date=on_date, rate=rate))
            saved += 1
        return saved

    def latest_rate(self, company_id: int, code: str, on_date: date) -> ExchangeRate | None:
        query = (
            select(ExchangeRate)
            .where(ExchangeRate.company_id == company_id, ExchangeRate.currency_code == code, ExchangeRate.rate_date <= on_date)
            .order_by(ExchangeRate.rate_date.desc())
        )
        return self.session.scalars(query).first()

    def rate_for(self, company_id: int, currency_code: str | None, on_date: date, typed_rate: Decimal | None = None) -> Decimal:
        """The rate to use on a form: 1 for the home currency, else the typed rate or the latest saved rate."""
        if not currency_code:
            return ONE
        if typed_rate is not None:
            if typed_rate <= 0:
                raise BusinessRuleError("The exchange rate must be more than zero.")
            return typed_rate
        latest = self.latest_rate(company_id, currency_code, on_date)
        if latest is None:
            raise BusinessRuleError(f"Enter the exchange rate for {currency_code} (Settings -> Currencies, or on the form).")
        return latest.rate

    # ---------- converting a journal entry ----------

    @staticmethod
    def to_home(lines: list[LedgerLine], rate: Decimal, balancing_index: int = 0) -> list[LedgerLine]:
        """
        Convert foreign-currency ledger lines to home currency. Rounding can
        leave a cent or two between debits and credits; that goes on the
        balancing line (e.g. Accounts Receivable).
        """
        if rate == ONE:
            return lines
        for line in lines:
            line.debit = to_money(line.debit * rate)
            line.credit = to_money(line.credit * rate)
        difference = sum((line.debit for line in lines), ZERO) - sum((line.credit for line in lines), ZERO)
        if difference != 0 and lines:
            balancing = lines[balancing_index]
            if balancing.debit > 0:
                balancing.debit -= difference
            else:
                balancing.credit += difference
        return lines


def company_home_currency(company: Company) -> str:
    return company.currency
