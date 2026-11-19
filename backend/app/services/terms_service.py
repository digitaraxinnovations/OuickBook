from datetime import date, timedelta

from app.core.exceptions import ConflictError, NotFoundError
from app.models import Company, Customer, PaymentTerm
from app.repositories.sales_repositories import PaymentTermRepository
from app.schemas.sales_extras import PaymentTermWrite
from app.seed.default_accounts import DEFAULT_PAYMENT_TERMS
from app.services.base import BaseService


class TermsService(BaseService):
    """The payment terms list (Due on receipt, Net 15, Net 30...)."""

    def __init__(self, session, repository: PaymentTermRepository):
        super().__init__(session)
        self.repository = repository

    def list(self, company_id: int) -> list[PaymentTerm]:
        terms = self.repository.list_all(company_id)
        if len(terms) == 0:
            # First use: give the company the standard terms.
            for template in DEFAULT_PAYMENT_TERMS:
                self.repository.add(PaymentTerm(company_id=company_id, name=template["name"], due_days=template["due_days"]))
            self.commit()
            terms = self.repository.list_all(company_id)
        return terms

    def get(self, company_id: int, term_id: int) -> PaymentTerm:
        term = self.repository.get(company_id, term_id)
        if term is None:
            raise NotFoundError("Payment term not found.")
        return term

    def create(self, company_id: int, data: PaymentTermWrite) -> PaymentTerm:
        if self.repository.get_by_name(company_id, data.name) is not None:
            raise ConflictError(f'A term named "{data.name}" already exists.')
        term = PaymentTerm(company_id=company_id, name=data.name, due_days=data.due_days, is_active=data.is_active)
        self.repository.add(term)
        self.commit()
        return term

    def update(self, company_id: int, term_id: int, data: PaymentTermWrite) -> PaymentTerm:
        term = self.get(company_id, term_id)
        if data.name != term.name and self.repository.get_by_name(company_id, data.name) is not None:
            raise ConflictError(f'A term named "{data.name}" already exists.')
        term.name = data.name
        term.due_days = data.due_days
        term.is_active = data.is_active
        self.commit()
        return term

    def due_date_for(
        self,
        company: Company,
        customer: Customer,
        invoice_date: date,
        terms_id: int | None,
    ) -> tuple[date, int | None]:
        """
        Work out the due date: the invoice's terms, else the customer's terms,
        else the company's default number of days. Returns (due date, terms id used).
        """
        chosen_id = terms_id or customer.terms_id
        if chosen_id is not None:
            term = self.get(company.id, chosen_id)
            return invoice_date + timedelta(days=term.due_days), term.id
        return invoice_date + timedelta(days=company.payment_terms_days), None
