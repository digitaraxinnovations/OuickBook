from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_vendor_service
from app.models import User
from app.schemas.contact import ContactWrite, VendorRead
from app.services.contact_service import VendorService

router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.get("", response_model=list[VendorRead])
def list_vendors(
    active_only: bool = False,
    user: User = Depends(get_current_user),
    service: VendorService = Depends(get_vendor_service),
):
    return service.list(user.company_id, active_only)


@router.get("/{vendor_id}", response_model=VendorRead)
def get_vendor(
    vendor_id: int,
    user: User = Depends(get_current_user),
    service: VendorService = Depends(get_vendor_service),
):
    return service.get(user.company_id, vendor_id)


@router.post("", response_model=VendorRead, status_code=status.HTTP_201_CREATED)
def create_vendor(
    data: ContactWrite,
    user: User = Depends(get_current_user),
    service: VendorService = Depends(get_vendor_service),
):
    return service.create(user.company_id, data)


@router.put("/{vendor_id}", response_model=VendorRead)
def update_vendor(
    vendor_id: int,
    data: ContactWrite,
    user: User = Depends(get_current_user),
    service: VendorService = Depends(get_vendor_service),
):
    return service.update(user.company_id, vendor_id, data)
