"""
Sales tax setup and filing.

- Agencies:    who you pay. Adding one creates its own liability account
               under "Sales Tax Payable", so each agency's balance is separate.
- Rates/codes: what you charge. A code is one rate or several added together.
- Periods:     what you owe each agency per filing period (monthly,
               quarterly or yearly, counted from the agency's start date).
- Payments:    Debit the agency liability, Credit the bank.
- Adjustments: change what you owe (see SalesTaxAdjustment for the entries).
"""

from datetime import date, timedelta

from app.core.dates import add_months
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.integrations.tax_rates import TaxRateProvider
from app.models import Account, SalesTaxAdjustment, SalesTaxPayment, TaxAgency, TaxCode, TaxCodeRate, TaxRate
from app.models.enums import AccountType, JournalSource
from app.repositories.account_repository import AccountRepository
from app.repositories.tax_repositories import (
    SalesTaxAdjustmentRepository,
    SalesTaxLineRepository,
    SalesTaxPaymentRepository,
    TaxAgencyRepository,
    TaxCodeRepository,
    TaxRateRepository,
)
from app.schemas.tax import (
    SalesTaxAdjustmentCreate,
    FileReturnRequest,
    SalesTaxPaymentCreate,
    TaxAgencyWrite,
    TaxCodeComponent,
    TaxCodeRead,
    TaxCodeWrite,
    TaxPeriod,
    TaxRateWrite,
)
from app.seed.default_accounts import DetailType, SystemAccount
from app.services.base import BaseService
from app.services.ledger_service import LedgerLine, LedgerService
from app.services.system_accounts import SystemAccounts

MONTHS_PER_PERIOD = {"MONTHLY": 1, "QUARTERLY": 3, "YEARLY": 12}
LIABILITY_DETAIL_TYPE = "Sales Tax Payable"


class TaxService(BaseService):
    def __init__(
        self,
        session,
        agency_repository: TaxAgencyRepository,
        rate_repository: TaxRateRepository,
        code_repository: TaxCodeRepository,
        tax_line_repository: SalesTaxLineRepository,
        payment_repository: SalesTaxPaymentRepository,
        adjustment_repository: SalesTaxAdjustmentRepository,
        account_repository: AccountRepository,
        system_accounts: SystemAccounts,
        ledger: LedgerService,
    ):
        super().__init__(session)
        self.agency_repository = agency_repository
        self.rate_repository = rate_repository
        self.code_repository = code_repository
        self.tax_line_repository = tax_line_repository
        self.payment_repository = payment_repository
        self.adjustment_repository = adjustment_repository
        self.account_repository = account_repository
        self.system_accounts = system_accounts
        self.ledger = ledger

    # ---------- agencies ----------

    def list_agencies(self, company_id: int) -> list[TaxAgency]:
        return self.agency_repository.list_all(company_id)

    def get_agency(self, company_id: int, agency_id: int) -> TaxAgency:
        agency = self.agency_repository.get(company_id, agency_id)
        if agency is None:
            raise NotFoundError("Tax agency not found.")
        return agency

    def create_agency(self, company_id: int, data: TaxAgencyWrite) -> TaxAgency:
        self.check_agency_name(company_id, data.name, None)
        liability_account = self.create_liability_account(company_id, data.name)
        agency = TaxAgency(
            company_id=company_id,
            name=data.name,
            filing_frequency=data.filing_frequency,
            start_date=data.start_date,
            liability_account_id=liability_account.id,
            is_active=data.is_active,
        )
        self.agency_repository.add(agency)
        self.commit()
        return agency

    def update_agency(self, company_id: int, agency_id: int, data: TaxAgencyWrite) -> TaxAgency:
        agency = self.get_agency(company_id, agency_id)
        self.check_agency_name(company_id, data.name, agency.id)
        agency.name = data.name
        agency.filing_frequency = data.filing_frequency
        agency.start_date = data.start_date
        agency.is_active = data.is_active
        self.commit()
        return agency

    def check_agency_name(self, company_id: int, name: str, agency_id: int | None) -> None:
        existing = self.agency_repository.get_by_name(company_id, name)
        if existing is not None and existing.id != agency_id:
            raise ConflictError("A tax agency with this name already exists.")

    def create_liability_account(self, company_id: int, agency_name: str) -> Account:
        parent = self.system_accounts.get(company_id, SystemAccount.SALES_TAX_PAYABLE)
        name = f"{agency_name} Payable"
        if self.account_repository.get_by_name(company_id, name) is not None:
            name = f"{agency_name} Sales Tax Payable"
        if self.account_repository.get_by_name(company_id, name) is not None:
            raise ConflictError(f"An account named '{name}' already exists.")
        account = Account(
            company_id=company_id,
            name=name,
            account_type=AccountType.LIABILITY,
            detail_type=LIABILITY_DETAIL_TYPE,
            parent_id=parent.id,
        )
        return self.account_repository.add(account)

    # ---------- rates ----------

    def list_rates(self, company_id: int) -> list[TaxRate]:
        return self.rate_repository.list_all(company_id)

    def get_rate(self, company_id: int, rate_id: int) -> TaxRate:
        rate = self.rate_repository.get(company_id, rate_id)
        if rate is None:
            raise NotFoundError("Tax rate not found.")
        return rate

    def create_rate(self, company_id: int, data: TaxRateWrite) -> TaxRate:
        self.get_agency(company_id, data.agency_id)
        rate = TaxRate(company_id=company_id, name=data.name, agency_id=data.agency_id, rate=data.rate, is_active=data.is_active)
        self.rate_repository.add(rate)

        if data.create_code:
            if self.code_repository.get_by_name(company_id, data.name) is not None:
                raise ConflictError("A sales tax code with this name already exists. Untick 'also create a code'.")
            code = TaxCode(company_id=company_id, name=data.name, is_active=data.is_active)
            code.components.append(TaxCodeRate(tax_rate_id=rate.id))
            self.code_repository.add(code)

        self.commit()
        return rate

    def update_rate(self, company_id: int, rate_id: int, data: TaxRateWrite) -> TaxRate:
        """Changing a rate only affects new sales; saved forms keep the tax they were given."""
        rate = self.get_rate(company_id, rate_id)
        self.get_agency(company_id, data.agency_id)
        if data.agency_id != rate.agency_id and self.tax_line_repository.rate_was_used(company_id, rate.id):
            raise BusinessRuleError("This rate has been charged already, so its agency cannot change.")
        rate.name = data.name
        rate.agency_id = data.agency_id
        rate.rate = data.rate
        rate.is_active = data.is_active
        self.commit()
        return rate

    # ---------- codes ----------

    def list_codes(self, company_id: int, active_only: bool = False) -> list[TaxCodeRead]:
        result = []
        for code in self.code_repository.list_all(company_id, active_only):
            result.append(self.code_read(code))
        return result

    def get_code(self, company_id: int, code_id: int) -> TaxCode:
        code = self.code_repository.get(company_id, code_id)
        if code is None:
            raise NotFoundError("Sales tax code not found.")
        return code

    def create_code(self, company_id: int, data: TaxCodeWrite) -> TaxCodeRead:
        self.check_code_name(company_id, data.name, None)
        code = TaxCode(company_id=company_id, name=data.name, is_active=data.is_active)
        self.set_components(company_id, code, data.rate_ids)
        self.code_repository.add(code)
        self.commit()
        return self.code_read(code)

    def update_code(self, company_id: int, code_id: int, data: TaxCodeWrite) -> TaxCodeRead:
        code = self.get_code(company_id, code_id)
        self.check_code_name(company_id, data.name, code.id)
        code.name = data.name
        code.is_active = data.is_active
        code.components.clear()
        self.session.flush()
        self.set_components(company_id, code, data.rate_ids)
        self.commit()
        return self.code_read(code)

    def check_code_name(self, company_id: int, name: str, code_id: int | None) -> None:
        existing = self.code_repository.get_by_name(company_id, name)
        if existing is not None and existing.id != code_id:
            raise ConflictError("A sales tax code with this name already exists.")

    def set_components(self, company_id: int, code: TaxCode, rate_ids: list[int]) -> None:
        seen = set()
        for rate_id in rate_ids:
            if rate_id in seen:
                continue
            seen.add(rate_id)
            rate = self.get_rate(company_id, rate_id)
            code.components.append(TaxCodeRate(tax_rate=rate))

    def code_read(self, code: TaxCode) -> TaxCodeRead:
        components = []
        for component in code.components:
            rate = component.tax_rate
            components.append(TaxCodeComponent(tax_rate_id=rate.id, name=rate.name, rate=rate.rate, agency_id=rate.agency_id))
        return TaxCodeRead(id=code.id, name=code.name, is_active=code.is_active, total_rate=code.total_rate, components=components)

    # ---------- filing periods ----------

    def periods(self, company_id: int, agency_id: int | None = None, today: date | None = None) -> list[TaxPeriod]:
        """Every filing period from each agency's start date up to today, newest first."""
        if today is None:
            today = date.today()
        agencies = self.list_agencies(company_id)
        if agency_id is not None:
            agencies = [self.get_agency(company_id, agency_id)]

        result = []
        for agency in agencies:
            months = MONTHS_PER_PERIOD[agency.filing_frequency]
            start = agency.start_date
            while start <= today:
                next_start = add_months(start, months)
                end = next_start - timedelta(days=1)
                result.append(self.period_for(company_id, agency, start, end, today))
                start = next_start

        result.sort(key=lambda period: (period.period_end, period.agency_name), reverse=True)
        return result

    def period_for(self, company_id: int, agency: TaxAgency, start: date, end: date, today: date) -> TaxPeriod:
        collected = self.tax_line_repository.tax_total(company_id, agency.id, start, end)
        adjustments = self.adjustment_repository.total_between(company_id, agency.id, start, end)
        payments = self.payment_repository.total_for_period(company_id, agency.id, start, end)
        balance = collected + adjustments - payments

        if end >= today:
            status = "OPEN"
        elif balance <= 0 and payments > 0:
            status = "PAID"
        elif balance <= 0:
            status = "NOTHING_DUE"
        else:
            status = "DUE"

        return TaxPeriod(
            agency_id=agency.id,
            agency_name=agency.name,
            period_start=start,
            period_end=end,
            tax_collected=collected,
            adjustments=adjustments,
            payments=payments,
            balance=balance,
            status=status,
        )

    # ---------- payments ----------

    def list_payments(self, company_id: int, agency_id: int | None = None) -> list[SalesTaxPayment]:
        return self.payment_repository.list_for_agency(company_id, agency_id)

    def record_payment(self, company_id: int, data: SalesTaxPaymentCreate, confirmation_no: str | None = None) -> SalesTaxPayment:
        agency = self.get_agency(company_id, data.agency_id)
        if data.period_end < data.period_start:
            raise BusinessRuleError("The period end cannot be before its start.")
        if data.amount <= 0:
            raise BusinessRuleError("Enter the amount you paid.")
        bank = self.check_payment_account(company_id, data.payment_account_id)

        payment = SalesTaxPayment(
            company_id=company_id,
            agency_id=agency.id,
            payment_date=data.payment_date,
            period_start=data.period_start,
            period_end=data.period_end,
            amount=data.amount,
            payment_account_id=bank.id,
            memo=data.memo,
            confirmation_no=confirmation_no,
        )
        self.payment_repository.add(payment)
        entry = self.ledger.post(
            company_id=company_id,
            entry_date=data.payment_date,
            source_type=JournalSource.SALES_TAX_PAYMENT,
            source_id=payment.id,
            memo=data.memo or f"Sales tax payment - {agency.name}",
            lines=[
                LedgerLine(agency.liability_account_id, debit=data.amount),
                LedgerLine(bank.id, credit=data.amount),
            ],
        )
        payment.journal_entry_id = entry.id
        self.commit()
        return payment

    def file_return(self, company_id: int, data: FileReturnRequest, provider: TaxRateProvider) -> SalesTaxPayment:
        """E-file one finished filing period through the tax provider and record the payment of what it owes."""
        agency = self.get_agency(company_id, data.agency_id)
        period = self.period_for(company_id, agency, data.period_start, data.period_end, date.today())
        if period.status == "OPEN":
            raise BusinessRuleError("This filing period has not ended yet.")
        if period.balance <= 0:
            raise BusinessRuleError("Nothing is due for this period.")
        confirmation = provider.file_return(agency.name, data.period_start, data.period_end, period.balance)
        payment = SalesTaxPaymentCreate(
            agency_id=agency.id,
            payment_date=data.payment_date,
            period_start=data.period_start,
            period_end=data.period_end,
            amount=period.balance,
            payment_account_id=data.payment_account_id,
            memo=f"E-filed - confirmation {confirmation}",
        )
        return self.record_payment(company_id, payment, confirmation_no=confirmation)

    def check_payment_account(self, company_id: int, account_id: int) -> Account:
        account = self.account_repository.get(company_id, account_id)
        is_bank = account is not None and account.account_type == AccountType.ASSET and account.detail_type == DetailType.BANK
        is_card = account is not None and account.account_type == AccountType.LIABILITY and account.detail_type == DetailType.CREDIT_CARD
        if not (is_bank or is_card) or not account.is_active:
            raise BusinessRuleError("Pay sales tax from a bank or credit card account.")
        return account

    # ---------- adjustments ----------

    def list_adjustments(self, company_id: int, agency_id: int | None = None) -> list[SalesTaxAdjustment]:
        return self.adjustment_repository.list_for_agency(company_id, agency_id)

    def record_adjustment(self, company_id: int, data: SalesTaxAdjustmentCreate) -> SalesTaxAdjustment:
        agency = self.get_agency(company_id, data.agency_id)
        if data.amount == 0:
            raise BusinessRuleError("Enter the adjustment amount.")
        account = self.account_repository.get(company_id, data.account_id)
        if account is None or not account.is_active:
            raise BusinessRuleError("Choose the account for the other side of the adjustment.")
        if account.id == agency.liability_account_id:
            raise BusinessRuleError("Choose an account other than the agency's own liability account.")

        adjustment = SalesTaxAdjustment(
            company_id=company_id,
            agency_id=agency.id,
            adjustment_date=data.adjustment_date,
            amount=data.amount,
            account_id=account.id,
            reason=data.reason,
        )
        self.adjustment_repository.add(adjustment)

        amount = abs(data.amount)
        if data.amount > 0:
            lines = [LedgerLine(account.id, debit=amount), LedgerLine(agency.liability_account_id, credit=amount)]
        else:
            lines = [LedgerLine(agency.liability_account_id, debit=amount), LedgerLine(account.id, credit=amount)]
        entry = self.ledger.post(
            company_id=company_id,
            entry_date=data.adjustment_date,
            source_type=JournalSource.SALES_TAX_ADJUST,
            source_id=adjustment.id,
            memo=f"Sales tax adjustment - {agency.name}: {data.reason}",
            lines=lines,
        )
        adjustment.journal_entry_id = entry.id
        self.commit()
        return adjustment
