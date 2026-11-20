from datetime import date

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_current_user, get_mileage_service
from app.models import User
from app.schemas.purchase import MileageRateUpdate, MileageSummary, TripRead, TripWrite
from app.services.mileage_service import MileageService

router = APIRouter(prefix="/mileage", tags=["Mileage"])


@router.get("/trips", response_model=list[TripRead])
def list_trips(
    year: int | None = None,
    user: User = Depends(get_current_user),
    service: MileageService = Depends(get_mileage_service),
):
    return service.list_year(user.company_id, year or date.today().year)


@router.post("/trips", response_model=TripRead, status_code=status.HTTP_201_CREATED)
def create_trip(
    data: TripWrite,
    user: User = Depends(get_current_user),
    service: MileageService = Depends(get_mileage_service),
):
    return service.create(user.company_id, data)


@router.put("/trips/{trip_id}", response_model=TripRead)
def update_trip(
    trip_id: int,
    data: TripWrite,
    user: User = Depends(get_current_user),
    service: MileageService = Depends(get_mileage_service),
):
    return service.update(user.company_id, trip_id, data)


@router.delete("/trips/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(
    trip_id: int,
    user: User = Depends(get_current_user),
    service: MileageService = Depends(get_mileage_service),
):
    service.delete(user.company_id, trip_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/summary", response_model=MileageSummary)
def mileage_summary(
    year: int | None = None,
    user: User = Depends(get_current_user),
    service: MileageService = Depends(get_mileage_service),
):
    return service.summary(user.company_id, year or date.today().year)


@router.put("/rate", response_model=MileageSummary)
def set_mileage_rate(
    data: MileageRateUpdate,
    user: User = Depends(get_current_user),
    service: MileageService = Depends(get_mileage_service),
):
    service.set_rate(user.company_id, data)
    return service.summary(user.company_id, date.today().year)
