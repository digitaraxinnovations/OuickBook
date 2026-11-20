"""
Mileage log. Business miles x the company's mileage rate = the deduction.
Trips are not posted to the ledger; the deduction is a tax figure.
"""

from datetime import date
from decimal import Decimal

from app.core.money import to_money
from app.models import Trip
from app.models.enums import TripPurpose
from app.repositories.company_repository import CompanyRepository
from app.repositories.purchase_repositories import TripRepository
from app.schemas.purchase import MileageRateUpdate, MileageSummary, TripWrite
from app.services.base import CrudService


class MileageService(CrudService):
    model = Trip
    item_name = "Trip"

    def __init__(self, session, repository: TripRepository, company_repository: CompanyRepository):
        super().__init__(session, repository)
        self.company_repository = company_repository

    def list_year(self, company_id: int, year: int) -> list[Trip]:
        return self.repository.list_between(company_id, date(year, 1, 1), date(year, 12, 31))

    def delete(self, company_id: int, trip_id: int) -> None:
        trip = self.get(company_id, trip_id)
        self.session.delete(trip)
        self.commit()

    def summary(self, company_id: int, year: int) -> MileageSummary:
        business = Decimal("0")
        personal = Decimal("0")
        for trip in self.list_year(company_id, year):
            if trip.purpose == TripPurpose.BUSINESS:
                business += trip.miles
            else:
                personal += trip.miles
        rate = self.company_repository.get(company_id).mileage_rate
        return MileageSummary(
            year=year,
            business_miles=business,
            personal_miles=personal,
            rate=rate,
            deduction=to_money(business * rate),
        )

    def set_rate(self, company_id: int, data: MileageRateUpdate) -> None:
        company = self.company_repository.get(company_id)
        company.mileage_rate = data.mileage_rate
        self.commit()

    def apply_changes(self, company_id: int, record: Trip, data: TripWrite) -> None:
        record.trip_date = data.trip_date
        record.vehicle = data.vehicle
        record.start_location = data.start_location
        record.end_location = data.end_location
        record.miles = data.miles
        record.purpose = data.purpose
        record.notes = data.notes
