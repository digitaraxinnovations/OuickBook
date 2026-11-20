from datetime import date
from decimal import Decimal

from sqlalchemy import func, select, update

from app.models import SalesTaxAdjustment, SalesTaxLine, SalesTaxPayment, TaxAgency, TaxCode, TaxRate
from app.repositories.base import BaseRepository


class TaxAgencyRepository(BaseRepository):
    model = TaxAgency

    def order_by_columns(self) -> list:
        return [TaxAgency.name]

    def get_by_name(self, company_id: int, name: str) -> TaxAgency | None:
        query = select(TaxAgency).where(TaxAgency.company_id == company_id, func.lower(TaxAgency.name) == name.lower())
        return self.session.scalar(query)


class TaxRateRepository(BaseRepository):
    model = TaxRate

    def order_by_columns(self) -> list:
        return [TaxRate.name]


class TaxCodeRepository(BaseRepository):
    model = TaxCode

    def order_by_columns(self) -> list:
        return [TaxCode.name]

    def get_by_name(self, company_id: int, name: str) -> TaxCode | None:
        query = select(TaxCode).where(TaxCode.company_id == company_id, func.lower(TaxCode.name) == name.lower())
        return self.session.scalar(query)


class SalesTaxLineRepository(BaseRepository):
    model = SalesTaxLine

    def mark_void(self, company_id: int, source_type: str, source_id: int) -> None:
        statement = (
            update(SalesTaxLine)
            .where(
                SalesTaxLine.company_id == company_id,
                SalesTaxLine.source_type == source_type,
                SalesTaxLine.source_id == source_id,
            )
            .values(is_void=True)
        )
        self.session.execute(statement)

    def rate_was_used(self, company_id: int, rate_id: int) -> bool:
        query = select(SalesTaxLine.id).where(SalesTaxLine.company_id == company_id, SalesTaxLine.tax_rate_id == rate_id)
        return self.session.scalars(query).first() is not None

    def list_between(self, company_id: int, start: date, end: date, agency_id: int | None = None) -> list[SalesTaxLine]:
        query = select(SalesTaxLine).where(
            SalesTaxLine.company_id == company_id,
            SalesTaxLine.is_void.is_(False),
            SalesTaxLine.tax_date >= start,
            SalesTaxLine.tax_date <= end,
        )
        if agency_id is not None:
            query = query.where(SalesTaxLine.agency_id == agency_id)
        return list(self.session.scalars(query))

    def tax_total(self, company_id: int, agency_id: int, start: date, end: date) -> Decimal:
        query = select(func.coalesce(func.sum(SalesTaxLine.tax_amount), 0)).where(
            SalesTaxLine.company_id == company_id,
            SalesTaxLine.agency_id == agency_id,
            SalesTaxLine.is_void.is_(False),
            SalesTaxLine.tax_date >= start,
            SalesTaxLine.tax_date <= end,
        )
        return Decimal(self.session.scalar(query))


class SalesTaxPaymentRepository(BaseRepository):
    model = SalesTaxPayment

    def order_by_columns(self) -> list:
        return [SalesTaxPayment.payment_date.desc(), SalesTaxPayment.id.desc()]

    def list_for_agency(self, company_id: int, agency_id: int | None) -> list[SalesTaxPayment]:
        query = select(SalesTaxPayment).where(SalesTaxPayment.company_id == company_id)
        if agency_id is not None:
            query = query.where(SalesTaxPayment.agency_id == agency_id)
        return list(self.session.scalars(query.order_by(*self.order_by_columns())))

    def total_paid_between(self, company_id: int, agency_id: int, start: date, end: date) -> Decimal:
        """Payments made on dates inside this range (used by the liability report)."""
        query = select(func.coalesce(func.sum(SalesTaxPayment.amount), 0)).where(
            SalesTaxPayment.company_id == company_id,
            SalesTaxPayment.agency_id == agency_id,
            SalesTaxPayment.payment_date >= start,
            SalesTaxPayment.payment_date <= end,
        )
        return Decimal(self.session.scalar(query))

    def total_for_period(self, company_id: int, agency_id: int, start: date, end: date) -> Decimal:
        """Payments recorded against this filing period."""
        query = select(func.coalesce(func.sum(SalesTaxPayment.amount), 0)).where(
            SalesTaxPayment.company_id == company_id,
            SalesTaxPayment.agency_id == agency_id,
            SalesTaxPayment.period_start == start,
            SalesTaxPayment.period_end == end,
        )
        return Decimal(self.session.scalar(query))


class SalesTaxAdjustmentRepository(BaseRepository):
    model = SalesTaxAdjustment

    def order_by_columns(self) -> list:
        return [SalesTaxAdjustment.adjustment_date.desc(), SalesTaxAdjustment.id.desc()]

    def list_for_agency(self, company_id: int, agency_id: int | None) -> list[SalesTaxAdjustment]:
        query = select(SalesTaxAdjustment).where(SalesTaxAdjustment.company_id == company_id)
        if agency_id is not None:
            query = query.where(SalesTaxAdjustment.agency_id == agency_id)
        return list(self.session.scalars(query.order_by(*self.order_by_columns())))

    def total_between(self, company_id: int, agency_id: int, start: date, end: date) -> Decimal:
        query = select(func.coalesce(func.sum(SalesTaxAdjustment.amount), 0)).where(
            SalesTaxAdjustment.company_id == company_id,
            SalesTaxAdjustment.agency_id == agency_id,
            SalesTaxAdjustment.adjustment_date >= start,
            SalesTaxAdjustment.adjustment_date <= end,
        )
        return Decimal(self.session.scalar(query))
