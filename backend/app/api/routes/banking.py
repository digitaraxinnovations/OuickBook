from fastapi import APIRouter, Depends, Response, status

from app.api.deps import (
    get_bank_import_service,
    get_bank_review_service,
    get_bank_rule_service,
    get_current_user,
    get_reconciliation_service,
    get_transfer_service,
)
from app.models import User
from app.models.enums import BankTransactionStatus
from app.schemas.banking import (
    AddTransactionRequest,
    BankAccountOverview,
    BankRuleRead,
    BankRuleWrite,
    BankTransactionRead,
    BatchActionResult,
    DiscrepancyItem,
    MatchCandidate,
    MatchRequest,
    ReconciliationRead,
    ReconciliationReport,
    ReconciliationSelection,
    ReconciliationStart,
    ReconciliationWorkspace,
    StatementImportRequest,
    StatementImportResult,
    TransferCreate,
    TransferRead,
)
from app.services.bank_import_service import BankImportService
from app.services.bank_review_service import BankReviewService
from app.services.bank_rule_service import BankRuleService
from app.services.reconciliation_service import ReconciliationService
from app.services.transfer_service import TransferService

router = APIRouter(prefix="/banking", tags=["Banking"])


# ---------- overview ----------

@router.get("/accounts", response_model=list[BankAccountOverview])
def banking_overview(
    user: User = Depends(get_current_user),
    review: BankReviewService = Depends(get_bank_review_service),
    reconciliations: ReconciliationService = Depends(get_reconciliation_service),
):
    return review.overview(user.company_id, reconciliations.last_reconciled_dates(user.company_id))


# ---------- transfers ----------

@router.get("/transfers", response_model=list[TransferRead])
def list_transfers(user: User = Depends(get_current_user), service: TransferService = Depends(get_transfer_service)):
    return service.list(user.company_id)


@router.post("/transfers", response_model=TransferRead, status_code=status.HTTP_201_CREATED)
def create_transfer(data: TransferCreate, user: User = Depends(get_current_user), service: TransferService = Depends(get_transfer_service)):
    return service.create(user.company_id, data)


@router.post("/transfers/{transfer_id}/void", response_model=TransferRead)
def void_transfer(transfer_id: int, user: User = Depends(get_current_user), service: TransferService = Depends(get_transfer_service)):
    return service.void(user.company_id, transfer_id)


# ---------- importing ----------

@router.post("/import", response_model=StatementImportResult)
def import_statement(
    data: StatementImportRequest,
    user: User = Depends(get_current_user),
    service: BankImportService = Depends(get_bank_import_service),
):
    """Upload a CSV, OFX or QFX statement. Lines already imported are skipped."""
    return service.import_statement(user.company_id, data)


@router.post("/accounts/{account_id}/sync", response_model=StatementImportResult)
def sync_bank_feed(account_id: int, user: User = Depends(get_current_user), service: BankImportService = Depends(get_bank_import_service)):
    """Download new lines from the bank feed (EXT - needs BANK_FEED_PROVIDER)."""
    return service.sync_feed(user.company_id, account_id)


@router.post("/apply-rules", response_model=BatchActionResult)
def apply_rules(
    account_id: int | None = None,
    user: User = Depends(get_current_user),
    service: BankImportService = Depends(get_bank_import_service),
):
    return BatchActionResult(count=service.apply_rules_to_queue(user.company_id, account_id))


# ---------- review queue ----------

@router.get("/transactions", response_model=list[BankTransactionRead])
def list_bank_transactions(
    account_id: int | None = None,
    status: BankTransactionStatus | None = None,
    user: User = Depends(get_current_user),
    service: BankReviewService = Depends(get_bank_review_service),
):
    return service.list(user.company_id, account_id, status)


@router.get("/transactions/{transaction_id}/matches", response_model=list[MatchCandidate])
def find_matches(transaction_id: int, user: User = Depends(get_current_user), service: BankReviewService = Depends(get_bank_review_service)):
    return service.find_matches(user.company_id, transaction_id)


@router.post("/transactions/{transaction_id}/match", response_model=BankTransactionRead)
def match_transaction(
    transaction_id: int,
    data: MatchRequest,
    user: User = Depends(get_current_user),
    service: BankReviewService = Depends(get_bank_review_service),
):
    return service.match(user.company_id, transaction_id, data.journal_line_id)


@router.post("/transactions/{transaction_id}/add", response_model=BankTransactionRead)
def add_transaction(
    transaction_id: int,
    data: AddTransactionRequest,
    user: User = Depends(get_current_user),
    service: BankReviewService = Depends(get_bank_review_service),
):
    """Create the transaction (expense, deposit, transfer or card credit). Several lines = split."""
    return service.add(user.company_id, transaction_id, data)


@router.post("/transactions/{transaction_id}/exclude", response_model=BankTransactionRead)
def exclude_transaction(transaction_id: int, user: User = Depends(get_current_user), service: BankReviewService = Depends(get_bank_review_service)):
    return service.exclude(user.company_id, transaction_id)


@router.post("/transactions/{transaction_id}/undo", response_model=BankTransactionRead)
def undo_transaction(transaction_id: int, user: User = Depends(get_current_user), service: BankReviewService = Depends(get_bank_review_service)):
    return service.undo(user.company_id, transaction_id)


# ---------- rules ----------

@router.get("/rules", response_model=list[BankRuleRead])
def list_rules(user: User = Depends(get_current_user), service: BankRuleService = Depends(get_bank_rule_service)):
    return service.list(user.company_id)


@router.post("/rules", response_model=BankRuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(data: BankRuleWrite, user: User = Depends(get_current_user), service: BankRuleService = Depends(get_bank_rule_service)):
    return service.create(user.company_id, data)


@router.put("/rules/{rule_id}", response_model=BankRuleRead)
def update_rule(rule_id: int, data: BankRuleWrite, user: User = Depends(get_current_user), service: BankRuleService = Depends(get_bank_rule_service)):
    return service.update(user.company_id, rule_id, data)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, user: User = Depends(get_current_user), service: BankRuleService = Depends(get_bank_rule_service)):
    service.delete(user.company_id, rule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- reconciliation ----------

@router.get("/reconciliations", response_model=list[ReconciliationRead])
def reconciliation_history(
    account_id: int,
    user: User = Depends(get_current_user),
    service: ReconciliationService = Depends(get_reconciliation_service),
):
    return service.history(user.company_id, account_id)


@router.post("/reconciliations", response_model=ReconciliationRead, status_code=status.HTTP_201_CREATED)
def start_reconciliation(
    data: ReconciliationStart,
    user: User = Depends(get_current_user),
    service: ReconciliationService = Depends(get_reconciliation_service),
):
    return service.start(user.company_id, data)


@router.get("/reconciliations/discrepancies", response_model=list[DiscrepancyItem])
def reconciliation_discrepancies(
    account_id: int,
    user: User = Depends(get_current_user),
    service: ReconciliationService = Depends(get_reconciliation_service),
):
    return service.discrepancies(user.company_id, account_id)


@router.get("/reconciliations/{reconciliation_id}", response_model=ReconciliationWorkspace)
def reconciliation_workspace(
    reconciliation_id: int,
    user: User = Depends(get_current_user),
    service: ReconciliationService = Depends(get_reconciliation_service),
):
    return service.workspace(user.company_id, reconciliation_id)


@router.put("/reconciliations/{reconciliation_id}/selection", response_model=ReconciliationWorkspace)
def save_reconciliation_selection(
    reconciliation_id: int,
    data: ReconciliationSelection,
    user: User = Depends(get_current_user),
    service: ReconciliationService = Depends(get_reconciliation_service),
):
    return service.select(user.company_id, reconciliation_id, data.journal_line_ids)


@router.post("/reconciliations/{reconciliation_id}/finish", response_model=ReconciliationRead)
def finish_reconciliation(
    reconciliation_id: int,
    user: User = Depends(get_current_user),
    service: ReconciliationService = Depends(get_reconciliation_service),
):
    return service.finish(user.company_id, reconciliation_id)


@router.post("/reconciliations/{reconciliation_id}/undo", response_model=ReconciliationRead)
def undo_reconciliation(
    reconciliation_id: int,
    user: User = Depends(get_current_user),
    service: ReconciliationService = Depends(get_reconciliation_service),
):
    return service.undo(user.company_id, reconciliation_id)


@router.delete("/reconciliations/{reconciliation_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_reconciliation(
    reconciliation_id: int,
    user: User = Depends(get_current_user),
    service: ReconciliationService = Depends(get_reconciliation_service),
):
    service.cancel(user.company_id, reconciliation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/reconciliations/{reconciliation_id}/report", response_model=ReconciliationReport)
def reconciliation_report(
    reconciliation_id: int,
    user: User = Depends(get_current_user),
    service: ReconciliationService = Depends(get_reconciliation_service),
):
    return service.report(user.company_id, reconciliation_id)
