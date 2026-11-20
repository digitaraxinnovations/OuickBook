from sqlalchemy import update

from app.core.exceptions import BusinessRuleError
from app.models import BankRule, BankTransaction
from app.repositories.account_repository import AccountRepository
from app.repositories.banking_repositories import BankRuleRepository
from app.repositories.contact_repository import VendorRepository
from app.schemas.banking import BankRuleWrite
from app.services.base import CrudService


class BankRuleService(CrudService):
    model = BankRule
    item_name = "Bank rule"

    def __init__(self, session, repository: BankRuleRepository, account_repository: AccountRepository, vendor_repository: VendorRepository):
        super().__init__(session, repository)
        self.account_repository = account_repository
        self.vendor_repository = vendor_repository

    def validate(self, company_id: int, data: BankRuleWrite) -> None:
        if self.account_repository.get(company_id, data.category_account_id) is None:
            raise BusinessRuleError("Choose the category the rule should use.")
        if data.account_id is not None and self.account_repository.get(company_id, data.account_id) is None:
            raise BusinessRuleError("That bank account does not exist.")
        if data.vendor_id is not None and self.vendor_repository.get(company_id, data.vendor_id) is None:
            raise BusinessRuleError("That vendor does not exist.")

    def apply_changes(self, company_id: int, record: BankRule, data: BankRuleWrite) -> None:
        record.name = data.name
        record.priority = data.priority
        record.account_id = data.account_id
        record.direction = data.direction
        record.match_type = data.match_type
        record.conditions = [condition.model_dump() for condition in data.conditions]
        record.category_account_id = data.category_account_id
        record.vendor_id = data.vendor_id
        record.auto_add = data.auto_add
        record.is_active = data.is_active

    def delete(self, company_id: int, rule_id: int) -> None:
        rule = self.get(company_id, rule_id)
        # Bank lines keep their suggestion, they just no longer point at the rule.
        self.session.execute(update(BankTransaction).where(BankTransaction.rule_id == rule.id).values(rule_id=None))
        self.session.delete(rule)
        self.commit()
