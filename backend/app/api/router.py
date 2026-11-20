"""
Collects every route file into one router.
"""

from fastapi import APIRouter

from app.api.routes import (
    accounts,
    attachments,
    auth,
    banking,
    taxes,
    checks,
    customers,
    deposits,
    expenses,
    invoices,
    journal_entries,
    mileage,
    payments,
    products,
    public,
    purchases,
    recurring,
    reports,
    sales_documents,
    terms,
    vendors,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(accounts.router)
api_router.include_router(customers.router)
api_router.include_router(vendors.router)
api_router.include_router(products.router)
api_router.include_router(terms.router)
api_router.include_router(invoices.router)
api_router.include_router(sales_documents.router)
api_router.include_router(payments.router)
api_router.include_router(deposits.router)
api_router.include_router(banking.router)
api_router.include_router(taxes.router)
api_router.include_router(expenses.router)
api_router.include_router(purchases.router)
api_router.include_router(checks.router)
api_router.include_router(attachments.router)
api_router.include_router(mileage.router)
api_router.include_router(journal_entries.router)
api_router.include_router(recurring.router)
api_router.include_router(reports.router)
api_router.include_router(public.router)
