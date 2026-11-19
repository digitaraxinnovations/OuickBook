from datetime import date

from pydantic import Field, ValidationError

from app.core.exceptions import BusinessRuleError
from app.models.enums import RecurringType
from app.recurring.base import RecurringHandler
from app.schemas.common import CleanStringsModel
from app.schemas.journal import JournalEntryCreate, JournalLineCreate
from app.services.journal_service import JournalService
from app.services.ledger_service import LedgerLine, LedgerService


class JournalEntryTemplate(CleanStringsModel):
    """A journal entry without its date."""

    memo: str | None = Field(default=None, max_length=500)
    lines: list[JournalLineCreate] = Field(min_length=2)


class JournalEntryRecurringHandler(RecurringHandler):
    transaction_type = RecurringType.JOURNAL_ENTRY

    def __init__(self, journal_service: JournalService, ledger: LedgerService):
        self.journal_service = journal_service
        self.ledger = ledger

    def check_template(self, company_id: int, template: dict) -> dict:
        try:
            parsed = JournalEntryTemplate.model_validate(template)
        except ValidationError as error:
            first = error.errors()[0]
            raise BusinessRuleError("Template: " + first["msg"])

        # Check the lines balance now, so the user finds out when saving - not next month.
        lines = []
        for line in parsed.lines:
            lines.append(LedgerLine(line.account_id, debit=line.debit, credit=line.credit))
        self.ledger.check_lines(company_id, lines)

        return parsed.model_dump(mode="json")

    def create_transaction(self, company_id: int, template: dict, transaction_date: date) -> int:
        data = JournalEntryCreate(
            entry_date=transaction_date,
            memo=template.get("memo"),
            lines=template["lines"],
        )
        entry = self.journal_service.create_manual(company_id, data)
        return entry.id
