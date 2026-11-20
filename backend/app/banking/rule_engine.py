"""
Decides which bank rule (if any) fits a bank transaction.
"""

from decimal import Decimal, InvalidOperation

from app.models import BankRule, BankTransaction
from app.models.enums import BankRuleDirection


def condition_matches(condition: dict, transaction: BankTransaction) -> bool:
    operator = condition["operator"]
    value = condition["value"]

    if condition["field"] == "amount":
        try:
            target = Decimal(value)
        except InvalidOperation:
            return False
        amount = abs(transaction.amount)
        if operator == "equals":
            return amount == target
        if operator == "greater_than":
            return amount > target
        if operator == "less_than":
            return amount < target
        return False

    text = transaction.description.lower()
    value = value.lower()
    if operator == "contains":
        return value in text
    if operator == "not_contains":
        return value not in text
    if operator == "equals":
        return text == value
    if operator == "starts_with":
        return text.startswith(value)
    if operator == "ends_with":
        return text.endswith(value)
    return False


def rule_matches(rule: BankRule, transaction: BankTransaction) -> bool:
    if not rule.is_active:
        return False
    if rule.account_id is not None and rule.account_id != transaction.account_id:
        return False
    if rule.direction == BankRuleDirection.MONEY_IN and transaction.amount < 0:
        return False
    if rule.direction == BankRuleDirection.MONEY_OUT and transaction.amount > 0:
        return False

    results = []
    for condition in rule.conditions:
        results.append(condition_matches(condition, transaction))
    if rule.match_type == "ANY":
        return any(results)
    return all(results)


def first_matching_rule(rules: list[BankRule], transaction: BankTransaction) -> BankRule | None:
    """`rules` must already be sorted by priority."""
    for rule in rules:
        if rule_matches(rule, transaction):
            return rule
    return None
