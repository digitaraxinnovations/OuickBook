from datetime import date

from sqlalchemy import func, select

from app.models import Budget, JournalEntry, JournalLine, Location, Project, Tag, TimeEntry, TrackingClass
from app.repositories.base import BaseRepository


class NamedRepository(BaseRepository):
    """Lists ordered and looked up by name."""

    def order_by_columns(self) -> list:
        return [self.model.name]

    def get_by_name(self, company_id: int, name: str):
        query = select(self.model).where(self.model.company_id == company_id, func.lower(self.model.name) == name.lower())
        return self.session.scalar(query)


class TrackingClassRepository(NamedRepository):
    model = TrackingClass


class LocationRepository(NamedRepository):
    model = Location


class TagRepository(NamedRepository):
    model = Tag

    def list_all(self, company_id: int, active_only: bool = False) -> list[Tag]:
        query = select(Tag).where(Tag.company_id == company_id).order_by(Tag.group_name, Tag.name)
        return list(self.session.scalars(query))


class ProjectRepository(NamedRepository):
    model = Project

    def list_all(self, company_id: int, active_only: bool = False) -> list[Project]:
        query = select(Project).where(Project.company_id == company_id).order_by(Project.name)
        return list(self.session.scalars(query))

    def has_transactions(self, company_id: int, project_id: int) -> bool:
        query = (
            select(JournalLine.id)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(JournalEntry.company_id == company_id, JournalLine.project_id == project_id)
        )
        return self.session.scalars(query).first() is not None

    def lines_for(self, company_id: int, project_id: int, start: date | None = None, end: date | None = None) -> list[JournalLine]:
        query = (
            select(JournalLine)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(JournalEntry.company_id == company_id, JournalLine.project_id == project_id)
        )
        if start is not None:
            query = query.where(JournalEntry.entry_date >= start)
        if end is not None:
            query = query.where(JournalEntry.entry_date <= end)
        return list(self.session.scalars(query.order_by(JournalEntry.entry_date, JournalLine.id)))

    def time_for(self, company_id: int, project_id: int, start: date | None = None, end: date | None = None) -> list[TimeEntry]:
        query = select(TimeEntry).where(TimeEntry.company_id == company_id, TimeEntry.project_id == project_id)
        if start is not None:
            query = query.where(TimeEntry.work_date >= start)
        if end is not None:
            query = query.where(TimeEntry.work_date <= end)
        return list(self.session.scalars(query))


class BudgetRepository(BaseRepository):
    model = Budget

    def order_by_columns(self) -> list:
        return [Budget.fiscal_year.desc(), Budget.name]


class DimensionQueries:
    """Journal lines added up per account and per class / location / project / tag."""

    def __init__(self, session):
        self.session = session

    def totals(self, company_id: int, dimension: str, start: date | None, end: date) -> list[tuple]:
        """
        Rows of (dimension value, account_id, debit, credit).
        `dimension` is "class", "location", "project" or "tag".
        Lines without a value come back with None.
        """
        if dimension == "tag":
            return self.tag_totals(company_id, start, end)
        column = {
            "class": JournalLine.class_id,
            "location": JournalLine.location_id,
            "project": JournalLine.project_id,
        }[dimension]
        query = (
            select(column, JournalLine.account_id, func.sum(JournalLine.debit), func.sum(JournalLine.credit))
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(JournalEntry.company_id == company_id, JournalEntry.entry_date <= end)
            .group_by(column, JournalLine.account_id)
        )
        if start is not None:
            query = query.where(JournalEntry.entry_date >= start)
        return [tuple(row) for row in self.session.execute(query)]

    def tag_totals(self, company_id: int, start: date | None, end: date) -> list[tuple]:
        """
        Like totals(), per tag. An entry with two tags counts under both;
        entries without tags are grouped under None.
        """
        tag_value = func.unnest(JournalEntry.tag_ids).label("tag_id")
        tagged = (
            select(tag_value, JournalLine.account_id, JournalLine.debit, JournalLine.credit)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(JournalEntry.company_id == company_id, JournalEntry.entry_date <= end)
        )
        untagged = (
            select(JournalLine.account_id, func.sum(JournalLine.debit), func.sum(JournalLine.credit))
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(
                JournalEntry.company_id == company_id,
                JournalEntry.entry_date <= end,
                func.cardinality(JournalEntry.tag_ids) == 0,
            )
            .group_by(JournalLine.account_id)
        )
        if start is not None:
            tagged = tagged.where(JournalEntry.entry_date >= start)
            untagged = untagged.where(JournalEntry.entry_date >= start)

        inner = tagged.subquery()
        per_tag = select(inner.c.tag_id, inner.c.account_id, func.sum(inner.c.debit), func.sum(inner.c.credit)).group_by(
            inner.c.tag_id, inner.c.account_id
        )
        rows = [tuple(row) for row in self.session.execute(per_tag)]
        for account_id, debit, credit in self.session.execute(untagged):
            rows.append((None, account_id, debit, credit))
        return rows
