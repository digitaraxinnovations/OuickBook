"""
The closing date: once the books are closed through a date (e.g. after
filing taxes), nothing dated on or before it can be posted unless the
closing password is given. The frontend asks for the password when it gets
the BOOKS_CLOSED error and sends it in the X-Closing-Password header.
"""

from datetime import date

from app.core.exceptions import BooksClosedError
from app.core.request_context import typed_closing_password
from app.core.security import PasswordHasher
from app.repositories.company_repository import CompanyRepository


class ClosingDateGuard:
    def __init__(self, company_repository: CompanyRepository, password_hasher: PasswordHasher):
        self.company_repository = company_repository
        self.password_hasher = password_hasher

    def check(self, company_id: int, entry_date: date) -> None:
        company = self.company_repository.get(company_id)
        if company is None or company.closing_date is None or entry_date > company.closing_date:
            return
        typed = typed_closing_password(self.company_repository.session)
        if company.closing_password_hash and typed and self.password_hasher.verify(typed, company.closing_password_hash):
            return
        message = f"The books are closed through {company.closing_date:%b %d, %Y}."
        if company.closing_password_hash:
            message += " Enter the closing password to save this."
        else:
            message += " Change the closing date in Settings to save this."
        raise BooksClosedError(message)
