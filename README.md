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
- **Banking** - statement import (CSV / OFX / QFX), review queue (match, add, split, exclude),
  bank rules, transfers, credit card credits, reconciliation with reports, bank deposits.
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
| Live bank feeds | `BANK_FEED_PROVIDER` | `none`: upload statements instead. Add a class in `backend/app/integrations/bank_feeds.py` |
| Sales tax rate lookup / e-filing | `TAX_RATE_PROVIDER` | `none`: enter rates by hand on Taxes → Sales tax settings. Add a class in `backend/app/integrations/tax_rates.py` |
| Payroll taxes, filing, direct deposit | `PAYROLL_PROVIDER` | `none`: set up taxes as pay items; direct deposit pay is recorded but sent by you. Add a class in `backend/app/integrations/payroll.py` |
| Live exchange rates | `EXCHANGE_RATE_PROVIDER` (+ `EXCHANGE_RATE_API_KEY`) | `none`: type rates on Settings → Currencies. Add a class in `backend/app/integrations/exchange_rates.py` |
| Webhook delivery | `WEBHOOK_DELIVERY` = `log` or `http` (+ `WEBHOOK_TIMEOUT_SECONDS`) | `log`: deliveries are recorded in Settings → API & webhooks but not sent |
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

## Running everything in Docker

Requirements: Docker Desktop only.

```powershell
Copy-Item .env.example .env
```

Edit `.env`: set `POSTGRES_PASSWORD` and a long random `JWT_SECRET_KEY`. Then:

```powershell
docker compose up -d --build
```

Open http://localhost:3000 and create an account.

| Container | What it does |
|---|---|
| `ledgerly-postgres` | PostgreSQL 17; data is kept in the `postgres_data` volume |
| `ledgerly-backend` | The API on http://localhost:8000 (docs at `/docs`); applies database migrations every time it starts |
| `ledgerly-scheduler` | Runs the daily job (recurring transactions, late fees, reminders, scheduled reports) every `DAILY_JOBS_INTERVAL_SECONDS` |
| `ledgerly-frontend` | The web app on http://localhost:3000 |

Docker settings are in the `# Docker` section of `.env`: the ports (`BACKEND_PORT`, `FRONTEND_PORT`), `PUBLIC_API_URL`, `API_WORKERS` and the scheduler interval.
`PUBLIC_API_URL` is the API address the browser uses, so it is built into the web app - after changing it run `docker compose build frontend`.
`CORS_ORIGINS` and `PUBLIC_APP_URL` must include the web app's address (http://localhost:3000 by default).
Set `TZ` to the business's time zone (e.g. `America/New_York`): containers run on UTC otherwise, so "today" -
for due dates, reports and the daily job - would change at UTC midnight.

Useful commands:

```powershell
docker compose logs -f backend
```

```powershell
docker compose down
```

`docker compose down -v` also deletes the database.

**Hosting on a server:** set `PUBLIC_API_URL`, `CORS_ORIGINS` and `PUBLIC_APP_URL` to your real addresses, use strong passwords, and put a web server with HTTPS (Caddy, Nginx, or your host's load balancer) in front of ports 3000 and 8000.

---

## Running it locally (without Docker for the code)

Requirements: Docker Desktop, Python 3.15, Node.js 20+.

**1. Configuration** (first time only)

```powershell
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env.local
```

Then edit `.env`: set `POSTGRES_PASSWORD` and a long random `JWT_SECRET_KEY`.

**2. Database** (only the database container)

```powershell
docker compose up -d postgres
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

### End-to-end tour and demo video

`frontend/e2e/` holds a Playwright tour of the whole app, in 13 chapters: sign-up and setup,
customers and products, sales tax, selling, expenses, banking, payroll, projects and budgets,
accounting, sales tax filing, reports, multicurrency, and running the company. It creates a new
company on every run, uses the app the way a person would, and checks each result.

With the app running (for example `docker compose up -d`), inside `frontend/`:

```powershell
npm run e2e
```

That runs the tour fast, as a test (about 3-4 minutes). To record the narrated demo video instead:

```powershell
npm run demo:video
```

It runs slowly with on-screen captions and saves `demo-video/ledgerly-demo.webm`, a chapter list
(`ledgerly-demo-chapters.txt`) and subtitles (`ledgerly-demo.vtt`). Settings - the app address
(`E2E_BASE_URL`, `E2E_API_URL`), speed, screen size - are in `frontend/e2e/demo.config.ts`; the
demo company's names and amounts are in `frontend/e2e/demo-data.ts`.

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
