import base64

from app.core.config import Settings
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import Account, Company, PaymentTerm
from app.repositories.account_repository import AccountRepository
from app.repositories.company_repository import CompanyRepository
from app.schemas.auth import CompanyUpdate
from app.schemas.sales_extras import LogoUpload, SalesSettingsUpdate
from app.seed.default_accounts import DEFAULT_ACCOUNTS, DEFAULT_PAYMENT_TERMS
from app.services.base import BaseService


def logo_data_url(company: Company) -> str | None:
    """The logo as a data: URL that can go straight into an <img> tag."""
    if company.logo is None:
        return None
    encoded = base64.b64encode(company.logo).decode("ascii")
    return f"data:{company.logo_mime_type};base64,{encoded}"


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
        """Create a new company with its starting Chart of Accounts and payment terms. Does not commit."""
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

        for template in DEFAULT_PAYMENT_TERMS:
            self.session.add(PaymentTerm(company_id=company.id, name=template["name"], due_days=template["due_days"]))

        return company

    def update(self, company_id: int, data: CompanyUpdate) -> Company:
        company = self.get(company_id)
        company.name = data.name
        company.email = data.email
        company.phone = data.phone
        company.address = data.address
        company.website = data.website
        company.payment_terms_days = data.payment_terms_days
        self.commit()
        return company

    def update_sales_settings(self, company_id: int, data: SalesSettingsUpdate) -> Company:
        company = self.get(company_id)
        company.invoice_template = data.invoice_template
        company.invoice_accent_color = data.invoice_accent_color
        company.invoice_footer = data.invoice_footer
        company.late_fee_enabled = data.late_fee_enabled
        company.late_fee_type = data.late_fee_type
        company.late_fee_amount = data.late_fee_amount
        company.late_fee_grace_days = data.late_fee_grace_days
        company.reminders_enabled = data.reminders_enabled
        company.reminder_days_after_due = data.reminder_days_after_due
        self.commit()
        return company

    def set_logo(self, company_id: int, data: LogoUpload) -> Company:
        try:
            image_bytes = base64.b64decode(data.data_base64, validate=True)
        except ValueError:
            raise BusinessRuleError("The logo file could not be read.")
        if len(image_bytes) > self.settings.max_logo_bytes:
            limit_kb = self.settings.max_logo_bytes // 1000
            raise BusinessRuleError(f"The logo is too large. The limit is {limit_kb} KB.")

        company = self.get(company_id)
        company.logo = image_bytes
        company.logo_mime_type = data.mime_type
        self.commit()
        return company

    def remove_logo(self, company_id: int) -> Company:
        company = self.get(company_id)
        company.logo = None
        company.logo_mime_type = None
        self.commit()
        return company
