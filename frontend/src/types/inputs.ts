/**
 * Data shapes sent TO the backend when creating or updating records.
 */
import { AccountType, PaymentMethod, ProductType, RecurringFrequency, RecurringType } from "./models";

export interface SignupInput {
  full_name: string;
  company_name: string;
  email: string;
  password: string;
}

export interface LoginInput {
  email: string;
  password: string;
}

export interface CompanyInput {
  name: string;
  email: string;
  phone: string;
  address: string;
  payment_terms_days: number;
}

export interface ContactInput {
  display_name: string;
  company_name: string;
  email: string;
  phone: string;
  address: string;
  notes: string;
  is_active: boolean;
}

export interface ProductInput {
  name: string;
  sku: string;
  product_type: ProductType;
  description: string;
  sales_price: string;
  income_account_id: number | null;
  is_active: boolean;
}

export interface AccountInput {
  name: string;
  code: string;
  account_type: AccountType;
  detail_type: string;
  description: string;
  parent_id: number | null;
  is_active: boolean;
}

export interface RecurringScheduleInput {
  name: string;
  transaction_type: RecurringType;
  frequency: RecurringFrequency;
  interval: number;
  start_date: string;
  end_date: string;
  is_active: boolean;
  template: Record<string, unknown>;
}

export interface InvoiceLineInput {
  product_id: number | null;
  description: string;
  quantity: string;
  rate: string;
}

export interface InvoiceInput {
  customer_id: number;
  invoice_date: string;
  due_date: string;
  memo: string;
  lines: InvoiceLineInput[];
}

export interface PaymentInput {
  invoice_id: number;
  payment_date: string;
  amount: string;
  payment_method: PaymentMethod;
  reference_no: string;
  deposit_account_id: number | null;
  memo: string;
}

export interface ExpenseLineInput {
  account_id: number;
  description: string;
  amount: string;
}

export interface ExpenseInput {
  vendor_id: number | null;
  payment_account_id: number;
  expense_date: string;
  payment_method: PaymentMethod;
  reference_no: string;
  memo: string;
  lines: ExpenseLineInput[];
}

export interface JournalLineInput {
  account_id: number;
  description: string;
  debit: string;
  credit: string;
}

export interface JournalEntryInput {
  entry_date: string;
  memo: string;
  lines: JournalLineInput[];
}
