from sqlalchemy import select

from app.models import Payment
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository):
    model = Payment

    def order_by_columns(self) -> list:
        return [Payment.payment_date.desc(), Payment.id.desc()]

    def list_for_invoice(self, company_id: int, invoice_id: int) -> list[Payment]:
        query = (
            select(Payment)
            .where(Payment.company_id == company_id, Payment.invoice_id == invoice_id)
            .order_by(Payment.payment_date, Payment.id)
        )
        return list(self.session.scalars(query))
