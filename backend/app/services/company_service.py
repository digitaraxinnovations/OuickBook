from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.models import Account, Company
from app.repositories.account_repository import AccountRepository
from app.repositories.company_repository import CompanyRepository
from app.schemas.auth import CompanyUpdate
from app.seed.default_accounts import DEFAULT_ACCOUNTS
from app.services.base import BaseService


class CompanyService(BaseService):
    def __init__(self, session, company_repository: CompanyRepository, account_repository: AccountRepository, settings: Settings):
        super().__init__(session)
        self.company_repository = company_repository
        self.account_repository = account_repository
        self.settings = settings

    def get(self, company_id: int) -> Company:
        company = self.company_repository.get(company_id)
        if company is None:
            raise NotFoundError("Company not found.")
        return company

    def create_with_default_accounts(self, name: str) -> Company:
        """Create a new company and its starting Chart of Accounts. Does not commit."""
        company = Company(
            name=name,
            currency=self.settings.default_currency,
            next_invoice_number=self.settings.invoice_number_start,
            payment_terms_days=self.settings.default_payment_terms_days,
        )
        self.company_repository.add(company)

        for template in DEFAULT_ACCOUNTS:
            account = Account(
                company_id=company.id,
                code=template["code"],
                name=template["name"],
                account_type=template["type"],
                detail_type=template["detail"],
                system_key=template["key"],
            )
            self.account_repository.add(account)

        return company

    def update(self, company_id: int, data: CompanyUpdate) -> Company:
        company = self.get(company_id)
        company.name = data.name
        company.email = data.email
        company.phone = data.phone
        company.address = data.address
        company.payment_terms_days = data.payment_terms_days
        self.commit()
        return company
