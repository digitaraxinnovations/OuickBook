"""
Base classes for services.

A service holds the business rules for one area (invoices, expenses...).
It uses repositories to read and write data and decides when to commit.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError


class BaseService:
    def __init__(self, session: Session):
        self.session = session

    def commit(self) -> None:
        self.session.commit()


class CrudService(BaseService):
    """
    Create / read / update for simple lists (customers, vendors, products).

    Subclasses set `model` and `item_name`, and can override:
    - validate()       to add business rules
    - apply_changes()  to control how request data is copied onto the record
    """

    model = None
    item_name = "Record"

    def __init__(self, session: Session, repository):
        super().__init__(session)
        self.repository = repository

    def list(self, company_id: int, active_only: bool = False) -> list:
        return self.repository.list_all(company_id, active_only)

    def get(self, company_id: int, record_id: int):
        record = self.repository.get(company_id, record_id)
        if record is None:
            raise NotFoundError(f"{self.item_name} not found.")
        return record

    def create(self, company_id: int, data):
        record = self.create_record(company_id, data)
        self.commit()
        return record

    def create_record(self, company_id: int, data):
        """Check, build and save a new record without committing."""
        self.validate(company_id, data)
        record = self.model(company_id=company_id)
        self.apply_changes(company_id, record, data)
        self.repository.add(record)
        return record

    def update(self, company_id: int, record_id: int, data):
        record = self.get(company_id, record_id)
        self.validate(company_id, data)
        self.apply_changes(company_id, record, data)
        self.commit()
        return record

    # ----- hooks for subclasses -----

    def validate(self, company_id: int, data) -> None:
        """Raise an AppError if the data breaks a business rule."""

    def apply_changes(self, company_id: int, record, data) -> None:
        """Copy every field from the request onto the database record."""
        for field_name, value in data.model_dump().items():
            setattr(record, field_name, value)
