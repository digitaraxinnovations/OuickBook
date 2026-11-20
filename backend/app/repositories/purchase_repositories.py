"""
Repositories for Phase 3 (vendor side) tables.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.models import Attachment, BillPayment, BillPaymentApplication, Expense, PurchaseDocument, Trip
from app.models.enums import ExpenseKind, PaymentMethod, PurchaseDocStatus, PurchaseDocType
from app.repositories.base import BaseRepository

UNPAID_BILL_STATUSES = (PurchaseDocStatus.OPEN, PurchaseDocStatus.PARTIALLY_PAID)


class PurchaseDocumentRepository(BaseRepository):
    model = PurchaseDocument

    def order_by_columns(self) -> list:
        return [PurchaseDocument.doc_date.desc(), PurchaseDocument.id.desc()]

    def list_filtered(
        self,
        company_id: int,
        doc_type: PurchaseDocType | None = None,
        vendor_id: int | None = None,
        status: PurchaseDocStatus | None = None,
    ) -> list[PurchaseDocument]:
        query = select(PurchaseDocument).where(PurchaseDocument.company_id == company_id)
        if doc_type is not None:
            query = query.where(PurchaseDocument.doc_type == doc_type)
        if vendor_id is not None:
            query = query.where(PurchaseDocument.vendor_id == vendor_id)
        if status is not None:
            query = query.where(PurchaseDocument.status == status)
        return list(self.session.scalars(query.order_by(*self.order_by_columns())))

    def list_unpaid_bills(self, company_id: int, vendor_id: int | None = None) -> list[PurchaseDocument]:
        query = select(PurchaseDocument).where(
            PurchaseDocument.company_id == company_id,
            PurchaseDocument.doc_type == PurchaseDocType.BILL,
            PurchaseDocument.status.in_(UNPAID_BILL_STATUSES),
        )
        if vendor_id is not None:
            query = query.where(PurchaseDocument.vendor_id == vendor_id)
        return list(self.session.scalars(query.order_by(PurchaseDocument.due_date, PurchaseDocument.id)))

    def open_balance_by_vendor(self, company_id: int) -> dict[int, Decimal]:
        """Unpaid bills minus unused vendor credits, per vendor."""
        query = (
            select(PurchaseDocument.doc_type, PurchaseDocument.vendor_id, func.sum(PurchaseDocument.total - PurchaseDocument.amount_applied))
            .where(
                PurchaseDocument.company_id == company_id,
                PurchaseDocument.doc_type.in_([PurchaseDocType.BILL, PurchaseDocType.VENDOR_CREDIT]),
                PurchaseDocument.status.in_([PurchaseDocStatus.OPEN, PurchaseDocStatus.PARTIALLY_PAID]),
            )
            .group_by(PurchaseDocument.doc_type, PurchaseDocument.vendor_id)
        )
        balances = {}
        for doc_type, vendor_id, amount in self.session.execute(query):
            amount = Decimal(amount or 0)
            if doc_type == PurchaseDocType.VENDOR_CREDIT:
                amount = -amount
            balances[vendor_id] = balances.get(vendor_id, Decimal("0.00")) + amount
        return balances


class BillPaymentRepository(BaseRepository):
    model = BillPayment

    def order_by_columns(self) -> list:
        return [BillPayment.payment_date.desc(), BillPayment.id.desc()]

    def applications_for_bill(self, company_id: int, bill_id: int) -> list[BillPaymentApplication]:
        query = (
            select(BillPaymentApplication)
            .join(BillPayment, BillPayment.id == BillPaymentApplication.payment_id)
            .where(BillPayment.company_id == company_id, BillPaymentApplication.bill_id == bill_id)
            .order_by(BillPayment.payment_date)
        )
        return list(self.session.scalars(query))

    def list_checks_to_print(self, company_id: int) -> list[BillPayment]:
        query = select(BillPayment).where(
            BillPayment.company_id == company_id,
            BillPayment.payment_method == PaymentMethod.CHECK,
            BillPayment.print_later.is_(True),
        )
        return list(self.session.scalars(query.order_by(BillPayment.payment_date)))

    def list_between(self, company_id: int, start_date: date, end_date: date) -> list[BillPayment]:
        query = select(BillPayment).where(
            BillPayment.company_id == company_id,
            BillPayment.payment_date >= start_date,
            BillPayment.payment_date <= end_date,
        )
        return list(self.session.scalars(query))


class ExpenseQueries:
    """Extra expense queries used by checks and the 1099 report."""

    def __init__(self, session):
        self.session = session

    def list_checks_to_print(self, company_id: int) -> list[Expense]:
        query = select(Expense).where(
            Expense.company_id == company_id,
            Expense.kind == ExpenseKind.CHECK,
            Expense.print_later.is_(True),
            Expense.is_void.is_(False),
        )
        return list(self.session.scalars(query.order_by(Expense.expense_date)))

    def list_between(self, company_id: int, start_date: date, end_date: date) -> list[Expense]:
        query = select(Expense).where(
            Expense.company_id == company_id,
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date,
            Expense.is_void.is_(False),
        )
        return list(self.session.scalars(query))


class AttachmentRepository(BaseRepository):
    model = Attachment

    def order_by_columns(self) -> list:
        return [Attachment.created_at.desc(), Attachment.id.desc()]

    def list_for(self, company_id: int, entity_type: str, entity_id: int | None) -> list[Attachment]:
        query = select(Attachment).where(Attachment.company_id == company_id, Attachment.entity_type == entity_type)
        if entity_id is None:
            query = query.where(Attachment.entity_id.is_(None))
        else:
            query = query.where(Attachment.entity_id == entity_id)
        return list(self.session.scalars(query.order_by(*self.order_by_columns())))


class TripRepository(BaseRepository):
    model = Trip

    def order_by_columns(self) -> list:
        return [Trip.trip_date.desc(), Trip.id.desc()]

    def list_between(self, company_id: int, start_date: date, end_date: date) -> list[Trip]:
        query = select(Trip).where(Trip.company_id == company_id, Trip.trip_date >= start_date, Trip.trip_date <= end_date)
        return list(self.session.scalars(query.order_by(*self.order_by_columns())))
