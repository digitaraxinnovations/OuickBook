"""
Repositories for Phase 2 sales tables.
"""

from decimal import Decimal

from sqlalchemy import func, select

from app.models import (
    BankDeposit,
    EmailLog,
    Payment,
    PaymentApplication,
    PaymentTerm,
    SalesDocument,
)
from app.models.enums import SalesDocStatus, SalesDocType
from app.repositories.base import BaseRepository


class PaymentTermRepository(BaseRepository):
    model = PaymentTerm

    def order_by_columns(self) -> list:
        return [PaymentTerm.due_days, PaymentTerm.name]

    def get_by_name(self, company_id: int, name: str) -> PaymentTerm | None:
        query = select(PaymentTerm).where(PaymentTerm.company_id == company_id, PaymentTerm.name == name)
        return self.session.scalar(query)


class SalesDocumentRepository(BaseRepository):
    model = SalesDocument

    def order_by_columns(self) -> list:
        return [SalesDocument.doc_date.desc(), SalesDocument.id.desc()]

    def list_filtered(
        self,
        company_id: int,
        doc_type: SalesDocType | None = None,
        customer_id: int | None = None,
        status: SalesDocStatus | None = None,
    ) -> list[SalesDocument]:
        query = select(SalesDocument).where(SalesDocument.company_id == company_id)
        if doc_type is not None:
            query = query.where(SalesDocument.doc_type == doc_type)
        if customer_id is not None:
            query = query.where(SalesDocument.customer_id == customer_id)
        if status is not None:
            query = query.where(SalesDocument.status == status)
        query = query.order_by(*self.order_by_columns())
        return list(self.session.scalars(query))

    def open_credit_by_customer(self, company_id: int) -> dict[int, Decimal]:
        """Credit memo money not yet used, per customer."""
        query = (
            select(SalesDocument.customer_id, func.sum(SalesDocument.total - SalesDocument.amount_applied))
            .where(
                SalesDocument.company_id == company_id,
                SalesDocument.doc_type == SalesDocType.CREDIT_MEMO,
                SalesDocument.status == SalesDocStatus.OPEN,
            )
            .group_by(SalesDocument.customer_id)
        )
        result = {}
        for customer_id, amount in self.session.execute(query):
            result[customer_id] = Decimal(amount or 0)
        return result

    def list_undeposited_receipts(self, company_id: int, undeposited_account_id: int) -> list[SalesDocument]:
        query = select(SalesDocument).where(
            SalesDocument.company_id == company_id,
            SalesDocument.doc_type == SalesDocType.SALES_RECEIPT,
            SalesDocument.status == SalesDocStatus.PAID,
            SalesDocument.money_account_id == undeposited_account_id,
            SalesDocument.deposit_id.is_(None),
        )
        return list(self.session.scalars(query.order_by(SalesDocument.doc_date)))


class PaymentRepository(BaseRepository):
    model = Payment

    def order_by_columns(self) -> list:
        return [Payment.payment_date.desc(), Payment.id.desc()]

    def list_for_customer(self, company_id: int, customer_id: int) -> list[Payment]:
        query = select(Payment).where(Payment.company_id == company_id, Payment.customer_id == customer_id)
        return list(self.session.scalars(query.order_by(Payment.payment_date, Payment.id)))

    def applications_for_invoice(self, company_id: int, invoice_id: int) -> list[PaymentApplication]:
        query = (
            select(PaymentApplication)
            .join(Payment, Payment.id == PaymentApplication.payment_id)
            .where(Payment.company_id == company_id, PaymentApplication.invoice_id == invoice_id)
            .order_by(Payment.payment_date, Payment.id)
        )
        return list(self.session.scalars(query))

    def unapplied_by_customer(self, company_id: int) -> dict[int, Decimal]:
        query = (
            select(Payment.customer_id, func.sum(Payment.unapplied_amount))
            .where(Payment.company_id == company_id, Payment.unapplied_amount > 0)
            .group_by(Payment.customer_id)
        )
        result = {}
        for customer_id, amount in self.session.execute(query):
            result[customer_id] = Decimal(amount or 0)
        return result

    def list_undeposited(self, company_id: int, undeposited_account_id: int) -> list[Payment]:
        query = select(Payment).where(
            Payment.company_id == company_id,
            Payment.deposit_account_id == undeposited_account_id,
            Payment.deposit_id.is_(None),
            Payment.amount > 0,
        )
        return list(self.session.scalars(query.order_by(Payment.payment_date)))


class DepositRepository(BaseRepository):
    model = BankDeposit

    def order_by_columns(self) -> list:
        return [BankDeposit.deposit_date.desc(), BankDeposit.id.desc()]


class EmailLogRepository(BaseRepository):
    model = EmailLog

    def order_by_columns(self) -> list:
        return [EmailLog.sent_at.desc(), EmailLog.id.desc()]
