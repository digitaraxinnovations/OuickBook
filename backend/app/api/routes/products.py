from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_product_service
from app.models import User
from app.schemas.product import ProductRead, ProductWrite
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products and Services"])


@router.get("", response_model=list[ProductRead])
def list_products(
    active_only: bool = False,
    user: User = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return service.list(user.company_id, active_only)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductWrite,
    user: User = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return service.create(user.company_id, data)


@router.put("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    data: ProductWrite,
    user: User = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return service.update(user.company_id, product_id, data)
