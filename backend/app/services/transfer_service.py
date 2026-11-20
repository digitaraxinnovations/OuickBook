"""
Transfers between your own accounts (e.g. savings -> checking, or paying
the credit card from checking).

    Debit  to_account      (money arrives / the card balance goes down)
    Credit from_account    (money leaves)
"""

from datetime import date

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import Account, Transfer
from app.models.enums import AccountType, JournalSource
from app.repositories.account_repository import AccountRepository
from app.repositories.banking_repositories import TransferRepository
from app.repositories.journal_repository import JournalRepository
from app.schemas.banking import TransferCreate
from app.seed.default_accounts import SystemAccount
from app.services.base import BaseService
from app.services.ledger_service import LedgerLine, LedgerService

# Accounts the app manages itself cannot take part in a transfer.
NOT_TRANSFERABLE = (SystemAccount.ACCOUNTS_RECEIVABLE, SystemAccount.ACCOUNTS_PAYABLE)


class TransferService(BaseService):
    def __init__(
        self,
        session,
        repository: TransferRepository,
        account_repository: AccountRepository,
        journal_repository: JournalRepository,
        ledger: LedgerService,
    ):
        super().__init__(session)
        self.repository = repository
        self.account_repository = account_repository
        self.journal_repository = journal_repository
        self.ledger = ledger

    def list(self, company_id: int) -> list[Transfer]:
        return self.repository.list_all(company_id)

    def get(self, company_id: int, transfer_id: int) -> Transfer:
        transfer = self.repository.get(company_id, transfer_id)
        if transfer is None:
            raise NotFoundError("Transfer not found.")
        return transfer

    def create(self, company_id: int, data: TransferCreate) -> Transfer:
        from_account = self.check_account(company_id, data.from_account_id)
        to_account = self.check_account(company_id, data.to_account_id)
        if from_account.id == to_account.id:
            raise BusinessRuleError("Choose two different accounts.")

        transfer = Transfer(
            company_id=company_id,
            transfer_date=data.transfer_date,
            from_account_id=from_account.id,
            to_account_id=to_account.id,
            amount=data.amount,
            memo=data.memo,
            is_void=False,
        )
        self.repository.add(transfer)
        entry = self.ledger.post(
            company_id=company_id,
            entry_date=data.transfer_date,
            source_type=JournalSource.TRANSFER,
            source_id=transfer.id,
            memo=data.memo or f"Transfer from {from_account.name} to {to_account.name}",
            lines=[LedgerLine(to_account.id, debit=data.amount), LedgerLine(from_account.id, credit=data.amount)],
        )
        transfer.journal_entry_id = entry.id
        self.commit()
        return transfer

    def check_account(self, company_id: int, account_id: int) -> Account:
        account = self.account_repository.get(company_id, account_id)
        is_allowed = (
            account is not None
            and account.is_active
            and account.account_type in (AccountType.ASSET, AccountType.LIABILITY)
            and account.system_key not in NOT_TRANSFERABLE
        )
        if not is_allowed:
            raise BusinessRuleError("Transfers are between bank, credit card and other asset or liability accounts.")
        return account

    def void(self, company_id: int, transfer_id: int) -> Transfer:
        transfer = self.get(company_id, transfer_id)
        if transfer.is_void:
            raise BusinessRuleError("This transfer is already void.")
        original = self.journal_repository.get(company_id, transfer.journal_entry_id)
        self.ledger.reverse(company_id, original, date.today(), JournalSource.TRANSFER, "Void of transfer")
        transfer.is_void = True
        self.commit()
        return transfer
