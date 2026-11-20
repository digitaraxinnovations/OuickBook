/**
 * Data shapes sent TO the backend when creating or updating records.
 */
import {
  AccountType,
  CreditSource,
  BankRuleDirection,
  ExpenseKind,
  RuleCondition,
  PurchaseDocType,
  TripPurpose,
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
  /** Customers and vendors: default payment terms. */
  terms_id?: number | null;
  /** Customers only: sales tax. */
  tax_exempt?: boolean;
  exemption_reason?: string;
  default_tax_code_id?: number | null;
  /** Vendors only: 1099 contractor details. */
  track_1099?: boolean;
  tax_id?: string;
}

export interface ProductInput {
  name: string;
  sku: string;
  product_type: ProductType;
  description: string;
  sales_price: string;
  income_account_id: number | null;
  is_active: boolean;
  taxable: boolean;
  category_id: number | null;
  purchase_description: string;
  purchase_cost: string;
  expense_account_id: number | null;
  inventory_asset_account_id: number | null;
  cogs_account_id: number | null;
  reorder_point: string | null;
  initial_quantity: string;
  as_of_date: string | null;
  components: { product_id: number; quantity: string }[];
}

export interface AccountInput {
  name: string;
  code: string;
  account_type: AccountType;
  detail_type: string;
  description: string;
  parent_id: number | null;
  box_1099: string | null;
  tax_line: string | null;
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
  taxable: boolean;
}

/** Discount, shipping and sales tax - shared by invoices and other sales forms. */
export interface SalesAmountsInput {
  tax_code_id: number | null;
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
  account_id: number | null;
  product_id: number | null;
  quantity: string;
  description: string;
  amount: string;
  customer_id: number | null;
}

export interface ExpenseInput {
  kind: ExpenseKind;
  check_number: string;
  print_later: boolean;
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

export interface PurchaseLineInput {
  account_id: number | null;
  product_id: number | null;
  description: string;
  quantity: string;
  rate: string;
  customer_id: number | null;
}

export interface PurchaseDocumentInput {
  doc_type: PurchaseDocType;
  vendor_id: number;
  doc_date: string;
  due_date: string;
  terms_id: number | null;
  doc_number: string;
  memo: string;
  lines: PurchaseLineInput[];
}

export interface BillPaymentInput {
  vendor_id: number;
  payment_date: string;
  payment_account_id: number;
  payment_method: PaymentMethod;
  check_number: string;
  print_later: boolean;
  memo: string;
  applications: { bill_id: number; amount: string }[];
  credits: { vendor_credit_id: number; amount: string }[];
}

export interface BatchBillPaymentInput {
  payment_date: string;
  payment_account_id: number;
  payment_method: PaymentMethod;
  print_later: boolean;
  bills: { bill_id: number; amount: string }[];
}

export interface TripInput {
  trip_date: string;
  vehicle: string;
  start_location: string;
  end_location: string;
  miles: string;
  purpose: TripPurpose;
  notes: string;
}

export interface TransferInput {
  transfer_date: string;
  from_account_id: number;
  to_account_id: number;
  amount: string;
  memo: string;
}

export interface StatementImportInput {
  account_id: number;
  filename: string;
  content: string;
  date_column: string;
  description_column: string;
  amount_column: string;
  debit_column: string;
  credit_column: string;
  date_format: string;
  reverse_signs: boolean;
}

export interface AddBankLineInput {
  vendor_id: number | null;
  memo: string;
  lines: { account_id: number; amount: string; description: string }[];
}

export interface BankRuleInput {
  name: string;
  priority: number;
  account_id: number | null;
  direction: BankRuleDirection;
  match_type: "ALL" | "ANY";
  conditions: RuleCondition[];
  category_account_id: number;
  vendor_id: number | null;
  auto_add: boolean;
  is_active: boolean;
}

// ---------- sales tax ----------

export interface TaxAgencyInput {
  name: string;
  filing_frequency: string;
  start_date: string;
  is_active: boolean;
}

export interface TaxRateInput {
  name: string;
  agency_id: number;
  rate: string;
  is_active: boolean;
  create_code: boolean;
}

export interface TaxCodeInput {
  name: string;
  rate_ids: number[];
  is_active: boolean;
}

export interface SalesTaxPaymentInput {
  agency_id: number;
  payment_date: string;
  period_start: string;
  period_end: string;
  amount: string;
  payment_account_id: number;
  memo: string;
}

export interface SalesTaxAdjustmentInput {
  agency_id: number;
  adjustment_date: string;
  amount: string;
  account_id: number;
  reason: string;
}

// ---------- inventory ----------

export interface CategoryInput {
  name: string;
  parent_id: number | null;
}

export interface PriceRuleInput {
  name: string;
  adjustment_percent: string;
  customer_id: number | null;
  category_id: number | null;
  product_id: number | null;
  start_date: string | null;
  end_date: string | null;
  is_active: boolean;
}

export interface InventoryAdjustmentInput {
  adjustment_date: string;
  account_id: number | null;
  memo: string;
  lines: { product_id: number; quantity_change: string }[];
}
