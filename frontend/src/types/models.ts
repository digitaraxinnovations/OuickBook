/**
 * Data shapes returned by the backend API.
 * Money values are strings (e.g. "1250.00") to avoid rounding errors.
 */

export type AccountType = "ASSET" | "LIABILITY" | "EQUITY" | "INCOME" | "EXPENSE";
export type InvoiceStatus = "OPEN" | "PARTIALLY_PAID" | "PAID" | "VOID";
export type PaymentMethod = "CASH" | "CHECK" | "CREDIT_CARD" | "BANK_TRANSFER" | "OTHER";
export type ProductType = "SERVICE" | "NON_INVENTORY" | "INVENTORY" | "BUNDLE";
export type DiscountType = "PERCENT" | "AMOUNT";
export type SalesDocType = "ESTIMATE" | "SALES_RECEIPT" | "CREDIT_MEMO" | "REFUND_RECEIPT" | "DELAYED_CHARGE" | "DELAYED_CREDIT";
export type SalesDocStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "OPEN" | "CLOSED" | "PAID" | "VOID";
export type CreditSource = "CREDIT_MEMO" | "PAYMENT";
export type DepositLineSource = "PAYMENT" | "SALES_RECEIPT" | "OTHER";
export type StatementType = "BALANCE_FORWARD" | "OPEN_ITEM" | "TRANSACTION";
export type ExpenseKind = "EXPENSE" | "CHECK" | "CARD_CREDIT";
export type PurchaseDocType = "BILL" | "VENDOR_CREDIT" | "PURCHASE_ORDER";
export type PurchaseDocStatus = "OPEN" | "PARTIALLY_PAID" | "PAID" | "CLOSED" | "VOID";
export type TripPurpose = "BUSINESS" | "PERSONAL";

export interface User {
  id: number;
  email: string;
  full_name: string;
  company_id: number;
}

export interface Company {
  id: number;
  name: string;
  currency: string;
  email: string | null;
  phone: string | null;
  address: string | null;
  website: string | null;
  payment_terms_days: number;
  invoice_template: string;
  invoice_accent_color: string;
}

export interface SalesSettings {
  invoice_template: string;
  invoice_accent_color: string;
  invoice_footer: string | null;
  late_fee_enabled: boolean;
  late_fee_type: "FIXED" | "PERCENT";
  late_fee_amount: string;
  late_fee_grace_days: number;
  reminders_enabled: boolean;
  reminder_days_after_due: number;
}

export interface PaymentTerm {
  id: number;
  name: string;
  due_days: number;
  is_active: boolean;
}

export interface AccountSummary {
  id: number;
  name: string;
  account_type: AccountType;
}

export interface Account extends AccountSummary {
  code: string | null;
  detail_type: string;
  description: string | null;
  system_key: string | null;
  is_active: boolean;
  parent_id: number | null;
  box_1099: string | null;
  tax_line: string | null;
  full_name: string;
  depth: number;
  balance: string;
}

export interface ContactSummary {
  id: number;
  display_name: string;
  email: string | null;
}

export interface Contact {
  id: number;
  display_name: string;
  company_name: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  notes: string | null;
  is_active: boolean;
}

export interface Customer extends Contact {
  currency_code: string | null;
  terms_id: number | null;
  tax_exempt: boolean;
  exemption_reason: string | null;
  default_tax_code_id: number | null;
  open_balance: string;
}

export interface Vendor extends Contact {
  currency_code: string | null;
  terms_id: number | null;
  track_1099: boolean;
  tax_id: string | null;
  open_balance: string;
}

export interface Product {
  id: number;
  name: string;
  sku: string | null;
  product_type: ProductType;
  description: string | null;
  sales_price: string;
  income_account: AccountSummary;
  is_active: boolean;
  taxable: boolean;
  category: { id: number; name: string } | null;
  purchase_description: string | null;
  purchase_cost: string;
  expense_account_id: number | null;
  inventory_asset_account_id: number | null;
  cogs_account_id: number | null;
  quantity_on_hand: string;
  reorder_point: string | null;
  is_low_stock: boolean;
  components: { product_id: number; name: string; quantity: string; sales_price: string }[];
}

export interface SalesLine {
  id: number;
  product_id: number | null;
  income_account_id: number;
  description: string | null;
  quantity: string;
  rate: string;
  taxable: boolean;
  amount: string;
  is_late_fee: boolean;
}

export interface InvoiceSummary {
  id: number;
  invoice_number: string;
  customer: ContactSummary;
  invoice_date: string;
  due_date: string;
  status: InvoiceStatus;
  total: string;
  amount_paid: string;
  balance_due: string;
  is_overdue: boolean;
}

export interface Invoice extends TrackingFields, InvoiceSummary {
  memo: string | null;
  terms_id: number | null;
  subtotal: string;
  discount_type: DiscountType | null;
  discount_value: string;
  discount_amount: string;
  shipping_amount: string;
  tax_code_id: number | null;
  tax_amount: string;
  estimate_id: number | null;
  late_fee_applied_on: string | null;
  last_emailed_at: string | null;
  lines: SalesLine[];
  currency_code: string | null;
  exchange_rate: string;
}

export interface InvoicePayment {
  payment_id: number;
  payment_date: string;
  payment_method: PaymentMethod;
  reference_no: string | null;
  deposit_account: AccountSummary;
  amount: string;
}

export interface SalesDocumentSummary {
  id: number;
  doc_type: SalesDocType;
  doc_number: string;
  customer: ContactSummary;
  doc_date: string;
  expiration_date: string | null;
  status: SalesDocStatus;
  total: string;
  amount_applied: string;
  remaining: string;
}

export interface SalesDocument extends TrackingFields, SalesDocumentSummary {
  memo: string | null;
  subtotal: string;
  discount_type: DiscountType | null;
  discount_value: string;
  discount_amount: string;
  shipping_amount: string;
  tax_code_id: number | null;
  tax_amount: string;
  money_account: AccountSummary | null;
  payment_method: PaymentMethod | null;
  reference_no: string | null;
  invoice_id: number | null;
  deposit_id: number | null;
  last_emailed_at: string | null;
  lines: SalesLine[];
  currency_code: string | null;
  exchange_rate: string;
}

export interface Payment {
  id: number;
  customer: ContactSummary;
  payment_date: string;
  amount: string;
  unapplied_amount: string;
  payment_method: PaymentMethod;
  reference_no: string | null;
  deposit_account: AccountSummary;
  memo: string | null;
  deposit_id: number | null;
  applications: { invoice: { id: number; invoice_number: string }; amount: string }[];
  credits_used: { source_type: CreditSource; source_id: number; amount: string }[];
  currency_code?: string | null;
  exchange_rate?: string;
}

export interface CustomerCredit {
  source_type: CreditSource;
  source_id: number;
  reference: string;
  credit_date: string;
  remaining: string;
}

export interface UndepositedItem {
  source_type: DepositLineSource;
  source_id: number;
  item_date: string;
  customer_name: string;
  reference: string;
  amount: string;
}

export interface Deposit {
  id: number;
  deposit_date: string;
  bank_account: AccountSummary;
  memo: string | null;
  total: string;
  lines: { id: number; source_type: DepositLineSource; source_id: number | null; account: AccountSummary; description: string | null; amount: string }[];
}

export interface StatementLine {
  line_date: string;
  transaction_type: string;
  reference: string;
  amount: string;
  balance: string;
}

export interface Statement {
  customer_id: number;
  customer_name: string;
  customer_email: string | null;
  customer_address: string | null;
  statement_type: StatementType;
  start_date: string | null;
  end_date: string;
  opening_balance: string;
  lines: StatementLine[];
  closing_balance: string;
}

export interface EmailLogEntry {
  id: number;
  sent_at: string;
  to_address: string;
  subject: string;
  body: string;
  attachment_name: string | null;
  related_type: string | null;
  related_id: number | null;
  provider: string;
  status: string;
  error: string | null;
}

export interface BatchResult {
  count: number;
  details: string[];
}

export interface PublicInvoice {
  company_name: string;
  company_email: string | null;
  company_address: string | null;
  accent_color: string;
  logo_data_url: string | null;
  invoice_number: string;
  customer_name: string;
  invoice_date: string;
  due_date: string;
  status: string;
  subtotal: string;
  discount_amount: string;
  shipping_amount: string;
  tax_amount: string;
  total: string;
  amount_paid: string;
  balance_due: string;
  memo: string | null;
  currency: string;
  lines: { description: string | null; quantity: string; rate: string; amount: string }[];
  online_payment_enabled: boolean;
  online_payment_simulated: boolean;
}

export interface ExpenseLine {
  id: number;
  account: AccountSummary;
  product_id: number | null;
  quantity: string;
  description: string | null;
  amount: string;
  customer_id: number | null;
}

export interface Expense extends TrackingFields {
  id: number;
  kind: ExpenseKind;
  vendor: ContactSummary | null;
  payment_account: AccountSummary;
  expense_date: string;
  payment_method: PaymentMethod;
  reference_no: string | null;
  check_number: string | null;
  print_later: boolean;
  memo: string | null;
  total: string;
  is_void: boolean;
  lines: ExpenseLine[];
  currency_code?: string | null;
  exchange_rate?: string;
}

export interface PurchaseLine {
  id: number;
  account: AccountSummary;
  product_id: number | null;
  description: string | null;
  quantity: string;
  rate: string;
  amount: string;
  customer_id: number | null;
}

export interface PurchaseDocumentSummary {
  id: number;
  doc_type: PurchaseDocType;
  doc_number: string | null;
  vendor: ContactSummary;
  doc_date: string;
  due_date: string | null;
  status: PurchaseDocStatus;
  total: string;
  amount_applied: string;
  balance: string;
  is_overdue: boolean;
  currency_code?: string | null;
  exchange_rate?: string;
}

export interface PurchaseDocument extends TrackingFields, PurchaseDocumentSummary {
  memo: string | null;
  terms_id: number | null;
  purchase_order_id: number | null;
  lines: PurchaseLine[];
}

export interface BillPayment {
  id: number;
  vendor: ContactSummary;
  payment_date: string;
  payment_account: AccountSummary;
  payment_method: PaymentMethod;
  check_number: string | null;
  print_later: boolean;
  amount: string;
  memo: string | null;
  applications: { bill: { id: number; doc_number: string | null }; amount: string }[];
  credits_used: { vendor_credit_id: number; amount: string }[];
  currency_code?: string | null;
  exchange_rate?: string;
}

export interface BillPaymentForBill {
  payment_id: number;
  payment_date: string;
  payment_method: PaymentMethod;
  check_number: string | null;
  payment_account: AccountSummary;
  amount: string;
}

export interface CheckToPrint {
  source_type: "EXPENSE" | "BILL_PAYMENT";
  source_id: number;
  check_date: string;
  payee: string;
  bank_account: AccountSummary;
  amount: string;
}

export interface Attachment {
  id: number;
  entity_type: string;
  entity_id: number | null;
  filename: string;
  mime_type: string;
  size_bytes: number;
  note: string | null;
  created_at: string;
}

export interface Trip {
  id: number;
  trip_date: string;
  vehicle: string | null;
  start_location: string | null;
  end_location: string | null;
  miles: string;
  purpose: TripPurpose;
  notes: string | null;
}

export interface MileageSummary {
  year: number;
  business_miles: string;
  personal_miles: string;
  rate: string;
  deduction: string;
}

export interface JournalLine {
  id: number;
  account: AccountSummary;
  description: string | null;
  debit: string;
  credit: string;
}

export interface JournalEntry {
  id: number;
  entry_date: string;
  memo: string | null;
  source_type: string;
  source_id: number | null;
  lines: JournalLine[];
}

export type RecurringFrequency = "DAILY" | "WEEKLY" | "MONTHLY" | "YEARLY";
export type RecurringType = "JOURNAL_ENTRY" | "INVOICE" | "SALES_RECEIPT" | "BILL" | "EXPENSE";

export interface RecurringSchedule {
  id: number;
  name: string;
  transaction_type: RecurringType;
  frequency: RecurringFrequency;
  interval: number;
  start_date: string;
  end_date: string | null;
  next_date: string | null;
  run_count: number;
  last_run_date: string | null;
  is_active: boolean;
  template: Record<string, unknown>;
}

export interface RunDueResult {
  created: { schedule_id: number; schedule_name: string; transaction_type: RecurringType; transaction_id: number; transaction_date: string }[];
}

export interface ReportRow {
  label: string;
  amount: string;
  account_id: number | null;
  /** Text columns of detail reports (see ReportResult.text_columns). */
  cells: string[];
  /** Amount columns of multi-column reports (see ReportResult.columns). */
  values: (string | null)[];
}

export interface ReportSection {
  title: string;
  rows: ReportRow[];
  total: string;
  totals: (string | null)[];
}

export type ColumnKind = "money" | "number" | "percent";

export interface ReportResult {
  key: string;
  title: string;
  start_date: string | null;
  end_date: string;
  sections: ReportSection[];
  summary: ReportRow[];
  columns: string[];
  column_kinds: ColumnKind[];
  text_columns: string[];
  basis: "accrual" | "cash";
  notes: string[];
}

/** Choices on a report. Each report says which ones it supports. */
export interface ReportOptions {
  basis?: string;
  column_by?: string;
  compare?: string | null;
  class_id?: number | null;
  location_id?: number | null;
  customer_id?: number | null;
  vendor_id?: number | null;
  project_id?: number | null;
  account_id?: number | null;
}

export interface ReportInfo {
  key: string;
  title: string;
  description: string;
  uses_start_date: boolean;
  group: string;
  options: string[];
  defaults: Record<string, string>;
}

export interface SavedReport {
  id: number;
  name: string;
  report_key: string;
  date_range: string;
  start_date: string | null;
  end_date: string | null;
  options: ReportOptions;
}

export interface ReportSchedule {
  id: number;
  saved_report_id: number;
  frequency: "DAILY" | "WEEKLY" | "MONTHLY";
  next_send_date: string;
  recipients: string[];
  file_format: "pdf" | "csv" | "xlsx";
  is_active: boolean;
  last_sent_at: string | null;
}

export interface DashboardSummary {
  period_start: string;
  period_end: string;
  income: string;
  expenses: string;
  net_income: string;
  open_invoices_total: string;
  open_invoice_count: number;
  overdue_invoices_total: string;
  overdue_invoice_count: number;
  bank_accounts: { account_id: number; name: string; balance: string }[];
  unpaid_bills_total: string;
  overdue_bills_total: string;
  overdue_bill_count: number;
}

// ---------- banking ----------

export type BankTransactionStatus = "FOR_REVIEW" | "ADDED" | "MATCHED" | "EXCLUDED";
export type BankRuleDirection = "MONEY_IN" | "MONEY_OUT" | "ANY";
export type ReconciliationStatus = "IN_PROGRESS" | "COMPLETED" | "UNDONE";

export interface Transfer {
  id: number;
  transfer_date: string;
  from_account: AccountSummary;
  to_account: AccountSummary;
  amount: string;
  memo: string | null;
  is_void: boolean;
}

export interface BankAccountOverview {
  account: AccountSummary;
  detail_type: string;
  books_balance: string;
  for_review_count: number;
  last_imported: string | null;
  last_reconciled: string | null;
}

export interface BankTransaction {
  id: number;
  account_id: number;
  txn_date: string;
  description: string;
  amount: string;
  source: string;
  status: BankTransactionStatus;
  rule_id: number | null;
  suggested_account: AccountSummary | null;
  suggested_vendor_id: number | null;
  journal_line_id: number | null;
  added_as: string | null;
  added_id: number | null;
}

export interface MatchCandidate {
  journal_line_id: number;
  entry_date: string;
  description: string;
  amount: string;
}

export interface StatementImportResult {
  imported: number;
  duplicates: number;
  auto_added: number;
}

export interface RuleCondition {
  field: "description" | "amount";
  operator: string;
  value: string;
}

export interface BankRule {
  id: number;
  name: string;
  priority: number;
  account_id: number | null;
  direction: BankRuleDirection;
  match_type: "ALL" | "ANY";
  conditions: RuleCondition[];
  category_account: AccountSummary;
  vendor_id: number | null;
  auto_add: boolean;
  is_active: boolean;
}

export interface Reconciliation {
  id: number;
  account: AccountSummary;
  statement_date: string;
  beginning_balance: string;
  ending_balance: string;
  status: ReconciliationStatus;
  completed_at: string | null;
}

export interface ReconcileItem {
  journal_line_id: number;
  entry_date: string;
  transaction_type: string;
  description: string;
  amount: string;
  selected: boolean;
}

export interface ReconciliationWorkspace {
  reconciliation: Reconciliation;
  items: ReconcileItem[];
  cleared_balance: string;
  difference: string;
}

export interface ReconciliationReport {
  reconciliation: Reconciliation;
  cleared_increases: ReconcileItem[];
  cleared_decreases: ReconcileItem[];
  cleared_balance: string;
  uncleared: ReconcileItem[];
  register_balance: string;
}

export interface DiscrepancyItem {
  reconciliation_id: number;
  statement_date: string;
  entry_date: string;
  description: string;
  amount: string;
  changed_on: string;
  change: string;
}

// ---------- sales tax ----------

export type FilingFrequency = "MONTHLY" | "QUARTERLY" | "YEARLY";
export type TaxPeriodStatus = "OPEN" | "DUE" | "PAID" | "NOTHING_DUE";

export interface TaxAgency {
  id: number;
  name: string;
  filing_frequency: FilingFrequency;
  start_date: string;
  liability_account: AccountSummary;
  is_active: boolean;
}

export interface TaxRate {
  id: number;
  name: string;
  agency_id: number;
  rate: string;
  is_active: boolean;
}

export interface TaxCode {
  id: number;
  name: string;
  is_active: boolean;
  total_rate: string;
  components: { tax_rate_id: number; name: string; rate: string; agency_id: number }[];
}

export interface TaxPeriod {
  agency_id: number;
  agency_name: string;
  period_start: string;
  period_end: string;
  tax_collected: string;
  adjustments: string;
  payments: string;
  balance: string;
  status: TaxPeriodStatus;
}

export interface SalesTaxPayment {
  id: number;
  agency_id: number;
  payment_date: string;
  period_start: string;
  period_end: string;
  amount: string;
  payment_account: AccountSummary;
  memo: string | null;
  confirmation_no: string | null;
}

export interface SalesTaxAdjustment {
  id: number;
  agency_id: number;
  adjustment_date: string;
  amount: string;
  account: AccountSummary;
  reason: string;
}

// ---------- inventory ----------

export interface ProductCategory {
  id: number;
  name: string;
  parent_id: number | null;
}

export interface PriceRule {
  id: number;
  name: string;
  adjustment_percent: string;
  customer_id: number | null;
  category_id: number | null;
  product_id: number | null;
  start_date: string | null;
  end_date: string | null;
  is_active: boolean;
}

export interface ProductPrice {
  product_id: number;
  price: string;
  rule_name: string | null;
}

export interface InventoryAdjustment {
  id: number;
  adjustment_number: string;
  adjustment_date: string;
  account: AccountSummary;
  memo: string | null;
  is_void: boolean;
  lines: { product_id: number; quantity_change: string; value_change: string }[];
}

export interface StockMovement {
  id: number;
  movement_date: string;
  source_type: string;
  source_id: number;
  description: string;
  quantity: string;
  value: string;
}

export interface ProductImportResult {
  created: number;
  updated: number;
  errors: string[];
}

// ---------- payroll and time ----------

export type PayFrequency = "WEEKLY" | "BIWEEKLY" | "SEMIMONTHLY" | "MONTHLY";
export type PayType = "HOURLY" | "SALARY";
export type PaycheckMethod = "CHECK" | "DIRECT_DEPOSIT";
export type PayItemKind =
  | "REGULAR"
  | "OVERTIME"
  | "SALARY"
  | "EARNING"
  | "DEDUCTION"
  | "EMPLOYEE_TAX"
  | "EMPLOYER_TAX"
  | "EMPLOYER_CONTRIBUTION";
export type PayCalculation = "FIXED" | "PERCENT";
export type PayrollRunStatus = "DRAFT" | "APPROVED" | "VOID";

export interface PaySchedule {
  id: number;
  name: string;
  frequency: PayFrequency;
  next_period_start: string;
  next_period_end: string;
  next_pay_date: string;
  is_active: boolean;
}

export interface PayItem {
  id: number;
  name: string;
  kind: PayItemKind;
  calculation: PayCalculation;
  default_amount: string;
  expense_account: AccountSummary | null;
  liability_account: AccountSummary | null;
  is_active: boolean;
}

export interface Employee {
  id: number;
  display_name: string;
  email: string | null;
  phone: string | null;
  address: string | null;
  tax_id: string | null;
  hire_date: string | null;
  release_date: string | null;
  pay_schedule_id: number | null;
  pay_type: PayType;
  pay_rate: string;
  default_hours: string;
  payment_method: PaycheckMethod;
  is_active: boolean;
  pay_items: { pay_item_id: number; amount: string }[];
}

export interface PaycheckLine {
  id: number;
  pay_item_id: number | null;
  kind: PayItemKind;
  description: string;
  hours: string | null;
  rate: string | null;
  amount: string;
}

export interface Paycheck {
  id: number;
  employee: { id: number; display_name: string; pay_type: PayType };
  regular_hours: string;
  overtime_hours: string;
  gross_pay: string;
  employee_deductions: string;
  employee_taxes: string;
  net_pay: string;
  employer_cost: string;
  payment_method: PaycheckMethod;
  check_number: string | null;
  deposit_reference: string | null;
  lines: PaycheckLine[];
}

export interface PayrollRunSummary {
  id: number;
  period_start: string;
  period_end: string;
  pay_date: string;
  status: PayrollRunStatus;
  bank_account: AccountSummary;
  total_gross: string;
  total_net: string;
  total_employer_cost: string;
}

export interface PayrollRun extends PayrollRunSummary {
  pay_schedule_id: number | null;
  paychecks: Paycheck[];
}

export interface LiabilityBalance {
  pay_item_id: number;
  name: string;
  kind: PayItemKind;
  accrued: string;
  paid: string;
  balance: string;
}

export interface LiabilityPayment {
  id: number;
  pay_item_id: number;
  payment_date: string;
  amount: string;
  bank_account: AccountSummary;
  memo: string | null;
  is_void: boolean;
}

export interface TimeEntry {
  id: number;
  employee_id: number | null;
  vendor_id: number | null;
  work_date: string;
  hours: string;
  customer_id: number | null;
  product_id: number | null;
  description: string | null;
  billable: boolean;
  bill_rate: string | null;
  invoice_id: number | null;
}

// ---------- classes, locations, projects, tags, budgets ----------

export interface TrackingFields {
  class_id: number | null;
  location_id: number | null;
  project_id: number | null;
  tag_ids: number[];
}

export interface NamedListItem {
  id: number;
  name: string;
  parent_id: number | null;
  is_active: boolean;
}

export interface Tag {
  id: number;
  name: string;
  group_name: string | null;
}

export type ProjectStatus = "IN_PROGRESS" | "COMPLETED" | "CANCELED";

export interface Project {
  id: number;
  name: string;
  customer_id: number;
  status: ProjectStatus;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
}

export interface ProjectSummary {
  project: Project;
  customer: ContactSummary;
  income: string;
  costs: string;
  labor_cost: string;
  labor_hours: string;
  profit: string;
  margin_percent: string | null;
  transactions: { entry_date: string; memo: string | null; account: AccountSummary; amount: string }[];
}

export interface BudgetSummary {
  id: number;
  name: string;
  fiscal_year: number;
  class_id: number | null;
  location_id: number | null;
}

export interface Budget extends BudgetSummary {
  lines: { account_id: number; account_name: string; account_type: string; months: string[] }[];
}

export interface BudgetVsActual {
  budget_id: number;
  name: string;
  start_date: string;
  end_date: string;
  rows: {
    account_id: number;
    account_name: string;
    account_type: string;
    budget: string;
    actual: string;
    difference: string;
    percent_of_budget: string | null;
  }[];
  budget_net_income: string;
  actual_net_income: string;
}

// ---------- companies, users, settings, currencies, search ----------

export type UserRole = "ADMIN" | "STANDARD" | "SALES" | "PURCHASES" | "REPORTS_ONLY" | "TIME_ONLY" | "ACCOUNTANT";

export interface CompanyMembership {
  company_id: number;
  company_name: string;
  role: UserRole;
  is_current: boolean;
}

export interface Member {
  user_id: number;
  full_name: string;
  email: string;
  role: UserRole;
  is_primary_admin: boolean;
  is_active: boolean;
}

export interface Invitation {
  id: number;
  email: string;
  role: UserRole;
  expires_at: string;
  accepted_at: string | null;
}

export interface InvitationInfo {
  company_name: string;
  email: string;
  role: UserRole;
  has_account: boolean;
}

export interface RoleInfo {
  role: UserRole;
  label: string;
}

export interface AuditEntry {
  id: number;
  user_name: string;
  action: "CREATED" | "CHANGED" | "DELETED";
  entity_type: string;
  entity_id: number | null;
  summary: string;
  changes: Record<string, [unknown, unknown]> | null;
  created_at: string;
}

export interface AdvancedSettings {
  fiscal_year_start_month: number;
  accounting_method: "ACCRUAL" | "CASH";
  closing_date: string | null;
  has_closing_password: boolean;
  multicurrency_enabled: boolean;
  currency: string;
  bill_terms_days: number;
}

export interface CurrencyItem {
  id: number;
  code: string;
  name: string;
  latest_rate: string | null;
  latest_rate_date: string | null;
}

export interface ExchangeRateItem {
  id: number;
  currency_code: string;
  rate_date: string;
  rate: string;
}

export interface SearchResult {
  kind: string;
  title: string;
  subtitle: string;
  href: string;
}

export interface RecentTransaction {
  entry_date: string;
  type_label: string;
  number: string;
  name: string;
  amount: string;
  href: string | null;
}

export interface ImportResult {
  created: number;
  updated: number;
  errors: string[];
}

export interface AppNotification {
  kind: string;
  level: "info" | "warning";
  message: string;
  href: string;
}

export interface ApiKeyItem {
  id: number;
  name: string;
  prefix: string;
  last_used_at: string | null;
  is_active: boolean;
}

export interface WebhookItem {
  id: number;
  url: string;
  events: string[];
  secret: string;
  is_active: boolean;
}

export interface WebhookDeliveryItem {
  id: number;
  webhook_id: number;
  event: string;
  status: string;
  response_code: number | null;
  error: string | null;
  created_at: string;
}

/** One outside service (payments, bank feed, sales tax, payroll): which provider is connected. */
export interface IntegrationStatus {
  provider: string;
  enabled: boolean;
  /** The built-in mock provider: it works, but nothing real happens. */
  simulated: boolean;
}

export interface Integrations {
  payments: IntegrationStatus;
  bank_feed: IntegrationStatus;
  tax_rates: IntegrationStatus;
  payroll: IntegrationStatus;
}

export interface FoundTaxRate {
  name: string;
  rate: string;
}

// ---------- customer payment score ----------

export type ScoreRating = "NOT_ENOUGH_HISTORY" | "GOOD" | "WATCH" | "RISKY";

export interface PaymentScore {
  customer_id: number;
  rating: ScoreRating;
  paid_invoices: number;
  late_invoices: number;
  average_days_late: number;
  overdue_invoices: number;
  reason: string;
  suggestion: string;
}
