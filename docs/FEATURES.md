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

## Phase 2 – Sales (Get paid)
- [ ] Estimates/quotes → convert to invoice; estimate status (pending/accepted/closed)
- [ ] Sales receipts, credit memos, refund receipts, delayed charges/credits
- [ ] Receive payment across multiple invoices, apply credits, partial payments, overpayments
- [ ] Bank deposits (from Undeposited Funds)
- [ ] Recurring invoices and recurring sales receipts
- [ ] Invoice templates/customization, logo, PDF export, print
- [ ] Email invoices/estimates/statements (EXT: SMTP), reminders for overdue invoices
- [ ] Customer statements; customer portal / pay-now link (EXT: payment processor)
- [ ] Discounts, shipping, deposits on invoices; progress invoicing
- [ ] Payment terms list; late fees

## Phase 3 – Expenses & bills (Pay bills)
- [ ] Bills, pay bills (single/batch), vendor credits, bill payments by check/card
- [ ] Checks (write/print), check numbering
- [ ] Purchase orders → convert to bill
- [ ] Recurring bills and expenses
- [ ] Receipt capture/upload with attachments
- [ ] Mileage tracking
- [ ] 1099 contractors and 1099 reporting

## Phase 4 – Banking
- [ ] Bank and credit card accounts, transfers, credit card credits
- [ ] Bank feeds (EXT: Plaid or similar) + CSV/OFX/QFX import
- [ ] For-review queue: match, categorize, split, exclude
- [ ] Bank rules (auto-categorization)
- [ ] Reconciliation with reconciliation reports
- [ ] Undo reconciliation, reconciliation discrepancy report

## Phase 5 – Taxes
- [ ] Sales tax: tax rates, agencies, combined rates, taxable items/customers
- [ ] Sales tax liability report, file/record sales tax payments, adjustments
- [ ] Tax categories mapping for income tax prep (Schedule C style)
- [ ] (EXT) automated tax rate lookup / e-filing

## Phase 6 – Inventory & products
- [ ] Inventory items (qty on hand, reorder point, FIFO cost), inventory adjustments
- [ ] Cost of goods sold posting; inventory valuation reports
- [ ] Bundles, categories, price rules
- [ ] Product import/export

## Phase 7 – Payroll & time
- [ ] Employees, pay schedules, pay types, deductions
- [ ] Payroll runs, paychecks, payroll liabilities
- [ ] Time tracking (timesheets, billable time → invoice)
- [ ] (EXT) payroll tax calculation, filing, direct deposit

## Phase 8 – Projects, classes, locations, budgets
- [ ] Projects with income/cost/profitability
- [ ] Class and location tracking on every transaction
- [ ] Budgets and Budget vs Actual
- [ ] Tags

## Phase 9 – Reports (full library)
- [ ] P&L (by month, by customer, by class/location, comparison), Balance Sheet (comparison, detail)
- [ ] Cash flow statement, General ledger, Journal, Transaction list, Account QuickReport
- [ ] A/R aging summary/detail, open invoices, collections, customer balance
- [ ] A/P aging summary/detail, unpaid bills, vendor balance
- [ ] Sales by customer/product, expenses by vendor, inventory valuation
- [ ] Sales tax, 1099, payroll reports, audit log
- [ ] Custom date ranges, accrual vs cash basis, filters, saved/custom reports
- [ ] Export to PDF / Excel / CSV, scheduled email reports (EXT)

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
