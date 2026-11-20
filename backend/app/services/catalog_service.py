"""
Product categories and price rules.

Price rules raise or lower an item's sales price by a percentage. When more
than one rule fits, the most specific one wins:
    an item rule  >  a category rule  >  a rule for all items
and a rule for one customer beats a rule for everyone.
"""

from datetime import date
from decimal import Decimal

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.money import to_money
from app.models import PriceRule, Product, ProductCategory
from app.repositories.contact_repository import CustomerRepository
from app.repositories.inventory_repositories import PriceRuleRepository, ProductCategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product import CategoryWrite, PriceRuleWrite, ProductPrice
from app.services.base import BaseService


class CatalogService(BaseService):
    def __init__(
        self,
        session,
        category_repository: ProductCategoryRepository,
        rule_repository: PriceRuleRepository,
        product_repository: ProductRepository,
        customer_repository: CustomerRepository,
    ):
        super().__init__(session)
        self.category_repository = category_repository
        self.rule_repository = rule_repository
        self.product_repository = product_repository
        self.customer_repository = customer_repository

    # ---------- categories ----------

    def list_categories(self, company_id: int) -> list[ProductCategory]:
        return self.category_repository.list_all(company_id)

    def save_category(self, company_id: int, data: CategoryWrite, category_id: int | None = None) -> ProductCategory:
        category = self.save_category_without_commit(company_id, data, category_id)
        self.commit()
        return category

    def save_category_without_commit(self, company_id: int, data: CategoryWrite, category_id: int | None = None) -> ProductCategory:
        existing = self.category_repository.get_by_name(company_id, data.name)
        if existing is not None and existing.id != category_id:
            raise ConflictError("A category with this name already exists.")

        if category_id is None:
            category = ProductCategory(company_id=company_id)
        else:
            category = self.category_repository.get(company_id, category_id)
            if category is None:
                raise NotFoundError("Category not found.")

        if data.parent_id is not None:
            self.check_parent(company_id, category_id, data.parent_id)
        category.name = data.name
        category.parent_id = data.parent_id
        if category_id is None:
            self.category_repository.add(category)
        return category

    def check_parent(self, company_id: int, category_id: int | None, parent_id: int) -> None:
        """The parent must exist and must not be the category itself or one of its sub-categories."""
        parent = self.category_repository.get(company_id, parent_id)
        if parent is None:
            raise BusinessRuleError("The parent category does not exist.")
        while parent is not None:
            if parent.id == category_id:
                raise BusinessRuleError("A category cannot be inside itself.")
            if parent.parent_id is None:
                break
            parent = self.category_repository.get(company_id, parent.parent_id)

    # ---------- price rules ----------

    def list_rules(self, company_id: int) -> list[PriceRule]:
        return self.rule_repository.list_all(company_id)

    def save_rule(self, company_id: int, data: PriceRuleWrite, rule_id: int | None = None) -> PriceRule:
        if data.start_date and data.end_date and data.end_date < data.start_date:
            raise BusinessRuleError("The end date cannot be before the start date.")
        if data.product_id is not None and data.category_id is not None:
            raise BusinessRuleError("Choose one item or one category, not both.")
        if data.customer_id is not None and self.customer_repository.get(company_id, data.customer_id) is None:
            raise BusinessRuleError("That customer does not exist.")
        if data.category_id is not None and self.category_repository.get(company_id, data.category_id) is None:
            raise BusinessRuleError("That category does not exist.")
        if data.product_id is not None and self.product_repository.get(company_id, data.product_id) is None:
            raise BusinessRuleError("That product does not exist.")

        if rule_id is None:
            rule = PriceRule(company_id=company_id)
        else:
            rule = self.rule_repository.get(company_id, rule_id)
            if rule is None:
                raise NotFoundError("Price rule not found.")
        for field_name, value in data.model_dump().items():
            setattr(rule, field_name, value)
        if rule_id is None:
            self.rule_repository.add(rule)
        self.commit()
        return rule

    def prices(self, company_id: int, customer_id: int | None, on_date: date) -> list[ProductPrice]:
        """Every active item's price for this customer on this date."""
        rules = []
        for rule in self.rule_repository.list_all(company_id, active_only=True):
            if self.rule_applies_on(rule, customer_id, on_date):
                rules.append(rule)

        result = []
        for product in self.product_repository.list_all(company_id, active_only=True):
            best = self.best_rule(rules, product)
            price = product.sales_price
            rule_name = None
            if best is not None:
                price = to_money(product.sales_price * (Decimal("100") + best.adjustment_percent) / Decimal("100"))
                rule_name = best.name
            result.append(ProductPrice(product_id=product.id, price=price, rule_name=rule_name))
        return result

    def rule_applies_on(self, rule: PriceRule, customer_id: int | None, on_date: date) -> bool:
        if rule.customer_id is not None and rule.customer_id != customer_id:
            return False
        if rule.start_date is not None and on_date < rule.start_date:
            return False
        if rule.end_date is not None and on_date > rule.end_date:
            return False
        return True

    def best_rule(self, rules: list[PriceRule], product: Product) -> PriceRule | None:
        best = None
        best_score = -1
        for rule in rules:
            score = self.specificity(rule, product)
            if score > best_score or (score == best_score and score >= 0 and rule.id > best.id):
                best = rule
                best_score = score
        return best

    def specificity(self, rule: PriceRule, product: Product) -> int:
        """How closely a rule fits the item: -1 = does not apply, higher = more specific."""
        if rule.product_id is not None:
            if rule.product_id != product.id:
                return -1
            score = 4
        elif rule.category_id is not None:
            if rule.category_id != product.category_id:
                return -1
            score = 2
        else:
            score = 0
        if rule.customer_id is not None:
            score += 1
        return score
