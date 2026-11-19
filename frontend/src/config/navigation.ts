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
  icon: "home" | "sales" | "expenses" | "banking" | "accounting" | "reports" | "settings";
  href?: string;
  links?: NavLink[];
}

export const sidebarMenu: NavGroup[] = [
  { label: "Dashboard", icon: "home", href: "/dashboard" },
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
    ],
  },
  {
    label: "Expenses",
    icon: "expenses",
    links: [
      { label: "Expenses", href: "/expenses" },
      { label: "Vendors", href: "/expenses/vendors" },
    ],
  },
  {
    label: "Banking",
    icon: "banking",
    links: [{ label: "Bank deposits", href: "/banking/deposits" }],
  },
  {
    label: "Accounting",
    icon: "accounting",
    links: [
      { label: "Chart of accounts", href: "/accounting/chart-of-accounts" },
      { label: "Journal entries", href: "/accounting/journal-entries" },
      { label: "Recurring transactions", href: "/accounting/recurring" },
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
    links: [{ label: "Expense", href: "/expenses/new" }],
  },
  {
    title: "Other",
    links: [
      { label: "Bank deposit", href: "/banking/deposits/new" },
      { label: "Journal entry", href: "/accounting/journal-entries/new" },
      { label: "Customer", href: "/sales/customers?new=1" },
      { label: "Vendor", href: "/expenses/vendors?new=1" },
      { label: "Product or service", href: "/sales/products?new=1" },
    ],
  },
];
