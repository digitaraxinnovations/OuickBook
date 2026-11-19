"""
Creates every recurring transaction that is due today, for every company.

Run it once a day from a scheduler (Windows Task Scheduler, cron, etc.):
    cd backend
    .venv\\Scripts\\python -m app.scripts.run_recurring
"""

from datetime import date

from app.api.deps import build_recurring_service
from app.db.session import SessionLocal
from app.repositories.recurring_repository import RecurringRepository


def main() -> None:
    today = date.today()
    session = SessionLocal()
    try:
        company_ids = RecurringRepository(session).company_ids_with_due_schedules(today)
        service = build_recurring_service(session)
        total = 0
        for company_id in company_ids:
            created = service.run_due(company_id, today)
            total += len(created)
        print(f"Created {total} recurring transaction(s) for {len(company_ids)} company(ies).")
    finally:
        session.close()


if __name__ == "__main__":
    main()
