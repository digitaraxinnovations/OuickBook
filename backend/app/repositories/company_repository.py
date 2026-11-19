from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, User


class CompanyRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, company_id: int) -> Company | None:
        return self.session.get(Company, company_id)

    def add(self, company: Company) -> Company:
        self.session.add(company)
        self.session.flush()
        return company


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        query = select(User).where(User.email == email.lower())
        return self.session.scalar(query)

    def add(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user
