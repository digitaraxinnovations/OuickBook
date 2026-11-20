"""
Sales Tax Liability: for each agency, the tax charged per rate in the period,
plus adjustments, minus payments made. The section total is what is still owed
for that period.
"""

from datetime import date

from app.core.money import ZERO
from app.reports.base import Report
from app.repositories.tax_repositories import (
    SalesTaxAdjustmentRepository,
    SalesTaxLineRepository,
    SalesTaxPaymentRepository,
    TaxAgencyRepository,
)
from app.schemas.report import ReportOptions, ReportResult, ReportRow

EARLIEST_DATE = date(1900, 1, 1)


class SalesTaxLiabilityReport(Report):
    key = "sales-tax-liability"
    group = "Sales tax"
    title = "Sales Tax Liability"
    description = "Sales tax charged per agency and rate, adjustments and payments for a period."

    def __init__(
        self,
        agency_repository: TaxAgencyRepository,
        tax_line_repository: SalesTaxLineRepository,
        payment_repository: SalesTaxPaymentRepository,
        adjustment_repository: SalesTaxAdjustmentRepository,
    ):
        self.agency_repository = agency_repository
        self.tax_line_repository = tax_line_repository
        self.payment_repository = payment_repository
        self.adjustment_repository = adjustment_repository

    def generate(self, company_id: int, start_date: date | None, end_date: date, options: ReportOptions) -> ReportResult:
        start = start_date or EARLIEST_DATE
        sections = []
        total_owed = ZERO
        total_taxable = ZERO

        for agency in self.agency_repository.list_all(company_id):
            rows = self.rate_rows(company_id, agency.id, start, end_date)
            adjustments = self.adjustment_repository.total_between(company_id, agency.id, start, end_date)
            payments = self.payment_repository.total_paid_between(company_id, agency.id, start, end_date)
            if adjustments != 0:
                rows.append(ReportRow(label="Adjustments", amount=adjustments))
            if payments != 0:
                rows.append(ReportRow(label="Payments made", amount=-payments))
            if not rows:
                continue
            section = self.make_section(agency.name, rows)
            sections.append(section)
            total_owed += section.total

        # A sale taxed by a combined rate has one tax line per rate, each with
        # the same taxable amount - count every sale once.
        taxable_per_sale = {}
        for line in self.tax_line_repository.list_between(company_id, start, end_date):
            taxable_per_sale[(line.source_type, line.source_id)] = line.taxable_amount
        for amount in taxable_per_sale.values():
            total_taxable += amount

        summary = [
            ReportRow(label="Taxable sales (all rates)", amount=total_taxable),
            ReportRow(label="Sales tax still owed for the period", amount=total_owed),
        ]
        return self.make_result(start_date, end_date, sections, summary)

    def rate_rows(self, company_id: int, agency_id: int, start: date, end: date) -> list[ReportRow]:
        """One row per rate: the tax charged, with the taxable sales in the label."""
        taxable_per_rate = {}
        tax_per_rate = {}
        rates = {}
        for line in self.tax_line_repository.list_between(company_id, start, end, agency_id):
            rate_id = line.tax_rate_id
            rates[rate_id] = line.tax_rate
            taxable_per_rate[rate_id] = taxable_per_rate.get(rate_id, ZERO) + line.taxable_amount
            tax_per_rate[rate_id] = tax_per_rate.get(rate_id, ZERO) + line.tax_amount

        rows = []
        for rate_id, rate in rates.items():
            percent = rate.rate.normalize()
            label = f"{rate.name} ({percent}%) on taxable sales of {taxable_per_rate[rate_id]:,.2f}"
            rows.append(ReportRow(label=label, amount=tax_per_rate[rate_id]))
        return rows
