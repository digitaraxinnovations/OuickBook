"""
Import and export lists and transactions as CSV files (Excel opens them).

    Customers / Vendors:  Name, Company, Email, Phone, Address, Notes
    Accounts:             Number, Name, Type, Detail type, Description, Parent
    Journal entries:      Entry no, Date, Account, Debit, Credit, Description, Memo
                          (rows with the same Entry no make one journal entry)

Imports are all-or-nothing: if any row has a problem nothing is saved and
every problem is listed. Products have their own import (Products page).

Each list is a DataTransfer subclass, so adding a new one means adding one
class to TRANSFERS - nothing else changes.
"""

import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.core.exceptions import AppError, BusinessRuleError, NotFoundError
from app.models.enums import AccountType
from app.repositories.account_repository import AccountRepository
from app.repositories.contact_repository import CustomerRepository, VendorRepository
from app.repositories.journal_repository import JournalRepository
from app.schemas.account import AccountCreate
from app.schemas.contact import CustomerWrite, VendorWrite
from app.schemas.journal import JournalEntryCreate, JournalLineCreate
from app.schemas.platform import ImportResult
from app.services.account_service import AccountService
from app.services.contact_service import CustomerService, VendorService
from app.services.journal_service import JournalService

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y")


def read_date(text: str) -> date:
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(text.strip(), date_format).date()
        except ValueError:
            continue
    raise ValueError(f'"{text}" is not a date (use YYYY-MM-DD or MM/DD/YYYY)')


def read_money(text: str) -> Decimal:
    if not text or not text.strip():
        return Decimal("0")
    try:
        return Decimal(text.replace(",", "").replace("$", "").strip())
    except InvalidOperation:
        raise ValueError(f'"{text}" is not a number')


def read_rows(content: str) -> list[tuple[int, dict]]:
    """(row number, {lower-case column: value}) for each data row."""
    reader = csv.DictReader(io.StringIO(content.lstrip("﻿")))
    rows = []
    for row_number, row in enumerate(reader, start=2):
        clean = {}
        for key, value in row.items():
            if key is not None:
                clean[key.strip().lower()] = (value or "").strip()
        if any(clean.values()):
            rows.append((row_number, clean))
    return rows


def write_csv(header: list[str], rows: list[list]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(header)
    for row in rows:
        writer.writerow(["" if value is None else value for value in row])
    return output.getvalue()


class DataTransfer:
    """One list that can be imported and exported."""

    name = ""
    columns: list[str] = []

    def export_rows(self, company_id: int) -> list[list]:
        raise NotImplementedError

    def import_row(self, company_id: int, row: dict) -> str:
        """Save one row (without committing). Returns "created" or "updated"."""
        raise NotImplementedError


class ContactTransfer(DataTransfer):
    columns = ["Name", "Company", "Email", "Phone", "Address", "Notes"]

    def __init__(self, repository, service, write_model):
        self.repository = repository
        self.service = service
        self.write_model = write_model

    def export_rows(self, company_id: int) -> list[list]:
        return [
            [contact.display_name, contact.company_name, contact.email, contact.phone, contact.address, contact.notes]
            for contact in self.repository.list_all(company_id)
        ]

    def import_row(self, company_id: int, row: dict) -> str:
        name = row.get("name") or row.get("display name") or ""
        if not name:
            raise ValueError("the name is empty")
        data = self.write_model(
            display_name=name,
            company_name=row.get("company") or None,
            email=row.get("email") or None,
            phone=row.get("phone") or None,
            address=row.get("address") or None,
            notes=row.get("notes") or None,
        )
        existing = self.find_by_name(company_id, name)
        if existing is None:
            self.service.create_record(company_id, data)
            return "created"
        self.service.validate(company_id, data)
        for field_name in ("company_name", "email", "phone", "address", "notes"):
            value = getattr(data, field_name)
            if value is not None:
                setattr(existing, field_name, value)
        return "updated"

    def find_by_name(self, company_id: int, name: str):
        for contact in self.repository.list_all(company_id):
            if contact.display_name.lower() == name.lower():
                return contact
        return None


class AccountTransfer(DataTransfer):
    name = "accounts"
    columns = ["Number", "Name", "Type", "Detail type", "Description", "Parent"]

    def __init__(self, repository: AccountRepository, service: AccountService):
        self.repository = repository
        self.service = service

    def export_rows(self, company_id: int) -> list[list]:
        accounts = self.repository.list_all(company_id)
        names = {account.id: account.name for account in accounts}
        return [
            [account.code, account.name, account.account_type.value, account.detail_type, account.description, names.get(account.parent_id, "")]
            for account in accounts
        ]

    def import_row(self, company_id: int, row: dict) -> str:
        name = row.get("name", "")
        if not name:
            raise ValueError("the name is empty")
        if self.repository.get_by_name(company_id, name) is not None:
            return "skipped"
        type_text = row.get("type", "").upper()
        if type_text not in AccountType.__members__:
            raise ValueError(f'the type must be one of {", ".join(AccountType.__members__)}')
        parent_id = None
        if row.get("parent"):
            parent = self.repository.get_by_name(company_id, row["parent"])
            if parent is None:
                raise ValueError(f'the parent account "{row["parent"]}" does not exist (list it above its sub-accounts)')
            parent_id = parent.id
        data = AccountCreate(
            name=name,
            code=row.get("number") or None,
            account_type=AccountType[type_text],
            detail_type=row.get("detail type") or type_text.title(),
            description=row.get("description") or None,
            parent_id=parent_id,
        )
        self.service.create_without_commit(company_id, data)
        return "created"


class JournalEntryTransfer(DataTransfer):
    """Transactions in and out as journal entries."""

    name = "journal-entries"
    columns = ["Entry no", "Date", "Account", "Debit", "Credit", "Description", "Memo"]

    def __init__(self, journal_repository: JournalRepository, account_repository: AccountRepository, service: JournalService):
        self.journal_repository = journal_repository
        self.account_repository = account_repository
        self.service = service

    def export_rows(self, company_id: int) -> list[list]:
        rows = []
        for entry in sorted(self.journal_repository.list_all(company_id), key=lambda item: (item.entry_date, item.id)):
            for line in entry.lines:
                rows.append(
                    [
                        entry.id,
                        entry.entry_date.isoformat(),
                        line.account.name,
                        line.debit if line.debit else "",
                        line.credit if line.credit else "",
                        line.description,
                        entry.memo,
                    ]
                )
        return rows

    def import_entries(self, company_id: int, rows: list[tuple[int, dict]]) -> tuple[int, list[str]]:
        """Group rows by entry number and post each group. Returns (entries created, problems)."""
        groups = {}
        for row_number, row in rows:
            key = row.get("entry no") or row.get("entry") or str(row_number)
            groups.setdefault(key, []).append((row_number, row))

        created = 0
        errors = []
        for key, group in groups.items():
            try:
                first = group[0][1]
                lines = []
                for row_number, row in group:
                    account = self.account_repository.get_by_name(company_id, row.get("account", ""))
                    if account is None:
                        raise ValueError(f'row {row_number}: the account "{row.get("account", "")}" does not exist')
                    lines.append(
                        JournalLineCreate(
                            account_id=account.id,
                            debit=read_money(row.get("debit", "")),
                            credit=read_money(row.get("credit", "")),
                            description=row.get("description") or None,
                        )
                    )
                data = JournalEntryCreate(entry_date=read_date(first.get("date", "")), memo=first.get("memo") or None, lines=lines)
                self.service.create_manual(company_id, data, commit=False)
                created += 1
            except (AppError, ValueError) as problem:
                message = problem.message if isinstance(problem, AppError) else str(problem)
                errors.append(f"Entry {key}: {message}")
        return created, errors


class DataTransferService:
    def __init__(self, session, transfers: dict[str, DataTransfer]):
        self.session = session
        self.transfers = transfers

    def get(self, name: str) -> DataTransfer:
        transfer = self.transfers.get(name)
        if transfer is None:
            raise NotFoundError(f'"{name}" cannot be imported or exported.')
        return transfer

    def export_csv(self, company_id: int, name: str) -> str:
        transfer = self.get(name)
        return write_csv(transfer.columns, transfer.export_rows(company_id))

    def import_csv(self, company_id: int, name: str, content: str) -> ImportResult:
        transfer = self.get(name)
        rows = read_rows(content)
        if not rows:
            raise BusinessRuleError("The file has no rows under its header.")

        if isinstance(transfer, JournalEntryTransfer):
            created, errors = transfer.import_entries(company_id, rows)
            return self.finish(created, 0, errors)

        created = 0
        updated = 0
        errors = []
        for row_number, row in rows:
            try:
                outcome = transfer.import_row(company_id, row)
                self.session.flush()
                if outcome == "created":
                    created += 1
                elif outcome == "updated":
                    updated += 1
            except (AppError, ValueError) as problem:
                message = problem.message if isinstance(problem, AppError) else str(problem)
                errors.append(f"Row {row_number}: {message}")
        return self.finish(created, updated, errors)

    def finish(self, created: int, updated: int, errors: list[str]) -> ImportResult:
        """All or nothing: any problem undoes the whole import."""
        if errors:
            self.session.rollback()
            return ImportResult(created=0, updated=0, errors=errors)
        self.session.commit()
        return ImportResult(created=created, updated=updated, errors=[])


def build_transfers(
    customer_repository: CustomerRepository,
    customer_service: CustomerService,
    vendor_repository: VendorRepository,
    vendor_service: VendorService,
    account_repository: AccountRepository,
    account_service: AccountService,
    journal_repository: JournalRepository,
    journal_service: JournalService,
) -> dict[str, DataTransfer]:
    customers = ContactTransfer(customer_repository, customer_service, CustomerWrite)
    customers.name = "customers"
    vendors = ContactTransfer(vendor_repository, vendor_service, VendorWrite)
    vendors.name = "vendors"
    return {
        "customers": customers,
        "vendors": vendors,
        "accounts": AccountTransfer(account_repository, account_service),
        "journal-entries": JournalEntryTransfer(journal_repository, account_repository, journal_service),
    }
