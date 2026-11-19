"""
The daily job. Run it once a day from a scheduler (Windows Task Scheduler, cron...):

    cd backend
    .venv\\Scripts\\python -m app.scripts.run_daily_jobs

For every company it:
  1. creates recurring transactions that are due,
  2. adds late fees to overdue invoices (if turned on),
  3. emails overdue reminders (if turned on).
"""

from datetime import date

from sqlalchemy import select

from app.api.deps import build_customer_documents_service, build_late_fee_service, build_recurring_service
from app.db.session import SessionLocal
from app.models import Company


def main() -> None:
    today = date.today()
    session = SessionLocal()
    try:
        company_ids = list(session.scalars(select(Company.id)))
        recurring = build_recurring_service(session)
        late_fees = build_late_fee_service(session)
        documents = build_customer_documents_service(session)

        for company_id in company_ids:
            created = recurring.run_due(company_id, today)
            fees = late_fees.apply_due(company_id, today)
            reminders = documents.send_overdue_reminders(company_id, today)
            print(
                f"Company {company_id}: {len(created)} recurring, "
                f"{fees.count} late fee(s), {reminders.count} reminder(s)"
            )
    finally:
        session.close()


if __name__ == "__main__":
    main()
