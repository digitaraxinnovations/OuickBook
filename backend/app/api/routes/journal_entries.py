from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_journal_service
from app.models import User
from app.schemas.journal import JournalEntryCreate, JournalEntryRead
from app.services.journal_service import JournalService

router = APIRouter(prefix="/journal-entries", tags=["Journal Entries"])


@router.get("", response_model=list[JournalEntryRead])
def list_journal_entries(
    user: User = Depends(get_current_user),
    service: JournalService = Depends(get_journal_service),
):
    return service.list(user.company_id)


@router.get("/{entry_id}", response_model=JournalEntryRead)
def get_journal_entry(
    entry_id: int,
    user: User = Depends(get_current_user),
    service: JournalService = Depends(get_journal_service),
):
    return service.get(user.company_id, entry_id)


@router.post("", response_model=JournalEntryRead, status_code=status.HTTP_201_CREATED)
def create_journal_entry(
    data: JournalEntryCreate,
    user: User = Depends(get_current_user),
    service: JournalService = Depends(get_journal_service),
):
    return service.create_manual(user.company_id, data)
