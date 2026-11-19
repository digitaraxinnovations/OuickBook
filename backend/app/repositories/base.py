"""
Shared data-access code.

A repository only talks to the database. It has no business rules -
those live in the services. This keeps both layers small and easy to test.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session


class BaseRepository:
    """
    Common queries for a model that belongs to a company.

    Subclasses set `model` and can override `order_by_columns`.
    """

    model = None

    def __init__(self, session: Session):
        self.session = session

    def order_by_columns(self) -> list:
        return [self.model.id]

    def get(self, company_id: int, record_id: int):
        query = select(self.model).where(
            self.model.id == record_id,
            self.model.company_id == company_id,
        )
        return self.session.scalar(query)

    def list_all(self, company_id: int, active_only: bool = False) -> list:
        query = select(self.model).where(self.model.company_id == company_id)
        if active_only:
            query = query.where(self.model.is_active.is_(True))
        query = query.order_by(*self.order_by_columns())
        return list(self.session.scalars(query))

    def add(self, record):
        self.session.add(record)
        self.session.flush()  # gives the new record its id
        return record
