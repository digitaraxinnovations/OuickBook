"""
Bank deposits: move payments and sales receipts out of Undeposited Funds
into a bank account, optionally with other money on the same deposit.

    Debit  Bank account                  (total)
    Credit Undeposited Funds             (each payment / sales receipt)
    Credit Other account                 (each "other" line)
"""

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.money import ZERO
from app.models import BankDeposit, DepositLine
from app.models.enums import AccountType, DepositLineSource, JournalSource
from app.repositories.account_repository import AccountRepository
from app.repositories.sales_repositories import DepositRepository, PaymentRepository, SalesDocumentRepository
from app.schemas.sales_extras import DepositCreate, UndepositedItem
from app.seed.default_accounts import SystemAccount
from app.services.base import BaseService
from app.services.ledger_service import LedgerLine, LedgerService
from app.services.system_accounts import SystemAccounts


class DepositService(BaseService):
    def __init__(
        self,
        session,
        repository: DepositRepository,
        payment_repository: PaymentRepository,
        sales_document_repository: SalesDocumentRepository,
        account_repository: AccountRepository,
        system_accounts: SystemAccounts,
        ledger: LedgerService,
    ):
        super().__init__(session)
        self.repository = repository
        self.payment_repository = payment_repository
        self.sales_document_repository = sales_document_repository
        self.account_repository = account_repository
        self.system_accounts = system_accounts
        self.ledger = ledger

    def list(self, company_id: int) -> list[BankDeposit]:
        return self.repository.list_all(company_id)

    def get(self, company_id: int, deposit_id: int) -> BankDeposit:
        deposit = self.repository.get(company_id, deposit_id)
        if deposit is None:
            raise NotFoundError("Deposit not found.")
        return deposit

    def list_undeposited(self, company_id: int) -> list[UndepositedItem]:
        """Payments and sales receipts waiting in Undeposited Funds."""
        undeposited = self.system_accounts.get(company_id, SystemAccount.UNDEPOSITED_FUNDS)
        items = []
        for payment in self.payment_repository.list_undeposited(company_id, undeposited.id):
            items.append(
                UndepositedItem(
                    source_type=DepositLineSource.PAYMENT,
                    source_id=payment.id,
                    item_date=payment.payment_date,
                    customer_name=payment.customer.display_name,
                    reference=payment.reference_no or ("Payment #" + str(payment.id)),
                    amount=payment.amount,
                )
            )
        for receipt in self.sales_document_repository.list_undeposited_receipts(company_id, undeposited.id):
            items.append(
                UndepositedItem(
                    source_type=DepositLineSource.SALES_RECEIPT,
                    source_id=receipt.id,
                    item_date=receipt.doc_date,
                    customer_name=receipt.customer.display_name,
                    reference="Sales receipt " + receipt.doc_number,
                    amount=receipt.total,
                )
            )
        items.sort(key=lambda item: item.item_date)
        return items

    def create(self, company_id: int, data: DepositCreate) -> BankDeposit:
        bank = self.account_repository.get(company_id, data.bank_account_id)
        undeposited = self.system_accounts.get(company_id, SystemAccount.UNDEPOSITED_FUNDS)
        if bank is None or bank.account_type != AccountType.ASSET or bank.id == undeposited.id:
            raise BusinessRuleError("Choose the bank account the money is deposited into.")
        if len(data.items) == 0 and len(data.other_lines) == 0:
            raise BusinessRuleError("Choose at least one payment or add a line.")

        deposit = BankDeposit(company_id=company_id, deposit_date=data.deposit_date, bank_account_id=bank.id, memo=data.memo)
        records_to_mark = []
        total = ZERO

        for item in data.items:
            record, amount, label = self.find_undeposited_record(company_id, item.source_type, item.source_id, undeposited.id)
            deposit.lines.append(
                DepositLine(
                    source_type=item.source_type,
                    source_id=item.source_id,
                    account_id=undeposited.id,
                    description=label,
                    amount=amount,
                )
            )
            records_to_mark.append(record)
            total += amount

        for line in data.other_lines:
            account = self.account_repository.get(company_id, line.account_id)
            if account is None or account.id == bank.id:
                raise BusinessRuleError("Choose a different account for each extra line.")
            deposit.lines.append(
                DepositLine(
                    source_type=DepositLineSource.OTHER,
                    account_id=account.id,
                    description=line.description,
                    amount=line.amount,
                )
            )
            total += line.amount

        deposit.total = total
        self.repository.add(deposit)

        ledger_lines = [LedgerLine(bank.id, debit=total)]
        for line in deposit.lines:
            ledger_lines.append(LedgerLine(line.account_id, credit=line.amount, description=line.description))
        entry = self.ledger.post(
            company_id=company_id,
            entry_date=data.deposit_date,
            source_type=JournalSource.DEPOSIT,
            source_id=deposit.id,
            memo=data.memo or "Bank deposit",
            lines=ledger_lines,
        )
        deposit.journal_entry_id = entry.id

        for record in records_to_mark:
            record.deposit_id = deposit.id

        self.commit()
        return deposit

    def find_undeposited_record(self, company_id: int, source_type: DepositLineSource, source_id: int, undeposited_id: int):
        """Return (record, amount, description) or raise if it cannot be deposited."""
        if source_type == DepositLineSource.PAYMENT:
            payment = self.payment_repository.get(company_id, source_id)
            if payment is None or payment.deposit_account_id != undeposited_id or payment.deposit_id is not None:
                raise BusinessRuleError(f"Payment #{source_id} is not waiting in Undeposited Funds.")
            return payment, payment.amount, "Payment from " + payment.customer.display_name

        if source_type == DepositLineSource.SALES_RECEIPT:
            receipt = self.sales_document_repository.get(company_id, source_id)
            if receipt is None or receipt.money_account_id != undeposited_id or receipt.deposit_id is not None:
                raise BusinessRuleError(f"Sales receipt #{source_id} is not waiting in Undeposited Funds.")
            return receipt, receipt.total, "Sales receipt " + receipt.doc_number

        raise BusinessRuleError("Use an extra line for money that is not a payment or sales receipt.")
