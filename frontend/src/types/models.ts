/**
 * Data shapes returned by the backend API.
 * Money values are strings (e.g. "1250.00") to avoid rounding errors.
 */

export type AccountType = "ASSET" | "LIABILITY" | "EQUITY" | "INCOME" | "EXPENSE";
export type InvoiceStatus = "OPEN" | "PARTIALLY_PAID" | "PAID" | "VOID";
export type PaymentMethod = "CASH" | "CHECK" | "CREDIT_CARD" | "BANK_TRANSFER" | "OTHER";
export type ProductType = "SERVICE" | "NON_INVENTORY";

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
  payment_terms_days: number;
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
  full_name: string;
  depth: number;
  balance: string;
}

export type RecurringFrequency = "DAILY" | "WEEKLY" | "MONTHLY" | "YEARLY";
export type RecurringType = "JOURNAL_ENTRY";

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
  open_balance: string;
}

export type Vendor = Contact;

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

export interface InvoiceLine {
  id: number;
  product_id: number | null;
  income_account_id: number;
  description: string | null;
  quantity: string;
  rate: string;
  amount: string;
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
  lines: InvoiceLine[];
}

export interface Payment {
  id: number;
  invoice: { id: number; invoice_number: string };
  customer: ContactSummary;
  payment_date: string;
  amount: string;
  payment_method: PaymentMethod;
  reference_no: string | null;
  deposit_account: AccountSummary;
  memo: string | null;
}

export interface ExpenseLine {
  id: number;
  account: AccountSummary;
  description: string | null;
  amount: string;
}

export interface Expense {
  id: number;
  vendor: ContactSummary | null;
  payment_account: AccountSummary;
  expense_date: string;
  payment_method: PaymentMethod;
  reference_no: string | null;
  memo: string | null;
  total: string;
  lines: ExpenseLine[];
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
}
