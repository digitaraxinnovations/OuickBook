# Ledgerly – Full Feature Roadmap (QuickBooks Online parity)

Status: [x] done · [~] in progress · [ ] planned
Items marked (EXT) need an outside service/account (bank data, card processor, tax authority, email/SMS provider).

## Phase 1 – Core accounting (done)
- [x] Sign up / sign in, company profile, JWT auth
- [x] Chart of accounts (types, detail types, sub-accounts, codes, activate/deactivate)
- [x] Double-entry general ledger, manual journal entries, recurring journal entries
- [x] Customers, vendors, products & services
- [x] Invoices, receive payment, void
- [x] Expenses
- [x] Reports: Profit & Loss, Balance Sheet, Trial Balance (+ A/R Aging)
- [x] Dashboard (income, expenses, profit, open/overdue invoices, bank balances)

## Phase 2 – Sales (Get paid) (done)
- [x] Estimates/quotes → convert to invoice; estimate status (pending/accepted/rejected/closed)
- [x] Sales receipts, credit memos, refund receipts, delayed charges/credits
- [x] Receive payment across multiple invoices, apply credits, partial payments, overpayments
- [x] Bank deposits (from Undeposited Funds, plus extra deposit lines)
- [x] Recurring invoices and recurring sales receipts
- [x] Invoice templates/customization (3 styles, accent color, footer), logo, PDF export, print
- [x] Email invoices/estimates/statements, reminders for overdue invoices — EXT: `EMAIL_PROVIDER=log` records to the Email log; `smtp` sends via SMTP settings
- [x] Customer statements (balance forward, open item, transaction); customer "view invoice" link
- [~] Pay-now on the customer link — EXT: `PaymentProcessor` interface ready, `PAYMENT_PROVIDER=none` until a processor (e.g. Stripe) is plugged in
- [x] Discounts (% or amount), shipping, deposits on invoices; progress invoicing (% of estimate)
- [x] Payment terms list (customer default terms); late fees (fixed or %, grace days)

## Phase 3 – Expenses & bills (Pay bills) (done)
- [x] Bills (vendor terms → due date), pay bills (single vendor or batch, one payment per vendor), vendor credits, bill payments by check/bank/card, delete payment
- [x] Checks (write, print later, print batch on check stock with amount in words, reprint), check numbering per bank account
- [x] Purchase orders → convert to bill (voiding the bill re-opens the order), close order
- [x] Recurring bills and expenses
- [x] Receipt upload inbox → create expense with receipt attached; attachments on expenses, bills, vendor credits, POs — automatic reading of receipt images (OCR) is EXT and not included
- [x] Mileage tracking (business/personal trips, rate per mile, yearly deduction)
- [x] 1099 contractors (vendor flag + tax ID, account → 1099 box) and 1099 summary report (card payments excluded, threshold in config)
- [x] Also: Accounts Payable Aging report, billable-to-customer on expense/bill lines, void expenses, vendor detail page, bills on dashboard

## Phase 4 – Banking (done)
- [x] Bank and credit card accounts, transfers (incl. paying the card), credit card credits
- [x] CSV / OFX / QFX / QBO statement import with duplicate detection and CSV column mapping
- [~] Live bank feeds — EXT: `BankFeedProvider` interface + "Update from bank" button ready, `BANK_FEED_PROVIDER=none` until a provider (e.g. Plaid) is plugged in
- [x] For-review queue: match to existing transactions, add (expense / deposit / transfer / card credit), split, exclude, undo
- [x] Bank rules (description / amount conditions, all/any, money in/out, per account, priority, auto-add)
- [x] Reconciliation (statement balance, tick items, difference, save for later, finish) with reconciliation report
- [x] Undo reconciliation (latest first), reconciliation discrepancy report (reconciled items voided afterwards)

## Phase 5 – Taxes
- [x] Sales tax: tax rates, agencies, combined rates, taxable items/customers (exempt customers, per-line taxable flag)
- [x] Sales tax liability report, filing periods, record sales tax payments, adjustments
- [x] Tax categories mapping for income tax prep (Schedule C style) + Tax Schedule Summary report
- [~] (EXT) automated tax rate lookup / e-filing - TaxRateProvider interface, TAX_RATE_PROVIDER=none (no provider connected)

## Phase 6 – Inventory & products
- [x] Inventory items (qty on hand, reorder point + low-stock alerts, FIFO cost, stock history), inventory qty adjustments; item lines on bills, expenses, vendor credits, POs
- [x] Cost of goods sold posting (sales, returns, vendor returns, voids); Inventory Valuation Summary + Detail reports
- [x] Bundles, categories, price rules (item / category / all, per customer, date range)
- [x] Product import/export (CSV)

## Phase 7 – Payroll & time
- [x] Employees (hourly / salary), pay schedules (weekly, biweekly, semimonthly, monthly), pay items: earnings, deductions, employee and employer taxes, employer contributions
- [x] Payroll runs (draft → approve → void), paychecks with check numbers, overtime, pay stubs (PDF), payroll liabilities and payments, Payroll Summary report
- [x] Time tracking (weekly timesheets for employees and contractors, billable time → invoice, hours fill in paychecks)
- [~] (EXT) payroll tax calculation, filing, direct deposit - PayrollProvider interface, PAYROLL_PROVIDER=none (taxes are pay items; direct deposit recorded, sent by you)

## Phase 8 – Projects, classes, locations, budgets
- [x] Projects with income, costs, labor cost (from time) and profit; Project Profitability report
- [x] Class and location tracking on invoices, sales forms, expenses, bills and journal entries (per line); P&L by Class / by Location
- [x] Budgets (per account per month, optionally per class or location) and Budget vs Actual
- [x] Tags (with groups) on transactions; P&L by Tag

## Phase 9 – Reports (full library)
- [x] P&L (by month / quarter / year, by customer / vendor, by class / location / tag, comparison), Balance Sheet (comparison, detail)
- [x] Cash flow statement, General ledger, Journal, Transaction list, Account QuickReport (click any account on a report)
- [x] A/R aging summary/detail, open invoices, collections, customer balance summary/detail
- [x] A/P aging summary/detail, unpaid bills, vendor balance summary/detail
- [x] Sales by customer/product, expenses by vendor, inventory valuation
- [~] Sales tax, 1099, payroll reports (done); audit log comes with Phase 10 (audit log of every change)
- [x] Custom date ranges (presets + custom), accrual vs cash basis, filters, saved/custom reports
- [x] Export to PDF / Excel / CSV, scheduled email reports (sent by the daily job through the EMAIL_PROVIDER interface)

## Phase 10 – Company, users & platform
- [ ] Multiple companies per login, company switcher
- [ ] Users, roles & permissions, invite users, accountant access
- [ ] Audit log of every change
- [ ] Settings: company, sales, expenses, payments, advanced (fiscal year, accounting method, closing date with password, multi-currency)
- [ ] Multi-currency with exchange rates (EXT for live rates)
- [ ] Global search, recent transactions, "+ New" quick create menu
- [ ] Attachments on any transaction
- [ ] Import/export (customers, vendors, accounts, products, transactions)
- [ ] Notifications, activity feed
- [ ] Public REST API + webhooks for integrations

## Out of scope / not copied
- Intuit name, logo, colors, and proprietary UI artwork (original branding is used instead)
