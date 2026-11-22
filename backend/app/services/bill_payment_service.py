"""
Paying bills.

    Debit  Accounts Payable     (we owe the vendor less)
    Credit Bank / Credit card   (the money left our account)

Using a vendor credit posts nothing: the credit already lowered Accounts Payable.
"""

from datetime import date

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.money import ZERO, to_money
from app.models import Account, BillPayment, BillPaymentApplication, VendorCreditUse
from app.models.enums import AccountType, JournalSource, PaymentMethod, PurchaseDocStatus, PurchaseDocType
from app.repositories.account_repository import AccountRepository
from app.repositories.contact_repository import VendorRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.purchase_repositories import BillPaymentRepository, PurchaseDocumentRepository
from app.schemas.purchase import BatchBillPaymentCreate, BillApplicationInput, BillPaymentCreate
from app.seed.default_accounts import DetailType, SystemAccount
from app.services.base import BaseService
from app.services.check_numbers import CheckNumberService
from app.services.currency_service import CurrencyService
from app.services.ledger_service import LedgerLine, LedgerService
from app.services.system_accounts import SystemAccounts

UNPAID = (PurchaseDocStatus.OPEN, PurchaseDocStatus.PARTIALLY_PAID)


class BillPaymentService(BaseService):
    def __init__(
        self,
        session,
        repository: BillPaymentRepository,
        purchase_repository: PurchaseDocumentRepository,
        vendor_repository: VendorRepository,
        account_repository: AccountRepository,
        journal_repository: JournalRepository,
        system_accounts: SystemAccounts,
        check_numbers: CheckNumberService,
        ledger: LedgerService,
        currencies: CurrencyService,
    ):
        super().__init__(session)
        self.currencies = currencies
        self.repository = repository
        self.purchase_repository = purchase_repository
        self.vendor_repository = vendor_repository
        self.account_repository = account_repository
        self.journal_repository = journal_repository
        self.system_accounts = system_accounts
        self.check_numbers = check_numbers
        self.ledger = ledger

    # ---------- reading ----------

    def list(self, company_id: int) -> list[BillPayment]:
        return self.repository.list_all(company_id)

    def get(self, company_id: int, payment_id: int) -> BillPayment:
        payment = self.repository.get(company_id, payment_id)
        if payment is None:
            raise NotFoundError("Bill payment not found.")
        return payment

    def list_for_bill(self, company_id: int, bill_id: int) -> list[dict]:
        rows = []
        for application in self.repository.applications_for_bill(company_id, bill_id):
            payment = application.payment
            rows.append(
                {
                    "payment_id": payment.id,
                    "payment_date": payment.payment_date,
                    "payment_method": payment.payment_method,
                    "check_number": payment.check_number,
                    "payment_account": payment.payment_account,
                    "amount": application.amount,
                }
            )
        return rows

    # ---------- paying ----------

    def pay(self, company_id: int, data: BillPaymentCreate, commit: bool = True) -> BillPayment:
        vendor = self.vendor_repository.get(company_id, data.vendor_id)
        if vendor is None:
            raise NotFoundError("Vendor not found.")
        account = self.check_payment_account(company_id, data.payment_account_id, data.payment_method)

        applied_total = ZERO
        for application in data.applications:
            applied_total += application.amount
        credits_total = ZERO
        for credit in data.credits:
            credits_total += credit.amount
        if credits_total > applied_total:
            raise BusinessRuleError("Vendor credits cannot be more than the bills being paid.")
        amount = applied_total - credits_total
        rate = self.currencies.rate_for(company_id, vendor.currency_code, data.payment_date, data.exchange_rate)

        payment = BillPayment(
            company_id=company_id,
            vendor_id=vendor.id,
            payment_date=data.payment_date,
            payment_account_id=account.id,
            payment_method=data.payment_method,
            print_later=data.print_later and data.payment_method == PaymentMethod.CHECK,
            amount=amount,
            memo=data.memo,
            currency_code=vendor.currency_code,
            exchange_rate=rate,
        )
        if data.payment_method == PaymentMethod.CHECK and not payment.print_later and amount > 0:
            payment.check_number = self.check_numbers.assign(company_id, account.id, data.check_number)

        seen = set()
        for application in data.applications:
            if application.bill_id in seen:
                raise BusinessRuleError("Each bill can only appear once in a payment.")
            seen.add(application.bill_id)
            bill = self.purchase_repository.get(company_id, application.bill_id)
            if bill is None or bill.doc_type != PurchaseDocType.BILL or bill.vendor_id != vendor.id:
                raise BusinessRuleError(f"Bill {application.bill_id} does not belong to this vendor.")
            if bill.status not in UNPAID:
                raise BusinessRuleError(f"Bill {bill.doc_number or bill.id} is not open.")
            if application.amount > bill.balance:
                raise BusinessRuleError(f"The amount for bill {bill.doc_number or bill.id} is more than its balance ({bill.balance}).")
            payment.applications.append(BillPaymentApplication(bill_id=bill.id, amount=application.amount))
            bill.amount_applied = bill.amount_applied + application.amount
            bill.status = PurchaseDocStatus.PAID if bill.balance == 0 else PurchaseDocStatus.PARTIALLY_PAID

        for credit_use in data.credits:
            credit = self.purchase_repository.get(company_id, credit_use.vendor_credit_id)
            if credit is None or credit.doc_type != PurchaseDocType.VENDOR_CREDIT or credit.vendor_id != vendor.id:
                raise BusinessRuleError("That vendor credit does not belong to this vendor.")
            if credit.status != PurchaseDocStatus.OPEN or credit_use.amount > credit.balance:
                raise BusinessRuleError(f"That vendor credit only has {credit.balance} left.")
            payment.credits_used.append(VendorCreditUse(vendor_credit_id=credit.id, amount=credit_use.amount))
            credit.amount_applied = credit.amount_applied + credit_use.amount
            if credit.balance == 0:
                credit.status = PurchaseDocStatus.CLOSED

        self.repository.add(payment)

        if amount > 0:
            entry = self.ledger.post(
                company_id=company_id,
                entry_date=data.payment_date,
                source_type=JournalSource.BILL_PAYMENT,
                source_id=payment.id,
                memo=f"Bill payment to {vendor.display_name}",
                lines=self.payment_ledger_lines(company_id, payment, account.id, applied_total),
            )
            payment.journal_entry_id = entry.id

        if commit:
            self.commit()
        return payment

    def payment_ledger_lines(self, company_id: int, payment: BillPayment, account_id: int, applied_total) -> list[LedgerLine]:
        """
            Debit  Accounts Payable        what the bills were booked at
            Credit bank or credit card     amount x payment rate
            Exchange gain / loss           the difference (foreign currency only)
        """
        payable = self.system_accounts.get(company_id, SystemAccount.ACCOUNTS_PAYABLE)
        paid_home = to_money(payment.amount * payment.exchange_rate)
        if not payment.currency_code or applied_total <= 0:
            return [LedgerLine(payable.id, debit=paid_home), LedgerLine(account_id, credit=paid_home)]

        # Only the money part of the payment (not vendor credits used) settles bills at a new rate.
        money_share = payment.amount / applied_total
        booked_home = ZERO
        for application in payment.applications:
            bill = self.purchase_repository.get(company_id, application.bill_id)
            booked_home += application.amount * money_share * bill.exchange_rate
        booked_home = to_money(booked_home)

        lines = [LedgerLine(payable.id, debit=booked_home), LedgerLine(account_id, credit=paid_home)]
        loss = paid_home - booked_home  # paying more home currency than the bill was booked at is a loss
        if loss != 0:
            exchange = self.system_accounts.get(company_id, SystemAccount.EXCHANGE_GAIN_LOSS)
            lines.append(LedgerLine(exchange.id, debit=loss) if loss > 0 else LedgerLine(exchange.id, credit=-loss))
        return lines

    def pay_batch(self, company_id: int, data: BatchBillPaymentCreate) -> list[BillPayment]:
        """'Pay bills' screen: one payment (and one check) per vendor."""
        bills_by_vendor = {}
        for item in data.bills:
            bill = self.purchase_repository.get(company_id, item.bill_id)
            if bill is None:
                raise BusinessRuleError(f"Bill {item.bill_id} does not exist.")
            bills_by_vendor.setdefault(bill.vendor_id, []).append(item)

        payments = []
        for vendor_id, items in bills_by_vendor.items():
            single = BillPaymentCreate(
                vendor_id=vendor_id,
                payment_date=data.payment_date,
                payment_account_id=data.payment_account_id,
                payment_method=data.payment_method,
                print_later=data.print_later,
                applications=[BillApplicationInput(bill_id=item.bill_id, amount=item.amount) for item in items],
            )
            payments.append(self.pay(company_id, single, commit=False))
        self.commit()
        return payments

    def check_payment_account(self, company_id: int, account_id: int, method: PaymentMethod) -> Account:
        account = self.account_repository.get(company_id, account_id)
        undeposited = self.system_accounts.get(company_id, SystemAccount.UNDEPOSITED_FUNDS)
        if account is None or not account.is_active:
            raise BusinessRuleError("Choose the bank or credit card account you paid from.")
        is_bank = account.account_type == AccountType.ASSET and account.system_key != SystemAccount.ACCOUNTS_RECEIVABLE and account.id != undeposited.id
        is_card = account.account_type == AccountType.LIABILITY and account.detail_type == DetailType.CREDIT_CARD
        if method == PaymentMethod.CHECK and not is_bank:
            raise BusinessRuleError("Checks must be written from a bank account.")
        if not is_bank and not is_card:
            raise BusinessRuleError("Pay bills from a bank or credit card account.")
        return account

    # ---------- deleting ----------

    def delete(self, company_id: int, payment_id: int) -> None:
        """Undo a bill payment: the bills and credits become open again."""
        payment = self.get(company_id, payment_id)
        if payment.journal_entry_id is not None:
            original = self.journal_repository.get(company_id, payment.journal_entry_id)
            self.ledger.reverse(company_id, original, date.today(), JournalSource.PURCHASE_VOID, "Deleted bill payment")

        for application in payment.applications:
            bill = application.bill
            bill.amount_applied = bill.amount_applied - application.amount
            bill.status = PurchaseDocStatus.OPEN if bill.amount_applied == 0 else PurchaseDocStatus.PARTIALLY_PAID
        for credit_use in payment.credits_used:
            credit = credit_use.vendor_credit
            credit.amount_applied = credit.amount_applied - credit_use.amount
            credit.status = PurchaseDocStatus.OPEN

        self.session.delete(payment)
        self.commit()
