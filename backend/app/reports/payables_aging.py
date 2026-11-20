from datetime import date

from app.core.money import ZERO
from app.reports.base import Report
from app.reports.receivables_aging import AGING_BUCKETS
from app.repositories.purchase_repositories import PurchaseDocumentRepository
from app.schemas.report import ReportResult, ReportRow


class PayablesAgingReport(Report):
    key = "ap-aging"
    title = "Accounts Payable Aging"
    description = "Unpaid bills grouped by how many days past due they are."
    uses_start_date = False

    def __init__(self, purchase_repository: PurchaseDocumentRepository):
        self.purchase_repository = purchase_repository

    def generate(self, company_id: int, start_date: date | None, end_date: date) -> ReportResult:
        rows_per_bucket = {}
        for title, _low, _high in AGING_BUCKETS:
            rows_per_bucket[title] = []

        for bill in self.purchase_repository.list_unpaid_bills(company_id):
            if bill.doc_date > end_date:
                continue
            days_overdue = (end_date - bill.due_date).days
            label = f"Bill {bill.doc_number or '#' + str(bill.id)} - {bill.vendor.display_name}"
            rows_per_bucket[self.find_bucket(days_overdue)].append(ReportRow(label=label, amount=bill.balance))

        sections = []
        grand_total = ZERO
        for title, _low, _high in AGING_BUCKETS:
            section = self.make_section(title, rows_per_bucket[title])
            sections.append(section)
            grand_total += section.total

        return self.make_result(start_date, end_date, sections, [ReportRow(label="Total unpaid bills", amount=grand_total)])

    def find_bucket(self, days_overdue: int) -> str:
        for title, low, high in AGING_BUCKETS:
            if (low is None or days_overdue >= low) and (high is None or days_overdue <= high):
                return title
        return AGING_BUCKETS[-1][0]
