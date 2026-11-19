from app.core.money import ZERO
from app.models import Customer, Vendor
from app.repositories.contact_repository import CustomerRepository, VendorRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.services.base import CrudService


class CustomerService(CrudService):
    model = Customer
    item_name = "Customer"

    def __init__(self, session, repository: CustomerRepository, invoice_repository: InvoiceRepository):
        super().__init__(session, repository)
        self.invoice_repository = invoice_repository

    def list_with_balances(self, company_id: int, active_only: bool = False) -> list[Customer]:
        customers = self.list(company_id, active_only)
        balances = self.invoice_repository.open_balance_by_customer(company_id)
        for customer in customers:
            # `open_balance` is not a database column - it is added for the response.
            customer.open_balance = balances.get(customer.id, ZERO)
        return customers

    def get_with_balance(self, company_id: int, customer_id: int) -> Customer:
        customer = self.get(company_id, customer_id)
        balances = self.invoice_repository.open_balance_by_customer(company_id)
        customer.open_balance = balances.get(customer.id, ZERO)
        return customer


class VendorService(CrudService):
    model = Vendor
    item_name = "Vendor"

    def __init__(self, session, repository: VendorRepository):
        super().__init__(session, repository)
