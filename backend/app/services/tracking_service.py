"""
Classes, locations, tags and projects - the lists, and the checks every
transaction runs before it uses them.
"""

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import Location, Project, Tag, TrackingClass
from app.models.enums import ProjectStatus
from app.repositories.contact_repository import CustomerRepository
from app.repositories.tracking_repositories import (
    LocationRepository,
    ProjectRepository,
    TagRepository,
    TrackingClassRepository,
)
from app.schemas.tracking import NamedListWrite, ProjectWrite, TagWrite, TrackingInput
from app.services.base import BaseService
from app.services.ledger_service import Tracking


class TrackingService(BaseService):
    def __init__(
        self,
        session,
        class_repository: TrackingClassRepository,
        location_repository: LocationRepository,
        tag_repository: TagRepository,
        project_repository: ProjectRepository,
        customer_repository: CustomerRepository,
    ):
        super().__init__(session)
        self.class_repository = class_repository
        self.location_repository = location_repository
        self.tag_repository = tag_repository
        self.project_repository = project_repository
        self.customer_repository = customer_repository

    # ---------- checking a transaction's tracking ----------

    def check(self, company_id: int, data: TrackingInput, customer_id: int | None = None) -> Tracking:
        """
        Make sure the class, location, project and tags exist.
        On a sales form the project must belong to the form's customer.
        """
        if data.class_id is not None and self.class_repository.get(company_id, data.class_id) is None:
            raise BusinessRuleError("That class does not exist.")
        if data.location_id is not None and self.location_repository.get(company_id, data.location_id) is None:
            raise BusinessRuleError("That location does not exist.")
        if data.project_id is not None:
            project = self.project_repository.get(company_id, data.project_id)
            if project is None:
                raise BusinessRuleError("That project does not exist.")
            if customer_id is not None and project.customer_id != customer_id:
                raise BusinessRuleError("That project belongs to another customer.")
        tag_ids = []
        for tag_id in data.tag_ids:
            if self.tag_repository.get(company_id, tag_id) is None:
                raise BusinessRuleError("A tag does not exist.")
            if tag_id not in tag_ids:
                tag_ids.append(tag_id)
        return Tracking(data.class_id, data.location_id, data.project_id, tag_ids)

    @staticmethod
    def apply(record, tracking: Tracking) -> None:
        """Save the tracking on the transaction itself (so it shows when the form is opened)."""
        record.class_id = tracking.class_id
        record.location_id = tracking.location_id
        record.project_id = tracking.project_id
        record.tag_ids = list(tracking.tag_ids)

    # ---------- classes and locations ----------

    def list_classes(self, company_id: int) -> list[TrackingClass]:
        return self.class_repository.list_all(company_id)

    def save_class(self, company_id: int, data: NamedListWrite, class_id: int | None = None) -> TrackingClass:
        return self.save_named(company_id, data, class_id, self.class_repository, TrackingClass, "class")

    def list_locations(self, company_id: int) -> list[Location]:
        return self.location_repository.list_all(company_id)

    def save_location(self, company_id: int, data: NamedListWrite, location_id: int | None = None) -> Location:
        return self.save_named(company_id, data, location_id, self.location_repository, Location, "location")

    def save_named(self, company_id: int, data: NamedListWrite, record_id: int | None, repository, model, label: str):
        """Classes and locations work the same way: a name, an optional parent, active or not."""
        existing = repository.get_by_name(company_id, data.name)
        if existing is not None and existing.id != record_id:
            raise ConflictError(f"A {label} with this name already exists.")
        if record_id is None:
            record = model(company_id=company_id)
        else:
            record = repository.get(company_id, record_id)
            if record is None:
                raise NotFoundError(f"That {label} does not exist.")
        if data.parent_id is not None:
            self.check_parent(company_id, repository, record_id, data.parent_id, label)
        record.name = data.name
        record.parent_id = data.parent_id
        record.is_active = data.is_active
        if record_id is None:
            repository.add(record)
        self.commit()
        return record

    def check_parent(self, company_id: int, repository, record_id: int | None, parent_id: int, label: str) -> None:
        parent = repository.get(company_id, parent_id)
        if parent is None:
            raise BusinessRuleError(f"The parent {label} does not exist.")
        while parent is not None:
            if parent.id == record_id:
                raise BusinessRuleError(f"A {label} cannot be inside itself.")
            parent = repository.get(company_id, parent.parent_id) if parent.parent_id else None

    # ---------- tags ----------

    def list_tags(self, company_id: int) -> list[Tag]:
        return self.tag_repository.list_all(company_id)

    def save_tag(self, company_id: int, data: TagWrite, tag_id: int | None = None) -> Tag:
        existing = self.tag_repository.get_by_name(company_id, data.name)
        if existing is not None and existing.id != tag_id:
            raise ConflictError("A tag with this name already exists.")
        if tag_id is None:
            tag = Tag(company_id=company_id)
        else:
            tag = self.tag_repository.get(company_id, tag_id)
            if tag is None:
                raise NotFoundError("Tag not found.")
        tag.name = data.name
        tag.group_name = data.group_name
        if tag_id is None:
            self.tag_repository.add(tag)
        self.commit()
        return tag

    # ---------- projects ----------

    def list_projects(self, company_id: int, active_only: bool = False) -> list[Project]:
        projects = self.project_repository.list_all(company_id)
        if active_only:
            projects = [project for project in projects if project.status == ProjectStatus.IN_PROGRESS]
        return projects

    def get_project(self, company_id: int, project_id: int) -> Project:
        project = self.project_repository.get(company_id, project_id)
        if project is None:
            raise NotFoundError("Project not found.")
        return project

    def save_project(self, company_id: int, data: ProjectWrite, project_id: int | None = None) -> Project:
        if self.customer_repository.get(company_id, data.customer_id) is None:
            raise BusinessRuleError("Please choose a customer for the project.")
        if data.start_date and data.end_date and data.end_date < data.start_date:
            raise BusinessRuleError("The end date cannot be before the start date.")
        if project_id is None:
            project = Project(company_id=company_id)
        else:
            project = self.get_project(company_id, project_id)
            if project.customer_id != data.customer_id and self.project_repository.has_transactions(company_id, project.id):
                raise BusinessRuleError("This project has transactions, so its customer cannot change.")
        for field_name, value in data.model_dump().items():
            setattr(project, field_name, value)
        if project_id is None:
            self.project_repository.add(project)
        self.commit()
        return project
