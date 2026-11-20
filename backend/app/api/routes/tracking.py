"""Classes, locations, tags, projects and budgets."""

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_budget_service, get_current_user, get_project_service, get_tracking_service
from app.models import User
from app.schemas.tracking import (
    BudgetRead,
    BudgetSummary,
    BudgetVsActual,
    BudgetWrite,
    NamedListRead,
    NamedListWrite,
    ProjectRead,
    ProjectSummary,
    ProjectWrite,
    TagRead,
    TagWrite,
)
from app.services.budget_service import BudgetService
from app.services.project_service import ProjectService
from app.services.tracking_service import TrackingService

router = APIRouter(tags=["Classes, locations, projects and budgets"])

CurrentUser = Depends(get_current_user)
Tracking = Depends(get_tracking_service)
Budgets = Depends(get_budget_service)


# ---------- classes ----------

@router.get("/classes", response_model=list[NamedListRead])
def list_classes(user: User = CurrentUser, service: TrackingService = Tracking):
    return service.list_classes(user.company_id)


@router.post("/classes", response_model=NamedListRead, status_code=status.HTTP_201_CREATED)
def create_class(data: NamedListWrite, user: User = CurrentUser, service: TrackingService = Tracking):
    return service.save_class(user.company_id, data)


@router.put("/classes/{class_id}", response_model=NamedListRead)
def update_class(class_id: int, data: NamedListWrite, user: User = CurrentUser, service: TrackingService = Tracking):
    return service.save_class(user.company_id, data, class_id)


# ---------- locations ----------

@router.get("/locations", response_model=list[NamedListRead])
def list_locations(user: User = CurrentUser, service: TrackingService = Tracking):
    return service.list_locations(user.company_id)


@router.post("/locations", response_model=NamedListRead, status_code=status.HTTP_201_CREATED)
def create_location(data: NamedListWrite, user: User = CurrentUser, service: TrackingService = Tracking):
    return service.save_location(user.company_id, data)


@router.put("/locations/{location_id}", response_model=NamedListRead)
def update_location(location_id: int, data: NamedListWrite, user: User = CurrentUser, service: TrackingService = Tracking):
    return service.save_location(user.company_id, data, location_id)


# ---------- tags ----------

@router.get("/tags", response_model=list[TagRead])
def list_tags(user: User = CurrentUser, service: TrackingService = Tracking):
    return service.list_tags(user.company_id)


@router.post("/tags", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag(data: TagWrite, user: User = CurrentUser, service: TrackingService = Tracking):
    return service.save_tag(user.company_id, data)


@router.put("/tags/{tag_id}", response_model=TagRead)
def update_tag(tag_id: int, data: TagWrite, user: User = CurrentUser, service: TrackingService = Tracking):
    return service.save_tag(user.company_id, data, tag_id)


# ---------- projects ----------

@router.get("/projects", response_model=list[ProjectRead])
def list_projects(active_only: bool = False, user: User = CurrentUser, service: TrackingService = Tracking):
    return service.list_projects(user.company_id, active_only)


@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectWrite, user: User = CurrentUser, service: TrackingService = Tracking):
    return service.save_project(user.company_id, data)


@router.put("/projects/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, data: ProjectWrite, user: User = CurrentUser, service: TrackingService = Tracking):
    return service.save_project(user.company_id, data, project_id)


@router.get("/projects/{project_id}/summary", response_model=ProjectSummary)
def project_summary(project_id: int, user: User = CurrentUser, service: ProjectService = Depends(get_project_service)):
    return service.summary(user.company_id, project_id)


# ---------- budgets ----------

@router.get("/budgets", response_model=list[BudgetSummary])
def list_budgets(user: User = CurrentUser, service: BudgetService = Budgets):
    return service.list(user.company_id)


@router.get("/budgets/{budget_id}", response_model=BudgetRead)
def get_budget(budget_id: int, user: User = CurrentUser, service: BudgetService = Budgets):
    return service.get(user.company_id, budget_id)


@router.post("/budgets", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
def create_budget(data: BudgetWrite, user: User = CurrentUser, service: BudgetService = Budgets):
    return service.save(user.company_id, data)


@router.put("/budgets/{budget_id}", response_model=BudgetRead)
def update_budget(budget_id: int, data: BudgetWrite, user: User = CurrentUser, service: BudgetService = Budgets):
    return service.save(user.company_id, data, budget_id)


@router.delete("/budgets/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(budget_id: int, user: User = CurrentUser, service: BudgetService = Budgets):
    service.delete(user.company_id, budget_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/budgets/{budget_id}/vs-actual", response_model=BudgetVsActual)
def budget_vs_actual(budget_id: int, first_month: int = 1, last_month: int = 12, user: User = CurrentUser, service: BudgetService = Budgets):
    return service.vs_actual(user.company_id, budget_id, first_month, last_month)
