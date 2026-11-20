"""
Who may do what.

Every API path belongs to an area (sales, purchases, banking...). Each role
can read and/or change each area. The check runs once per request, in
get_current_user, so no route has to remember to check permissions.

To change what a role can do, edit ROLE_ACCESS. To put a new route in an
area, add its first path part to AREA_OF_PATH.
"""

from app.models.enums import UserRole

READ = "read"
WRITE = "write"

# First part of the API path -> area. Paths not listed are "accounting".
AREA_OF_PATH = {
    # always allowed for any signed-in member
    "auth": "always",
    "companies": "always",
    "search": "always",
    "recent": "always",
    "attachments": "always",
    "notifications": "always",
    # sales and customers
    "invoices": "sales",
    "sales-documents": "sales",
    "payments": "sales",
    "customers": "sales",
    "products": "sales",
    "product-categories": "sales",
    "price-rules": "sales",
    "product-prices": "sales",
    "inventory-adjustments": "sales",
    "terms": "sales",
    "email-log": "sales",
    # expenses and vendors
    "expenses": "purchases",
    "purchase-documents": "purchases",
    "bill-payments": "purchases",
    "vendors": "purchases",
    "checks": "purchases",
    "mileage": "purchases",
    # banking
    "banking": "banking",
    "deposits": "banking",
    # payroll and time
    "employees": "payroll",
    "pay-schedules": "payroll",
    "pay-items": "payroll",
    "payroll-runs": "payroll",
    "payroll-liabilities": "payroll",
    "payroll": "payroll",
    "time-entries": "time",
    # reports
    "reports": "reports",
    "saved-reports": "reports",
    "report-schedules": "reports",
    "dashboard": "reports",
    # company settings and users
    "company": "settings",
    "audit-log": "settings",
    "currencies": "settings",
    "exchange-rates": "settings",
    "data": "settings",
    "users": "users",
    "invitations": "users",
}

ALL_AREAS = ["sales", "purchases", "banking", "accounting", "payroll", "time", "reports", "settings", "users"]


def full_access(except_areas: dict[str, str] | None = None) -> dict[str, str]:
    access = {area: WRITE for area in ALL_AREAS}
    for area, level in (except_areas or {}).items():
        if level is None:
            access.pop(area, None)
        else:
            access[area] = level
    return access


# role -> {area: READ or WRITE}. A missing area means no access.
ROLE_ACCESS = {
    UserRole.ADMIN: full_access(),
    UserRole.ACCOUNTANT: full_access({"users": READ}),
    UserRole.STANDARD: full_access({"settings": READ, "users": None}),
    # Limited roles still read the lists their screens need (accounts, products...).
    UserRole.SALES: {"sales": WRITE, "time": WRITE, "accounting": READ, "settings": READ},
    UserRole.PURCHASES: {"purchases": WRITE, "sales": READ, "accounting": READ, "settings": READ},
    UserRole.REPORTS_ONLY: {"reports": WRITE, "sales": READ, "purchases": READ, "accounting": READ, "settings": READ},
    UserRole.TIME_ONLY: {"time": WRITE, "sales": READ, "purchases": READ, "payroll": READ, "accounting": READ},
}

ROLE_LABELS = {
    UserRole.ADMIN: "Admin - everything, including users and settings",
    UserRole.ACCOUNTANT: "Accountant - everything except managing users",
    UserRole.STANDARD: "Standard - all transactions and reports, no settings or users",
    UserRole.SALES: "Customers and sales only",
    UserRole.PURCHASES: "Vendors and purchases only",
    UserRole.REPORTS_ONLY: "Reports only",
    UserRole.TIME_ONLY: "Time tracking only",
}


def area_of(path: str, api_prefix: str) -> str:
    """'/api/v1/invoices/12' -> 'sales'."""
    if path.startswith(api_prefix):
        path = path[len(api_prefix):]
    first = path.strip("/").split("/")[0]
    return AREA_OF_PATH.get(first, "accounting")


def is_allowed(role: UserRole, area: str, method: str) -> bool:
    if area == "always":
        return True
    level = ROLE_ACCESS.get(role, {}).get(area)
    if level is None:
        return False
    if method in ("GET", "HEAD", "OPTIONS"):
        return True
    return level == WRITE
