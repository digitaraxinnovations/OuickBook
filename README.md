# Ledgerly

Small-business accounting app modeled on QuickBooks Online: invoices, payments,
expenses, a chart of accounts, double-entry bookkeeping and financial reports.

| Layer    | Tech                                              |
|----------|---------------------------------------------------|
| Backend  | Python, FastAPI, SQLAlchemy 2, Alembic, Pydantic  |
| Database | PostgreSQL 17 (Docker)                            |
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4 |

---

## Features

- **Sign up / sign in** - each sign-up creates a company with a ready-made Chart of Accounts and payment terms.
- **Sales** - customers (with statements), products & services, invoices with discounts, shipping,
  deposits, payment terms and late fees; estimates with progress invoicing; sales receipts,
  credit memos, refund receipts, delayed charges and credits; payments across several invoices
  using credits and overpayments; PDF, email and a customer "view invoice" link.
- **Banking** - bank deposits from Undeposited Funds.
- **Expenses** - vendors (with 1099 tracking), expenses and checks (numbering, batch printing),
  bills with terms, paying bills one by one or in batches, vendor credits, purchase orders,
  receipt uploads and attachments, mileage log.
- **Accounting** - chart of accounts with sub-accounts and live balances, journal entries
  (automatic + manual), recurring invoices / sales receipts / bills / expenses / journal entries.
- **Reports** - Profit and Loss, Balance Sheet, Trial Balance, A/R Aging, A/P Aging, 1099 summary.
- **Dashboard** - income, expenses, net income, unpaid and overdue invoices, bank balances.

Every money event is posted to the general ledger as a balanced journal entry
(debits always equal credits), so all reports are built from one source of truth.

The full roadmap, and what is done, is in [docs/FEATURES.md](docs/FEATURES.md).

### Outside services (EXT)

Features that need an outside provider work out of the box in a safe "off" mode and
switch on with settings in `.env` - no code changes:

| Feature | Setting | Default |
|---|---|---|
| Sending email | `EMAIL_PROVIDER` = `log` or `smtp` (+ `SMTP_*`) | `log`: emails are saved in **Settings → Email log** instead of being sent |
| "Pay now" on invoices | `PAYMENT_PROVIDER` | `none`: button hidden. Add a class in `backend/app/integrations/payments.py` |
| Links in emails | `PUBLIC_APP_URL` | `http://localhost:3000` |

---

## Folder structure

```
QuickBooks/
├── .env                    # central config for backend + database (not committed)
├── .env.example            # documented template of every setting
├── docker-compose.yml      # PostgreSQL
├── backend/
│   ├── alembic/            # database migrations
│   ├── app/
│   │   ├── main.py         # creates the FastAPI app
│   │   ├── core/           # config, security, errors, money helpers
│   │   ├── db/             # SQLAlchemy base class and session
│   │   ├── models/         # database tables (one file per area)
│   │   ├── schemas/        # request / response shapes (Pydantic)
│   │   ├── repositories/   # database queries only - no business rules
│   │   ├── services/       # business rules (invoices, payments, ledger...)
│   │   ├── reports/        # one class per report
│   │   ├── seed/           # default chart of accounts (plain data)
│   │   └── api/
│   │       ├── deps.py     # builds services for the routes (dependency wiring)
│   │       ├── router.py   # collects all routes
│   │       └── routes/     # thin HTTP endpoints, one file per area
│   └── tests/              # API tests against a separate test database
└── frontend/
    ├── .env.local          # frontend config (API URL, app name...)
    └── src/
        ├── config/         # app.config.ts (central config) + navigation.ts (menus)
        ├── lib/            # ApiClient, TokenStorage, formatting helpers
        ├── services/       # one class per API resource; index.ts creates them
        ├── types/          # TypeScript shapes of API data
        ├── context/        # AuthContext (signed-in user and company)
        ├── hooks/          # useLoad, useFormState, useQueryFlag
        ├── components/     # ui/, layout/, forms/, lists/, reports/
        └── app/            # pages (Next.js App Router)
```

### How a request flows

```
Route (HTTP only) -> Service (business rules) -> Repository (database) -> PostgreSQL
                          |
                          +-> LedgerService (posts balanced journal entries)
```

### SOLID in this codebase

- **Single responsibility** - routes only handle HTTP, services only hold rules,
  repositories only query. `PasswordHasher` and `TokenService` each do one job.
- **Open/closed** - add a report by writing a new `Report` subclass and listing it in
  `build_default_reports()`; nothing else changes. Sidebar items live in `navigation.ts`.
- **Liskov substitution** - every report can be run the same way through `ReportService`;
  `CustomerService`, `VendorService` and `ProductService` are drop-in `CrudService`s.
- **Interface segregation** - small, focused classes (e.g. `LedgerService` exposes just
  `post` and `reverse`), and the frontend services each cover one resource.
- **Dependency inversion** - services receive their repositories in the constructor;
  `api/deps.py` (backend) and `services/index.ts` (frontend) are the only places that
  build objects.

### Configuration

Nothing is hardcoded. Backend and database settings live in the root `.env`
(read by `backend/app/core/config.py`). Frontend settings live in
`frontend/.env.local` (read by `frontend/src/config/app.config.ts`).

---

## Running it locally

Requirements: Docker Desktop, Python 3.12+, Node.js 20+.

**1. Configuration** (first time only)

```powershell
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env.local
```

Then edit `.env`: set `POSTGRES_PASSWORD` and a long random `JWT_SECRET_KEY`.

**2. Database**

```powershell
docker compose up -d
```

**3. Backend** (inside `backend/`)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

**4. Frontend** (inside `frontend/`)

```powershell
npm install
npm run dev
```

Open http://localhost:3000 and create an account.

> If port 3000 is busy, run `npm run dev -- --port 3001` and add
> `http://localhost:3001` to `CORS_ORIGINS` in `.env`.

---

### Windows: "An Application Control policy has blocked this file"

Windows Smart App Control can block the compiled parts of two Python packages.
The app works without them:

```powershell
cd backend
.venv\Scripts\python -m pip uninstall -y sqlalchemy
$env:DISABLE_SQLALCHEMY_CEXT = "1"; .venv\Scripts\python -m pip install --no-binary sqlalchemy SQLAlchemy==2.1.9
```

and set `POSTGRES_DRIVER=pg8000` in `.env` (a pure-Python database driver).

---

## Tests

Tests use a separate database (`TEST_POSTGRES_DB`, wiped on every run).

```powershell
docker exec ledgerly-postgres createdb -U ledgerly ledgerly_test
cd backend
.venv\Scripts\python -m pytest
```

Frontend type check: `npm run typecheck` (inside `frontend/`).

### Local test account

The local development database has a sample company created during setup:
email `demo@example.com`, password `demo-pass-2026`. It exists only in your local
Docker database - change or delete it freely.

---

## Daily job

Once a day, the app creates due recurring transactions, adds late fees and emails
overdue reminders (late fees and reminders only when turned on in **Settings → Sales**).
Schedule this command once a day (Windows Task Scheduler or cron), from the `backend` folder:

```powershell
.venv\Scripts\python -m app.scripts.run_daily_jobs
```

Each step can also be run by hand: **Run due** on the Recurring transactions page,
and **Apply late fees** / **Send reminders** on the Invoices page.

---

## Database changes

After editing a model in `backend/app/models/`:

```powershell
cd backend
.venv\Scripts\alembic revision --autogenerate -m "describe the change"
.venv\Scripts\alembic upgrade head
```
