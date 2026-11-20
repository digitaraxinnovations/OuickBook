/**
 * Data shapes returned by the backend API.
 * Money values are strings (e.g. "1250.00") to avoid rounding errors.
 */

export type AccountType = "ASSET" | "LIABILITY" | "EQUITY" | "INCOME" | "EXPENSE";
export type InvoiceStatus = "OPEN" | "PARTIALLY_PAID" | "PAID" | "VOID";
export type PaymentMethod = "CASH" | "CHECK" | "CREDIT_CARD" | "BANK_TRANSFER" | "OTHER";
export type ProductType = "SERVICE" | "NON_INVENTORY";
export type DiscountType = "PERCENT" | "AMOUNT";
export type SalesDocType = "ESTIMATE" | "SALES_RECEIPT" | "CREDIT_MEMO" | "REFUND_RECEIPT" | "DELAYED_CHARGE" | "DELAYED_CREDIT";
export type SalesDocStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "OPEN" | "CLOSED" | "PAID" | "VOID";
export type CreditSource = "CREDIT_MEMO" | "PAYMENT";
export type DepositLineSource = "PAYMENT" | "SALES_RECEIPT" | "OTHER";
export type StatementType = "BALANCE_FORWARD" | "OPEN_ITEM" | "TRANSACTION";
export type ExpenseKind = "EXPENSE" | "CHECK";
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
  terms_id: number | null;
  open_balance: string;
}

export interface Vendor extends Contact {
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
}

export interface SalesLine {
  id: number;
  product_id: number | null;
  income_account_id: number;
  description: string | null;
  quantity: string;
  rate: string;
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

export interface Invoice extends InvoiceSummary {
  memo: string | null;
  terms_id: number | null;
  subtotal: string;
  discount_type: DiscountType | null;
  discount_value: string;
  discount_amount: string;
  shipping_amount: string;
  estimate_id: number | null;
  late_fee_applied_on: string | null;
  last_emailed_at: string | null;
  lines: SalesLine[];
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

export interface SalesDocument extends SalesDocumentSummary {
  memo: string | null;
  subtotal: string;
  discount_type: DiscountType | null;
  discount_value: string;
  discount_amount: string;
  shipping_amount: string;
  money_account: AccountSummary | null;
  payment_method: PaymentMethod | null;
  reference_no: string | null;
  invoice_id: number | null;
  deposit_id: number | null;
  last_emailed_at: string | null;
  lines: SalesLine[];
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
  total: string;
  amount_paid: string;
  balance_due: string;
  memo: string | null;
  currency: string;
  lines: { description: string | null; quantity: string; rate: string; amount: string }[];
  online_payment_enabled: boolean;
}

export interface ExpenseLine {
  id: number;
  account: AccountSummary;
  description: string | null;
  amount: string;
  customer_id: number | null;
}

export interface Expense {
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
}

export interface PurchaseLine {
  id: number;
  account: AccountSummary;
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
}

export interface PurchaseDocument extends PurchaseDocumentSummary {
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
}

export interface ReportSection {
  title: string;
  rows: ReportRow[];
  total: string;
}

export interface ReportResult {
  key: string;
  title: string;
  start_date: string | null;
  end_date: string;
  sections: ReportSection[];
  summary: ReportRow[];
}

export interface ReportInfo {
  key: string;
  title: string;
  description: string;
  uses_start_date: boolean;
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
