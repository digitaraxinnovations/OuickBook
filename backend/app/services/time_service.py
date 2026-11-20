"""
Time tracking.

A time entry is hours worked by an employee or a contractor (vendor). Billable
time for a customer can be added to that customer's next invoice (see
InvoiceService); once invoiced it cannot be changed until the invoice is voided.
"""

from datetime import date

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import TimeEntry
from app.repositories.contact_repository import CustomerRepository, VendorRepository
from app.repositories.payroll_repositories import EmployeeRepository, TimeEntryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.payroll import TimeEntryWrite
from app.services.base import BaseService
from app.repositories.tracking_repositories import ProjectRepository


class TimeService(BaseService):
    def __init__(
        self,
        session,
        repository: TimeEntryRepository,
        employee_repository: EmployeeRepository,
        vendor_repository: VendorRepository,
        customer_repository: CustomerRepository,
        product_repository: ProductRepository,
        project_repository: ProjectRepository,
    ):
        super().__init__(session)
        self.repository = repository
        self.employee_repository = employee_repository
        self.vendor_repository = vendor_repository
        self.customer_repository = customer_repository
        self.product_repository = product_repository
        self.project_repository = project_repository

    def list(self, company_id: int, start: date | None, end: date | None, employee_id: int | None, customer_id: int | None, unbilled_only: bool) -> list[TimeEntry]:
        return self.repository.list_filtered(company_id, start, end, employee_id, customer_id, unbilled_only)

    def get(self, company_id: int, entry_id: int) -> TimeEntry:
        entry = self.repository.get(company_id, entry_id)
        if entry is None:
            raise NotFoundError("Time entry not found.")
        return entry

    def save(self, company_id: int, data: TimeEntryWrite, entry_id: int | None = None) -> TimeEntry:
        self.validate(company_id, data)
        if entry_id is None:
            entry = TimeEntry(company_id=company_id)
        else:
            entry = self.get(company_id, entry_id)
            self.check_not_invoiced(entry)
        for field_name, value in data.model_dump().items():
            setattr(entry, field_name, value)
        if entry.bill_rate is None and entry.product_id is not None:
            entry.bill_rate = self.product_repository.get(company_id, entry.product_id).sales_price
        if entry_id is None:
            self.repository.add(entry)
        self.commit()
        return entry

    def delete(self, company_id: int, entry_id: int) -> None:
        entry = self.get(company_id, entry_id)
        self.check_not_invoiced(entry)
        self.session.delete(entry)
        self.commit()

    def check_not_invoiced(self, entry: TimeEntry) -> None:
        if entry.invoice_id is not None:
            raise BusinessRuleError("This time is on an invoice. Void the invoice to change it.")

    def validate(self, company_id: int, data: TimeEntryWrite) -> None:
        if (data.employee_id is None) == (data.vendor_id is None):
            raise BusinessRuleError("Choose who did the work: one employee or one contractor.")
        if data.employee_id is not None and self.employee_repository.get(company_id, data.employee_id) is None:
            raise BusinessRuleError("That employee does not exist.")
        if data.vendor_id is not None and self.vendor_repository.get(company_id, data.vendor_id) is None:
            raise BusinessRuleError("That contractor does not exist.")
        if data.customer_id is not None and self.customer_repository.get(company_id, data.customer_id) is None:
            raise BusinessRuleError("That customer does not exist.")
        if data.product_id is not None and self.product_repository.get(company_id, data.product_id) is None:
            raise BusinessRuleError("That service does not exist.")
        if data.billable and data.customer_id is None:
            raise BusinessRuleError("Billable time needs a customer.")
        if data.project_id is not None:
            project = self.project_repository.get(company_id, data.project_id)
            if project is None:
                raise BusinessRuleError("That project does not exist.")
            if data.customer_id is not None and project.customer_id != data.customer_id:
                raise BusinessRuleError("That project belongs to another customer.")
