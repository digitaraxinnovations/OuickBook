"""
Brings bank lines in (statement files or a bank feed), skips ones already
imported, and applies bank rules to the new ones.
"""

from app.banking.rule_engine import first_matching_rule
from app.banking.statement_parsers import StatementLine, parser_for
from app.core.exceptions import AppError
from app.integrations.bank_feeds import BankFeedProvider
from app.models import BankTransaction
from app.models.enums import BankTransactionStatus
from app.repositories.banking_repositories import BankRuleRepository, BankTransactionRepository
from app.schemas.banking import AddLineInput, AddTransactionRequest, StatementImportRequest, StatementImportResult
from app.services.bank_review_service import BankReviewService
from app.services.base import BaseService


class BankImportService(BaseService):
    def __init__(
        self,
        session,
        repository: BankTransactionRepository,
        rule_repository: BankRuleRepository,
        review_service: BankReviewService,
        feed_provider: BankFeedProvider,
    ):
        super().__init__(session)
        self.repository = repository
        self.rule_repository = rule_repository
        self.review_service = review_service
        self.feed_provider = feed_provider

    def import_statement(self, company_id: int, data: StatementImportRequest) -> StatementImportResult:
        self.review_service.check_banking_account(company_id, data.account_id)
        lines = parser_for(data.filename, data).parse(data.content)
        source = "OFX" if data.filename.lower().endswith((".ofx", ".qfx", ".qbo")) else "CSV"
        return self.save_lines(company_id, data.account_id, lines, source)

    def sync_feed(self, company_id: int, account_id: int) -> StatementImportResult:
        self.review_service.check_banking_account(company_id, account_id)
        lines = self.feed_provider.fetch_transactions(company_id, account_id, None)
        return self.save_lines(company_id, account_id, lines, "FEED")

    def save_lines(self, company_id: int, account_id: int, lines: list[StatementLine], source: str) -> StatementImportResult:
        existing = self.repository.existing_external_ids(company_id, account_id)
        new_transactions = []
        duplicates = 0
        for line in lines:
            if line.external_id in existing:
                duplicates += 1
                continue
            existing.add(line.external_id)
            transaction = BankTransaction(
                company_id=company_id,
                account_id=account_id,
                txn_date=line.txn_date,
                description=line.description,
                amount=line.amount,
                external_id=line.external_id,
                source=source,
                status=BankTransactionStatus.FOR_REVIEW,
            )
            self.repository.add(transaction)
            new_transactions.append(transaction)
        self.commit()

        auto_added = self.apply_rules(company_id, new_transactions)
        return StatementImportResult(imported=len(new_transactions), duplicates=duplicates, auto_added=auto_added)

    def apply_rules_to_queue(self, company_id: int, account_id: int | None) -> int:
        """Run the rules again on everything still waiting for review."""
        waiting = self.repository.list_for(company_id, account_id, BankTransactionStatus.FOR_REVIEW)
        return self.apply_rules(company_id, waiting)

    def apply_rules(self, company_id: int, transactions: list[BankTransaction]) -> int:
        """Set suggestions from the first matching rule; add straight away for auto-add rules."""
        rules = self.rule_repository.list_all(company_id, active_only=True)
        auto_added = 0
        for transaction in transactions:
            rule = first_matching_rule(rules, transaction)
            if rule is None:
                continue
            transaction.rule_id = rule.id
            transaction.suggested_account_id = rule.category_account_id
            transaction.suggested_vendor_id = rule.vendor_id
            self.commit()
            if rule.auto_add:
                request = AddTransactionRequest(
                    vendor_id=rule.vendor_id,
                    lines=[AddLineInput(account_id=rule.category_account_id, amount=abs(transaction.amount))],
                )
                try:
                    self.review_service.add(company_id, transaction.id, request)
                    auto_added += 1
                except AppError:
                    # Leave it as a suggestion; the user can add it by hand.
                    self.session.rollback()
        return auto_added
