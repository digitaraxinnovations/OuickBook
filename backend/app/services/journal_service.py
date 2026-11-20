from app.core.exceptions import NotFoundError
from app.models import JournalEntry
from app.models.enums import JournalSource
from app.repositories.journal_repository import JournalRepository
from app.schemas.journal import JournalEntryCreate
from app.services.base import BaseService
from app.schemas.tracking import TrackingInput
from app.services.ledger_service import LedgerLine, LedgerService
from app.services.tracking_service import TrackingService


class JournalService(BaseService):
    """Viewing the ledger and writing manual journal entries."""

    def __init__(self, session, journal_repository: JournalRepository, ledger: LedgerService, tracking: TrackingService):
        super().__init__(session)
        self.journal_repository = journal_repository
        self.ledger = ledger
        self.tracking = tracking

    def list(self, company_id: int) -> list[JournalEntry]:
        return self.journal_repository.list_all(company_id)

    def get(self, company_id: int, entry_id: int) -> JournalEntry:
        entry = self.journal_repository.get(company_id, entry_id)
        if entry is None:
            raise NotFoundError("Journal entry not found.")
        return entry

    def create_manual(self, company_id: int, data: JournalEntryCreate) -> JournalEntry:
        tags = self.tracking.check(company_id, TrackingInput(tag_ids=data.tag_ids))
        lines = []
        for line in data.lines:
            # Each line can have its own class, location and project.
            line_tracking = self.tracking.check(
                company_id, TrackingInput(class_id=line.class_id, location_id=line.location_id, project_id=line.project_id)
            )
            lines.append(
                LedgerLine(
                    line.account_id,
                    debit=line.debit,
                    credit=line.credit,
                    description=line.description,
                    class_id=line_tracking.class_id,
                    location_id=line_tracking.location_id,
                    project_id=line_tracking.project_id,
                )
            )

        entry = self.ledger.post(
            company_id=company_id,
            entry_date=data.entry_date,
            source_type=JournalSource.MANUAL,
            memo=data.memo,
            lines=lines,
            tracking=tags,
        )
        self.commit()
        return entry
