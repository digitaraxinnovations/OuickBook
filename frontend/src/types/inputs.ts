/**
 * Data shapes sent TO the backend when creating or updating records.
 */
import {
  AccountType,
  CreditSource,
  DepositLineSource,
  DiscountType,
  PaymentMethod,
  ProductType,
  RecurringFrequency,
  RecurringType,
  SalesDocType,
  StatementType,
} from "./models";

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
  website: string;
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
  /** Customers only: default payment terms. */
  terms_id?: number | null;
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

export interface PaymentTermInput {
  name: string;
  due_days: number;
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

export interface SalesLineInput {
  product_id: number | null;
  description: string;
  quantity: string;
  rate: string;
}

/** Discount and shipping - shared by invoices and other sales forms. */
export interface SalesAmountsInput {
  discount_type: DiscountType | null;
  discount_value: string;
  shipping_amount: string;
}

export interface InvoiceInput extends SalesAmountsInput {
  customer_id: number;
  invoice_date: string;
  due_date: string;
  terms_id: number | null;
  memo: string;
  lines: SalesLineInput[];
  delayed_document_ids: number[];
  deposit_amount: string;
  deposit_account_id: number | null;
}

export interface SalesDocumentInput extends SalesAmountsInput {
  doc_type: SalesDocType;
  customer_id: number;
  doc_date: string;
  expiration_date: string;
  memo: string;
  lines: SalesLineInput[];
  money_account_id: number | null;
  payment_method: PaymentMethod | null;
  reference_no: string;
}

export interface PaymentInput {
  customer_id: number;
  payment_date: string;
  amount: string;
  payment_method: PaymentMethod;
  reference_no: string;
  deposit_account_id: number | null;
  memo: string;
  applications: { invoice_id: number; amount: string }[];
  credits: { source_type: CreditSource; source_id: number; amount: string }[];
}

export interface DepositInput {
  deposit_date: string;
  bank_account_id: number;
  memo: string;
  items: { source_type: DepositLineSource; source_id: number }[];
  other_lines: { account_id: number; description: string; amount: string }[];
}

export interface EmailInput {
  to: string;
  subject: string;
  message: string;
}

export interface StatementEmailInput extends EmailInput {
  statement_type: StatementType;
  start_date: string;
  end_date: string;
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
