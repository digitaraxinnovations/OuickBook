from sqlalchemy import select

from app.models import HealthDismissal
from app.repositories.base import BaseRepository


class HealthDismissalRepository(BaseRepository):
    model = HealthDismissal

    def get_by_key(self, company_id: int, key: str) -> HealthDismissal | None:
        query = select(HealthDismissal).where(HealthDismissal.company_id == company_id, HealthDismissal.finding_key == key)
        return self.session.scalar(query)

    def delete(self, row: HealthDismissal) -> None:
        self.session.delete(row)
