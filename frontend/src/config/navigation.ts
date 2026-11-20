/**
 * Sidebar menu and the "+ New" menu.
 * To add a page to the menu, add one line here - no component changes needed.
 */

export interface NavLink {
  label: string;
  href: string;
}

export interface NavGroup {
  label: string;
  icon: "home" | "projects" | "sales" | "expenses" | "banking" | "payroll" | "taxes" | "accounting" | "reports" | "settings";
  href?: string;
  links?: NavLink[];
}

export const sidebarMenu: NavGroup[] = [
  { label: "Dashboard", icon: "home", href: "/dashboard" },
  { label: "Projects", icon: "projects", href: "/projects" },
  {
    label: "Sales",
    icon: "sales",
    links: [
      { label: "Invoices", href: "/sales/invoices" },
      { label: "Estimates", href: "/sales/forms/estimates" },
      { label: "Sales receipts", href: "/sales/forms/sales-receipts" },
      { label: "Payments received", href: "/sales/payments" },
      { label: "Credit memos", href: "/sales/forms/credit-memos" },
      { label: "Refund receipts", href: "/sales/forms/refund-receipts" },
      { label: "Delayed charges", href: "/sales/forms/delayed-charges" },
      { label: "Delayed credits", href: "/sales/forms/delayed-credits" },
      { label: "Customers", href: "/sales/customers" },
      { label: "Products & services", href: "/sales/products" },
      { label: "Inventory adjustments", href: "/sales/inventory-adjustments" },
      { label: "Categories & price rules", href: "/sales/price-rules" },
    ],
  },
  {
    label: "Expenses",
    icon: "expenses",
    links: [
      { label: "Expenses & checks", href: "/expenses" },
      { label: "Bills", href: "/expenses/forms/bills" },
      { label: "Pay bills", href: "/expenses/pay-bills" },
      { label: "Bill payments", href: "/expenses/bill-payments" },
      { label: "Vendor credits", href: "/expenses/forms/vendor-credits" },
      { label: "Purchase orders", href: "/expenses/forms/purchase-orders" },
      { label: "Print checks", href: "/expenses/print-checks" },
      { label: "Receipts", href: "/expenses/receipts" },
      { label: "Mileage", href: "/expenses/mileage" },
      { label: "Vendors", href: "/expenses/vendors" },
    ],
  },
  {
    label: "Banking",
    icon: "banking",
    links: [
      { label: "Bank transactions", href: "/banking" },
      { label: "Reconcile", href: "/banking/reconcile" },
      { label: "Bank rules", href: "/banking/rules" },
      { label: "Transfers", href: "/banking/transfers" },
      { label: "Bank deposits", href: "/banking/deposits" },
    ],
  },
  {
    label: "Payroll",
    icon: "payroll",
    links: [
      { label: "Employees", href: "/payroll/employees" },
      { label: "Run payroll", href: "/payroll/runs" },
      { label: "Payroll liabilities", href: "/payroll/liabilities" },
      { label: "Time", href: "/payroll/time" },
      { label: "Payroll settings", href: "/payroll/settings" },
    ],
  },
  {
    label: "Taxes",
    icon: "taxes",
    links: [
      { label: "Sales tax", href: "/taxes" },
      { label: "Sales tax settings", href: "/taxes/settings" },
    ],
  },
  {
    label: "Accounting",
    icon: "accounting",
    links: [
      { label: "Chart of accounts", href: "/accounting/chart-of-accounts" },
      { label: "Journal entries", href: "/accounting/journal-entries" },
      { label: "Recurring transactions", href: "/accounting/recurring" },
      { label: "Budgets", href: "/accounting/budgets" },
      { label: "Classes, locations & tags", href: "/accounting/tracking" },
    ],
  },
  { label: "Reports", icon: "reports", href: "/reports" },
  { label: "Settings", icon: "settings", href: "/settings" },
];

/** The "+ New" menu, in columns like the original product. */
export const newMenuGroups: { title: string; links: NavLink[] }[] = [
  {
    title: "Customers",
    links: [
      { label: "Invoice", href: "/sales/invoices/new" },
      { label: "Receive payment", href: "/sales/payments/new" },
      { label: "Estimate", href: "/sales/forms/estimates/new" },
      { label: "Sales receipt", href: "/sales/forms/sales-receipts/new" },
      { label: "Credit memo", href: "/sales/forms/credit-memos/new" },
      { label: "Refund receipt", href: "/sales/forms/refund-receipts/new" },
      { label: "Delayed charge", href: "/sales/forms/delayed-charges/new" },
      { label: "Delayed credit", href: "/sales/forms/delayed-credits/new" },
    ],
  },
  {
    title: "Vendors",
    links: [
      { label: "Expense", href: "/expenses/new" },
      { label: "Check", href: "/expenses/new?kind=CHECK" },
      { label: "Bill", href: "/expenses/forms/bills/new" },
      { label: "Pay bills", href: "/expenses/pay-bills" },
      { label: "Purchase order", href: "/expenses/forms/purchase-orders/new" },
      { label: "Vendor credit", href: "/expenses/forms/vendor-credits/new" },
      { label: "Upload receipt", href: "/expenses/receipts" },
      { label: "Add trip", href: "/expenses/mileage?new=1" },
    ],
  },
  {
    title: "Other",
    links: [
      { label: "Bank deposit", href: "/banking/deposits/new" },
      { label: "Transfer", href: "/banking/transfers?new=1" },
      { label: "Credit card credit", href: "/expenses/new?kind=CARD_CREDIT" },
      { label: "Journal entry", href: "/accounting/journal-entries/new" },
      { label: "Pay sales tax", href: "/taxes?pay=1" },
      { label: "Run payroll", href: "/payroll/runs?new=1" },
      { label: "Weekly timesheet", href: "/payroll/time" },
      { label: "Customer", href: "/sales/customers?new=1" },
      { label: "Project", href: "/projects?new=1" },
      { label: "Vendor", href: "/expenses/vendors?new=1" },
      { label: "Product or service", href: "/sales/products?new=1" },
      { label: "Inventory qty adjustment", href: "/sales/inventory-adjustments?new=1" },
    ],
  },
];
