"""
Print checks: checks and bill payments saved with "print later" get their
check numbers here and are printed together.
"""

from app.core.exceptions import BusinessRuleError
from app.documents.check_pdf import CheckData, CheckPdfBuilder
from app.models import BillPayment, Expense
from app.repositories.account_repository import AccountRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.purchase_repositories import BillPaymentRepository, ExpenseQueries
from app.schemas.purchase import CheckToPrint, NextCheckNumber, PrintChecksRequest
from app.services.base import BaseService
from app.services.check_numbers import CheckNumberService
from app.services.customer_documents_service import PdfFile


class CheckPrintingService(BaseService):
    def __init__(
        self,
        session,
        expense_repository: ExpenseRepository,
        expense_queries: ExpenseQueries,
        bill_payment_repository: BillPaymentRepository,
        account_repository: AccountRepository,
        company_repository: CompanyRepository,
        check_numbers: CheckNumberService,
    ):
        super().__init__(session)
        self.expense_repository = expense_repository
        self.expense_queries = expense_queries
        self.bill_payment_repository = bill_payment_repository
        self.account_repository = account_repository
        self.company_repository = company_repository
        self.check_numbers = check_numbers

    def list_to_print(self, company_id: int) -> list[CheckToPrint]:
        result = []
        for expense in self.expense_queries.list_checks_to_print(company_id):
            result.append(
                CheckToPrint(
                    source_type="EXPENSE",
                    source_id=expense.id,
                    check_date=expense.expense_date,
                    payee=expense.vendor.display_name if expense.vendor else "(no payee)",
                    bank_account=expense.payment_account,
                    amount=expense.total,
                )
            )
        for payment in self.bill_payment_repository.list_checks_to_print(company_id):
            result.append(
                CheckToPrint(
                    source_type="BILL_PAYMENT",
                    source_id=payment.id,
                    check_date=payment.payment_date,
                    payee=payment.vendor.display_name,
                    bank_account=payment.payment_account,
                    amount=payment.amount,
                )
            )
        result.sort(key=lambda item: item.check_date)
        return result

    def next_number(self, company_id: int, bank_account_id: int) -> NextCheckNumber:
        return NextCheckNumber(
            bank_account_id=bank_account_id,
            next_check_number=self.check_numbers.peek(company_id, bank_account_id),
        )

    def print_checks(self, company_id: int, data: PrintChecksRequest) -> PdfFile:
        """Number the chosen checks in order, mark them printed and return the PDF."""
        bank = self.account_repository.get(company_id, data.bank_account_id)
        if bank is None:
            raise BusinessRuleError("Choose the bank account the checks are drawn on.")

        checks = []
        number = data.first_check_number
        for item in data.items:
            record = self.find_record(company_id, item.source_type, item.source_id)
            if record.payment_account_id != bank.id:
                raise BusinessRuleError("All checks printed together must be from the same bank account.")
            record.check_number = str(number)
            record.print_later = False
            checks.append(self.check_data(record, bank.name))
            number += 1

        self.check_numbers.move_past(company_id, bank.id, number - 1)
        company = self.company_repository.get(company_id)
        content = CheckPdfBuilder(company).build(checks)
        self.commit()
        return PdfFile(f"Checks-{data.first_check_number}-{number - 1}.pdf", content)

    def reprint(self, company_id: int, source_type: str, source_id: int) -> PdfFile:
        """Print one check again with its existing number."""
        record = self.find_record(company_id, source_type, source_id, must_be_waiting=False)
        if not record.check_number:
            raise BusinessRuleError("This check has no number yet. Use Print checks.")
        company = self.company_repository.get(company_id)
        content = CheckPdfBuilder(company).build([self.check_data(record, record.payment_account.name)])
        return PdfFile(f"Check-{record.check_number}.pdf", content)

    def find_record(self, company_id: int, source_type: str, source_id: int, must_be_waiting: bool = True):
        if source_type == "EXPENSE":
            record = self.expense_repository.get(company_id, source_id)
        else:
            record = self.bill_payment_repository.get(company_id, source_id)
        if record is None:
            raise BusinessRuleError(f"Check {source_type.lower()} #{source_id} not found.")
        if must_be_waiting and not record.print_later:
            raise BusinessRuleError(f"Check {source_type.lower()} #{source_id} is not waiting to be printed.")
        return record

    def check_data(self, record, bank_name: str) -> CheckData:
        if isinstance(record, Expense):
            payee = record.vendor.display_name if record.vendor else ""
            check = CheckData(record.check_number, record.expense_date, payee, record.total, record.memo or "", bank_name)
            for line in record.lines:
                check.stub_lines.append((line.description or line.account.name, line.amount))
            return check

        payment: BillPayment = record
        check = CheckData(payment.check_number, payment.payment_date, payment.vendor.display_name, payment.amount, payment.memo or "", bank_name)
        for application in payment.applications:
            label = "Bill " + (application.bill.doc_number or "#" + str(application.bill.id))
            check.stub_lines.append((label, application.amount))
        for credit in payment.credits_used:
            check.stub_lines.append(("Vendor credit used", -credit.amount))
        return check
