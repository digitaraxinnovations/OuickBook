"""
How reliably each customer pays.

Worked out from the books every time it is asked for: for every fully paid
invoice, how many days after the due date the last payment arrived.
Nothing is saved and nothing is changed.
"""

from datetime import date

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.models import Invoice
from app.models.enums import InvoiceStatus
from app.repositories.contact_repository import CustomerRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.sales_repositories import PaymentRepository
from app.schemas.payment_score import PaymentScore, ScoreRating

SUGGESTIONS = {
    ScoreRating.NOT_ENOUGH_HISTORY: "Use your normal terms until there is more history.",
    ScoreRating.GOOD: "Keep the current terms.",
    ScoreRating.WATCH: "Send a reminder before the due date.",
    ScoreRating.RISKY: "Ask for a deposit or payment up front.",
}


class PaymentHistory:
    """What one customer has done so far."""

    def __init__(self):
        self.days_late: list[int] = []  # one entry per paid invoice, 0 = on time
        self.overdue_invoices = 0

    @property
    def late_invoices(self) -> int:
        return len([days for days in self.days_late if days > 0])

    @property
    def average_days_late(self) -> int:
        if not self.days_late:
            return 0
        return int(sum(self.days_late) / len(self.days_late) + 0.5)


class PaymentScoreService:
    def __init__(
        self,
        settings: Settings,
        customer_repository: CustomerRepository,
        invoice_repository: InvoiceRepository,
        payment_repository: PaymentRepository,
    ):
        self.settings = settings
        self.customer_repository = customer_repository
        self.invoice_repository = invoice_repository
        self.payment_repository = payment_repository

    def list(self, company_id: int, today: date | None = None) -> list[PaymentScore]:
        invoices = self.invoice_repository.list_filtered(company_id)
        histories = self.histories(company_id, invoices, today or date.today())
        scores = []
        for customer in self.customer_repository.list_all(company_id):
            scores.append(self.score(customer.id, histories.get(customer.id, PaymentHistory())))
        return scores

    def get(self, company_id: int, customer_id: int, today: date | None = None) -> PaymentScore:
        if self.customer_repository.get(company_id, customer_id) is None:
            raise NotFoundError("Customer not found.")
        invoices = self.invoice_repository.list_filtered(company_id, customer_id=customer_id)
        histories = self.histories(company_id, invoices, today or date.today())
        return self.score(customer_id, histories.get(customer_id, PaymentHistory()))

    def histories(self, company_id: int, invoices: list[Invoice], today: date) -> dict[int, PaymentHistory]:
        paid_on = self.payment_repository.last_payment_dates(company_id)
        result: dict[int, PaymentHistory] = {}
        for invoice in invoices:
            history = result.setdefault(invoice.customer_id, PaymentHistory())
            if invoice.status == InvoiceStatus.PAID and invoice.id in paid_on:
                history.days_late.append(max((paid_on[invoice.id] - invoice.due_date).days, 0))
            elif invoice.balance_due > 0 and (today - invoice.due_date).days > self.settings.score_overdue_days:
                history.overdue_invoices += 1
        return result

    def score(self, customer_id: int, history: PaymentHistory) -> PaymentScore:
        rating = self.rating_for(history)
        return PaymentScore(
            customer_id=customer_id,
            rating=rating,
            paid_invoices=len(history.days_late),
            late_invoices=history.late_invoices,
            average_days_late=history.average_days_late,
            overdue_invoices=history.overdue_invoices,
            reason=self.reason_for(history),
            suggestion=SUGGESTIONS[rating],
        )

    def rating_for(self, history: PaymentHistory) -> ScoreRating:
        rating = ScoreRating.NOT_ENOUGH_HISTORY
        if len(history.days_late) >= self.settings.score_min_invoices:
            if history.average_days_late <= self.settings.score_good_max_days:
                rating = ScoreRating.GOOD
            elif history.average_days_late <= self.settings.score_watch_max_days:
                rating = ScoreRating.WATCH
            else:
                rating = ScoreRating.RISKY
        # A long overdue invoice is a warning sign even for a good or new customer.
        if history.overdue_invoices and rating in (ScoreRating.NOT_ENOUGH_HISTORY, ScoreRating.GOOD):
            rating = ScoreRating.WATCH
        return rating

    def reason_for(self, history: PaymentHistory) -> str:
        paid = len(history.days_late)
        if paid == 0:
            reason = "No paid invoices yet."
        elif history.late_invoices == 0:
            reason = f"Paid all {paid} invoice(s) on time."
        else:
            reason = f"Paid {history.late_invoices} of {paid} invoice(s) late, {history.average_days_late} day(s) late on average."
        if history.overdue_invoices:
            days = self.settings.score_overdue_days
            reason += f" {history.overdue_invoices} unpaid invoice(s) more than {days} days overdue."
        return reason
