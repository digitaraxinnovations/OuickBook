from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_tax_rate_provider, get_tax_service
from app.integrations.tax_rates import TaxRateProvider
from app.models import User
from app.schemas.tax import (
    RateLookupRequest,
    RateLookupResult,
    SalesTaxAdjustmentCreate,
    SalesTaxAdjustmentRead,
    SalesTaxPaymentCreate,
    SalesTaxPaymentRead,
    TaxAgencyRead,
    TaxAgencyWrite,
    TaxCodeRead,
    TaxCodeWrite,
    TaxPeriod,
    TaxRateRead,
    TaxRateWrite,
)
from app.seed.default_accounts import TAX_LINES
from app.services.tax_service import TaxService

router = APIRouter(prefix="/taxes", tags=["Taxes"])


# ---------- agencies ----------

@router.get("/agencies", response_model=list[TaxAgencyRead])
def list_agencies(user: User = Depends(get_current_user), service: TaxService = Depends(get_tax_service)):
    return service.list_agencies(user.company_id)


@router.post("/agencies", response_model=TaxAgencyRead, status_code=status.HTTP_201_CREATED)
def create_agency(data: TaxAgencyWrite, user: User = Depends(get_current_user), service: TaxService = Depends(get_tax_service)):
    return service.create_agency(user.company_id, data)


@router.put("/agencies/{agency_id}", response_model=TaxAgencyRead)
def update_agency(agency_id: int, data: TaxAgencyWrite, user: User = Depends(get_current_user), service: TaxService = Depends(get_tax_service)):
    return service.update_agency(user.company_id, agency_id, data)


# ---------- rates ----------

@router.get("/rates", response_model=list[TaxRateRead])
def list_rates(user: User = Depends(get_current_user), service: TaxService = Depends(get_tax_service)):
    return service.list_rates(user.company_id)


@router.post("/rates", response_model=TaxRateRead, status_code=status.HTTP_201_CREATED)
def create_rate(data: TaxRateWrite, user: User = Depends(get_current_user), service: TaxService = Depends(get_tax_service)):
    return service.create_rate(user.company_id, data)


@router.put("/rates/{rate_id}", response_model=TaxRateRead)
def update_rate(rate_id: int, data: TaxRateWrite, user: User = Depends(get_current_user), service: TaxService = Depends(get_tax_service)):
    return service.update_rate(user.company_id, rate_id, data)


# ---------- codes (what you pick on a sales form) ----------

@router.get("/codes", response_model=list[TaxCodeRead])
def list_codes(active_only: bool = False, user: User = Depends(get_current_user), service: TaxService = Depends(get_tax_service)):
    return service.list_codes(user.company_id, active_only)


@router.post("/codes", response_model=TaxCodeRead, status_code=status.HTTP_201_CREATED)
def create_code(data: TaxCodeWrite, user: User = Depends(get_current_user), service: TaxService = Depends(get_tax_service)):
    return service.create_code(user.company_id, data)


@router.put("/codes/{code_id}", response_model=TaxCodeRead)
def update_code(code_id: int, data: TaxCodeWrite, user: User = Depends(get_current_user), service: TaxService = Depends(get_tax_service)):
    return service.update_code(user.company_id, code_id, data)


# ---------- filing ----------

@router.get("/periods", response_model=list[TaxPeriod])
def list_periods(agency_id: int | None = None, user: User = Depends(get_current_user), service: TaxService = Depends(get_tax_service)):
    return service.periods(user.company_id, agency_id)


@router.get("/payments", response_model=list[SalesTaxPaymentRead])
def list_payments(agency_id: int | None = None, user: User = Depends(get_current_user), service: TaxService = Depends(get_tax_service)):
    return service.list_payments(user.company_id, agency_id)


@router.post("/payments", response_model=SalesTaxPaymentRead, status_code=status.HTTP_201_CREATED)
def record_payment(data: SalesTaxPaymentCreate, user: User = Depends(get_current_user), service: TaxService = Depends(get_tax_service)):
    return service.record_payment(user.company_id, data)


@router.get("/adjustments", response_model=list[SalesTaxAdjustmentRead])
def list_adjustments(agency_id: int | None = None, user: User = Depends(get_current_user), service: TaxService = Depends(get_tax_service)):
    return service.list_adjustments(user.company_id, agency_id)


@router.post("/adjustments", response_model=SalesTaxAdjustmentRead, status_code=status.HTTP_201_CREATED)
def record_adjustment(data: SalesTaxAdjustmentCreate, user: User = Depends(get_current_user), service: TaxService = Depends(get_tax_service)):
    return service.record_adjustment(user.company_id, data)


# ---------- income tax categories ----------

@router.get("/tax-lines", response_model=dict[str, str])
def list_tax_lines(user: User = Depends(get_current_user)):
    return TAX_LINES


# ---------- automatic rates (EXT) ----------

@router.get("/lookup/status")
def lookup_status(user: User = Depends(get_current_user), provider: TaxRateProvider = Depends(get_tax_rate_provider)):
    return {"enabled": provider.is_enabled(), "provider": provider.provider_name}


@router.post("/lookup", response_model=list[RateLookupResult])
def lookup_rates(data: RateLookupRequest, user: User = Depends(get_current_user), provider: TaxRateProvider = Depends(get_tax_rate_provider)):
    result = []
    for found in provider.lookup_rates(data.address):
        result.append(RateLookupResult(name=found.name, rate=found.rate))
    return result
