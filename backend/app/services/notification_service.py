"""
Notifications: things that need attention, worked out when asked (nothing to
store or mark as read - fix the cause and the notification goes away).
"""

from datetime import date, timedelta

from sqlalchemy import func, select

from app.models import BankTransaction, Invoice, Product, PurchaseDocument, PaySchedule
from app.models.enums import BankTransactionStatus, InvoiceStatus, ProductType, PurchaseDocStatus, PurchaseDocType
from app.schemas.platform import Notification
from app.services.tax_service import TaxService

BILLS_DUE_SOON_DAYS = 7
PAYDAY_SOON_DAYS = 3


class NotificationService:
    def __init__(self, session, tax_service: TaxService):
        self.session = session
        self.tax_service = tax_service

    def count(self, query) -> int:
        return self.session.scalar(select(func.count()).select_from(query.subquery())) or 0

    def list(self, company_id: int, today: date | None = None) -> list[Notification]:
        today = today or date.today()
        notes = []

        overdue = self.count(
            select(Invoice.id).where(
                Invoice.company_id == company_id,
                Invoice.status.in_([InvoiceStatus.OPEN, InvoiceStatus.PARTIALLY_PAID]),
                Invoice.due_date < today,
            )
        )
        if overdue:
            notes.append(Notification(kind="overdue_invoices", level="warning", message=f"{overdue} invoice(s) are overdue.", href="/reports/collections"))

        bills = self.count(
            select(PurchaseDocument.id).where(
                PurchaseDocument.company_id == company_id,
                PurchaseDocument.doc_type == PurchaseDocType.BILL,
                PurchaseDocument.status.in_([PurchaseDocStatus.OPEN, PurchaseDocStatus.PARTIALLY_PAID]),
                PurchaseDocument.due_date <= today + timedelta(days=BILLS_DUE_SOON_DAYS),
            )
        )
        if bills:
            notes.append(Notification(kind="bills_due", level="warning", message=f"{bills} bill(s) are due within {BILLS_DUE_SOON_DAYS} days or overdue.", href="/expenses/pay-bills"))

        to_review = self.count(
            select(BankTransaction.id).where(BankTransaction.company_id == company_id, BankTransaction.status == BankTransactionStatus.FOR_REVIEW)
        )
        if to_review:
            notes.append(Notification(kind="bank_review", level="info", message=f"{to_review} bank transaction(s) are waiting for review.", href="/banking"))

        low_stock = self.count(
            select(Product.id).where(
                Product.company_id == company_id,
                Product.product_type == ProductType.INVENTORY,
                Product.is_active.is_(True),
                Product.reorder_point.is_not(None),
                Product.quantity_on_hand <= Product.reorder_point,
            )
        )
        if low_stock:
            notes.append(Notification(kind="low_stock", level="info", message=f"{low_stock} item(s) are low on stock.", href="/sales/products"))

        paydays = self.session.scalars(
            select(PaySchedule).where(
                PaySchedule.company_id == company_id,
                PaySchedule.is_active.is_(True),
                PaySchedule.next_pay_date <= today + timedelta(days=PAYDAY_SOON_DAYS),
            )
        ).all()
        for schedule in paydays:
            notes.append(
                Notification(kind="payroll_due", level="warning", message=f"Run payroll for {schedule.name} (pay day {schedule.next_pay_date:%b %d}).", href="/payroll/runs?new=1")
            )

        due_periods = [period for period in self.tax_service.periods(company_id, today=today) if period.status == "DUE"]
        if due_periods:
            notes.append(Notification(kind="sales_tax_due", level="warning", message=f"{len(due_periods)} sales tax period(s) are due.", href="/taxes"))
        return notes
