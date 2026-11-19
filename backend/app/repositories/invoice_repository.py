from decimal import Decimal

from sqlalchemy import func, select

from app.models import Invoice
from app.models.enums import InvoiceStatus
from app.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository):
    model = Invoice

    def order_by_columns(self) -> list:
        return [Invoice.invoice_date.desc(), Invoice.id.desc()]

    def list_filtered(self, company_id: int, customer_id: int | None = None, status: InvoiceStatus | None = None) -> list[Invoice]:
        query = select(Invoice).where(Invoice.company_id == company_id)
        if customer_id is not None:
            query = query.where(Invoice.customer_id == customer_id)
        if status is not None:
            query = query.where(Invoice.status == status)
        query = query.order_by(*self.order_by_columns())
        return list(self.session.scalars(query))

    def get_by_public_token(self, token: str) -> Invoice | None:
        """Used by the customer link - deliberately not limited to one company."""
        query = select(Invoice).where(Invoice.public_token == token)
        return self.session.scalar(query)

    def list_unpaid(self, company_id: int) -> list[Invoice]:
        query = select(Invoice).where(
            Invoice.company_id == company_id,
            Invoice.status.in_([InvoiceStatus.OPEN, InvoiceStatus.PARTIALLY_PAID]),
        )
        return list(self.session.scalars(query))

    def open_balance_by_customer(self, company_id: int) -> dict[int, Decimal]:
        """Return {customer_id: amount still owed} for every customer with unpaid invoices."""
        query = (
            select(Invoice.customer_id, func.sum(Invoice.total - Invoice.amount_paid))
            .where(
                Invoice.company_id == company_id,
                Invoice.status != InvoiceStatus.VOID,
            )
            .group_by(Invoice.customer_id)
        )
        balances = {}
        for customer_id, balance in self.session.execute(query):
            balances[customer_id] = Decimal(balance or 0)
        return balances
