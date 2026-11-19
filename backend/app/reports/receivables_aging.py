from datetime import date

from app.reports.base import Report
from app.repositories.invoice_repository import InvoiceRepository
from app.schemas.report import ReportResult, ReportRow

# (section title, smallest days overdue, largest days overdue)
AGING_BUCKETS = [
    ("Current", None, 0),
    ("1 - 30 days past due", 1, 30),
    ("31 - 60 days past due", 31, 60),
    ("61 - 90 days past due", 61, 90),
    ("91 or more days past due", 91, None),
]


class ReceivablesAgingReport(Report):
    key = "ar-aging"
    title = "Accounts Receivable Aging"
    description = "Unpaid invoices grouped by how many days past due they are."
    uses_start_date = False

    def __init__(self, invoice_repository: InvoiceRepository):
        self.invoice_repository = invoice_repository

    def generate(self, company_id: int, start_date: date | None, end_date: date) -> ReportResult:
        rows_per_bucket = {}
        for title, _low, _high in AGING_BUCKETS:
            rows_per_bucket[title] = []

        for invoice in self.invoice_repository.list_unpaid(company_id):
            if invoice.invoice_date > end_date:
                continue
            days_overdue = (end_date - invoice.due_date).days
            bucket_title = self.find_bucket(days_overdue)
            label = f"Invoice {invoice.invoice_number} - {invoice.customer.display_name}"
            rows_per_bucket[bucket_title].append(ReportRow(label=label, amount=invoice.balance_due))

        sections = []
        grand_total = 0
        for title, _low, _high in AGING_BUCKETS:
            section = self.make_section(title, rows_per_bucket[title])
            sections.append(section)
            grand_total += section.total

        return self.make_result(
            start_date,
            end_date,
            sections=sections,
            summary=[ReportRow(label="Total open receivables", amount=grand_total)],
        )

    def find_bucket(self, days_overdue: int) -> str:
        for title, low, high in AGING_BUCKETS:
            above_low = low is None or days_overdue >= low
            below_high = high is None or days_overdue <= high
            if above_low and below_high:
                return title
        return AGING_BUCKETS[-1][0]
