"""
Payroll liabilities: deductions, taxes and employer amounts you hold until
you send them on (to the tax office, the pension fund, the health insurer...).

    Pay a liability:  Debit the pay item's liability account, Credit the bank
"""

from datetime import date
from decimal import Decimal

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.money import ZERO
from app.models import PayrollLiabilityPayment
from app.models.enums import AccountType, JournalSource
from app.repositories.account_repository import AccountRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.payroll_repositories import LiabilityPaymentRepository, PayItemRepository, PayrollRunRepository
from app.schemas.payroll import LiabilityBalance, LiabilityPaymentCreate
from app.seed.default_accounts import DetailType, SystemAccount
from app.services.base import BaseService
from app.services.ledger_service import LedgerLine, LedgerService
from app.services.paycheck_calculator import EMPLOYEE_SIDE, EMPLOYER_SIDE
from app.services.system_accounts import SystemAccounts


class PayrollLiabilityService(BaseService):
    def __init__(
        self,
        session,
        payment_repository: LiabilityPaymentRepository,
        item_repository: PayItemRepository,
        run_repository: PayrollRunRepository,
        account_repository: AccountRepository,
        journal_repository: JournalRepository,
        system_accounts: SystemAccounts,
        ledger: LedgerService,
    ):
        super().__init__(session)
        self.payment_repository = payment_repository
        self.item_repository = item_repository
        self.run_repository = run_repository
        self.account_repository = account_repository
        self.journal_repository = journal_repository
        self.system_accounts = system_accounts
        self.ledger = ledger

    def balances(self, company_id: int) -> list[LiabilityBalance]:
        accrued = self.run_repository.accrued_per_pay_item(company_id)
        paid = self.payment_repository.paid_per_pay_item(company_id)
        result = []
        for item in self.item_repository.list_all(company_id):
            if item.kind not in EMPLOYEE_SIDE and item.kind not in EMPLOYER_SIDE:
                continue
            item_accrued = accrued.get(item.id, ZERO)
            item_paid = paid.get(item.id, ZERO)
            if item_accrued == 0 and item_paid == 0 and not item.is_active:
                continue
            result.append(
                LiabilityBalance(
                    pay_item_id=item.id,
                    name=item.name,
                    kind=item.kind,
                    accrued=item_accrued,
                    paid=item_paid,
                    balance=item_accrued - item_paid,
                )
            )
        return result

    def list_payments(self, company_id: int) -> list[PayrollLiabilityPayment]:
        return self.payment_repository.list_all(company_id)

    def pay(self, company_id: int, data: LiabilityPaymentCreate) -> PayrollLiabilityPayment:
        item = self.item_repository.get(company_id, data.pay_item_id)
        if item is None or (item.kind not in EMPLOYEE_SIDE and item.kind not in EMPLOYER_SIDE):
            raise BusinessRuleError("Choose a deduction, tax or employer contribution to pay.")
        bank = self.account_repository.get(company_id, data.bank_account_id)
        if bank is None or bank.account_type != AccountType.ASSET or bank.detail_type != DetailType.BANK:
            raise BusinessRuleError("Pay payroll liabilities from a bank account.")

        balance = self.balance_of(company_id, item.id)
        if data.amount > balance:
            raise BusinessRuleError(f"Only {balance} is owed for {item.name}.")

        payment = PayrollLiabilityPayment(
            company_id=company_id,
            pay_item_id=item.id,
            payment_date=data.payment_date,
            amount=data.amount,
            bank_account_id=bank.id,
            memo=data.memo,
            is_void=False,
        )
        self.payment_repository.add(payment)
        liability_id = item.liability_account_id or self.system_accounts.get(company_id, SystemAccount.PAYROLL_LIABILITIES).id
        entry = self.ledger.post(
            company_id=company_id,
            entry_date=data.payment_date,
            source_type=JournalSource.PAYROLL_LIABILITY,
            source_id=payment.id,
            memo=data.memo or f"Payroll liability payment - {item.name}",
            lines=[LedgerLine(liability_id, debit=data.amount), LedgerLine(bank.id, credit=data.amount)],
        )
        payment.journal_entry_id = entry.id
        self.commit()
        return payment

    def balance_of(self, company_id: int, pay_item_id: int) -> Decimal:
        for row in self.balances(company_id):
            if row.pay_item_id == pay_item_id:
                return row.balance
        return ZERO

    def void_payment(self, company_id: int, payment_id: int) -> PayrollLiabilityPayment:
        payment = self.payment_repository.get(company_id, payment_id)
        if payment is None:
            raise NotFoundError("Payment not found.")
        if payment.is_void:
            raise BusinessRuleError("This payment is already void.")
        original = self.journal_repository.get(company_id, payment.journal_entry_id)
        self.ledger.reverse(company_id, original, date.today(), JournalSource.PAYROLL_LIABILITY, "Void of liability payment")
        payment.is_void = True
        self.commit()
        return payment
