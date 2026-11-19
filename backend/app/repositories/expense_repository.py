from app.models import Expense
from app.repositories.base import BaseRepository


class ExpenseRepository(BaseRepository):
    model = Expense

    def order_by_columns(self) -> list:
        return [Expense.expense_date.desc(), Expense.id.desc()]
