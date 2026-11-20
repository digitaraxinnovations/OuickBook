"""Categories, price rules, inventory adjustments and stock history."""

from datetime import date

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    get_catalog_service,
    get_current_user,
    get_inventory_adjustment_service,
    get_inventory_history,
)
from app.models import User
from app.repositories.inventory_repositories import InventoryMovementRepository
from app.schemas.inventory import InventoryAdjustmentCreate, InventoryAdjustmentRead, StockMovementRead
from app.schemas.product import CategoryRead, CategoryWrite, PriceRuleRead, PriceRuleWrite, ProductPrice
from app.services.catalog_service import CatalogService
from app.services.inventory_adjustment_service import InventoryAdjustmentService

router = APIRouter(tags=["Inventory"])


# ---------- categories ----------

@router.get("/product-categories", response_model=list[CategoryRead])
def list_categories(user: User = Depends(get_current_user), service: CatalogService = Depends(get_catalog_service)):
    return service.list_categories(user.company_id)


@router.post("/product-categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryWrite, user: User = Depends(get_current_user), service: CatalogService = Depends(get_catalog_service)):
    return service.save_category(user.company_id, data)


@router.put("/product-categories/{category_id}", response_model=CategoryRead)
def update_category(category_id: int, data: CategoryWrite, user: User = Depends(get_current_user), service: CatalogService = Depends(get_catalog_service)):
    return service.save_category(user.company_id, data, category_id)


# ---------- price rules ----------

@router.get("/price-rules", response_model=list[PriceRuleRead])
def list_price_rules(user: User = Depends(get_current_user), service: CatalogService = Depends(get_catalog_service)):
    return service.list_rules(user.company_id)


@router.post("/price-rules", response_model=PriceRuleRead, status_code=status.HTTP_201_CREATED)
def create_price_rule(data: PriceRuleWrite, user: User = Depends(get_current_user), service: CatalogService = Depends(get_catalog_service)):
    return service.save_rule(user.company_id, data)


@router.put("/price-rules/{rule_id}", response_model=PriceRuleRead)
def update_price_rule(rule_id: int, data: PriceRuleWrite, user: User = Depends(get_current_user), service: CatalogService = Depends(get_catalog_service)):
    return service.save_rule(user.company_id, data, rule_id)


@router.get("/product-prices", response_model=list[ProductPrice])
def product_prices(
    customer_id: int | None = None,
    on_date: date | None = None,
    user: User = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
):
    """Each item's price after price rules, for a customer and date (used when filling in a sales form)."""
    return service.prices(user.company_id, customer_id, on_date or date.today())


# ---------- inventory adjustments ----------

@router.get("/inventory-adjustments", response_model=list[InventoryAdjustmentRead])
def list_adjustments(user: User = Depends(get_current_user), service: InventoryAdjustmentService = Depends(get_inventory_adjustment_service)):
    return service.list(user.company_id)


@router.post("/inventory-adjustments", response_model=InventoryAdjustmentRead, status_code=status.HTTP_201_CREATED)
def create_adjustment(
    data: InventoryAdjustmentCreate,
    user: User = Depends(get_current_user),
    service: InventoryAdjustmentService = Depends(get_inventory_adjustment_service),
):
    return service.create(user.company_id, data)


@router.post("/inventory-adjustments/{adjustment_id}/void", response_model=InventoryAdjustmentRead)
def void_adjustment(
    adjustment_id: int,
    user: User = Depends(get_current_user),
    service: InventoryAdjustmentService = Depends(get_inventory_adjustment_service),
):
    return service.void(user.company_id, adjustment_id)


# ---------- stock history ----------

@router.get("/products/{product_id}/stock-history", response_model=list[StockMovementRead])
def stock_history(
    product_id: int,
    user: User = Depends(get_current_user),
    movements: InventoryMovementRepository = Depends(get_inventory_history),
):
    return movements.for_product(user.company_id, product_id)
