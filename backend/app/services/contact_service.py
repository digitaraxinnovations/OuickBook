from decimal import Decimal

from sqlalchemy import select

from app.core.exceptions import BusinessRuleError
from app.core.money import ZERO
from app.models import Customer, Vendor
from app.repositories.contact_repository import CustomerRepository, VendorRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.purchase_repositories import PurchaseDocumentRepository
from app.repositories.sales_repositories import PaymentRepository, PaymentTermRepository, SalesDocumentRepository
from app.repositories.tax_repositories import TaxCodeRepository
from app.schemas.contact import CustomerWrite, VendorWrite
from app.services.base import CrudService
from app.models import Expense
from app.services.currency_service import CurrencyService


class CustomerService(CrudService):
    model = Customer
    item_name = "Customer"

    def __init__(
        self,
        session,
        repository: CustomerRepository,
        invoice_repository: InvoiceRepository,
        sales_document_repository: SalesDocumentRepository,
        payment_repository: PaymentRepository,
        terms_repository: PaymentTermRepository,
        tax_code_repository: TaxCodeRepository,
        currencies: CurrencyService,
    ):
        super().__init__(session, repository)
        self.currencies = currencies
        self.tax_code_repository = tax_code_repository
        self.invoice_repository = invoice_repository
        self.sales_document_repository = sales_document_repository
        self.payment_repository = payment_repository
        self.terms_repository = terms_repository

    def validate(self, company_id: int, data: CustomerWrite) -> None:
        if data.terms_id is not None and self.terms_repository.get(company_id, data.terms_id) is None:
            raise BusinessRuleError("Those payment terms do not exist.")
        if data.default_tax_code_id is not None and self.tax_code_repository.get(company_id, data.default_tax_code_id) is None:
            raise BusinessRuleError("That sales tax rate does not exist.")
        data.currency_code = self.currencies.check_customer_currency(company_id, data.currency_code)

    def update(self, company_id: int, record_id: int, data: CustomerWrite):
        customer = self.get(company_id, record_id)
        new_currency = self.currencies.check_customer_currency(company_id, data.currency_code)
        if new_currency != customer.currency_code and self.invoice_repository.list_filtered(company_id, customer_id=customer.id):
            raise BusinessRuleError("This customer has invoices, so their currency cannot change.")
        return super().update(company_id, record_id, data)

    def open_balances(self, company_id: int) -> dict[int, Decimal]:
        """What each customer owes: unpaid invoices minus credit memos and overpayments not used yet."""
        balances = self.invoice_repository.open_balance_by_customer(company_id)
        credits = self.sales_document_repository.open_credit_by_customer(company_id)
        unapplied = self.payment_repository.unapplied_by_customer(company_id)

        result = {}
        for customer_id, amount in balances.items():
            result[customer_id] = amount
        for source in (credits, unapplied):
            for customer_id, amount in source.items():
                result[customer_id] = result.get(customer_id, ZERO) - amount
        return result

    def list_with_balances(self, company_id: int, active_only: bool = False) -> list[Customer]:
        customers = self.list(company_id, active_only)
        balances = self.open_balances(company_id)
        for customer in customers:
            # `open_balance` is not a database column - it is added for the response.
            customer.open_balance = balances.get(customer.id, ZERO)
        return customers

    def get_with_balance(self, company_id: int, customer_id: int) -> Customer:
        customer = self.get(company_id, customer_id)
        customer.open_balance = self.open_balances(company_id).get(customer.id, ZERO)
        return customer


class VendorService(CrudService):
    model = Vendor
    item_name = "Vendor"

    def __init__(
        self,
        session,
        repository: VendorRepository,
        purchase_repository: PurchaseDocumentRepository,
        terms_repository: PaymentTermRepository,
        currencies: CurrencyService,
    ):
        super().__init__(session, repository)
        self.purchase_repository = purchase_repository
        self.terms_repository = terms_repository
        self.currencies = currencies

    def validate(self, company_id: int, data: VendorWrite) -> None:
        if data.terms_id is not None and self.terms_repository.get(company_id, data.terms_id) is None:
            raise BusinessRuleError("Those payment terms do not exist.")
        data.currency_code = self.currencies.check_customer_currency(company_id, data.currency_code)

    def update(self, company_id: int, record_id: int, data: VendorWrite):
        vendor = self.get(company_id, record_id)
        new_currency = self.currencies.check_customer_currency(company_id, data.currency_code)
        if new_currency != vendor.currency_code and self.has_transactions(company_id, vendor.id):
            raise BusinessRuleError("This vendor has bills or expenses, so their currency cannot change.")
        return super().update(company_id, record_id, data)

    def has_transactions(self, company_id: int, vendor_id: int) -> bool:
        if self.purchase_repository.list_filtered(company_id, vendor_id=vendor_id):
            return True
        query = select(Expense.id).where(Expense.company_id == company_id, Expense.vendor_id == vendor_id).limit(1)
        return self.session.scalar(query) is not None

    def list_with_balances(self, company_id: int, active_only: bool = False) -> list[Vendor]:
        vendors = self.list(company_id, active_only)
        balances = self.purchase_repository.open_balance_by_vendor(company_id)
        for vendor in vendors:
            # `open_balance` is not a database column - it is added for the response.
            vendor.open_balance = balances.get(vendor.id, ZERO)
        return vendors

    def get_with_balance(self, company_id: int, vendor_id: int) -> Vendor:
        vendor = self.get(company_id, vendor_id)
        vendor.open_balance = self.purchase_repository.open_balance_by_vendor(company_id).get(vendor.id, ZERO)
        return vendor
