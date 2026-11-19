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
  icon: "home" | "sales" | "expenses" | "accounting" | "reports" | "settings";
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
      { label: "Payments received", href: "/sales/payments" },
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

export const newMenu: NavLink[] = [
  { label: "Invoice", href: "/sales/invoices/new" },
  { label: "Expense", href: "/expenses/new" },
  { label: "Journal entry", href: "/accounting/journal-entries/new" },
  { label: "Customer", href: "/sales/customers?new=1" },
  { label: "Vendor", href: "/expenses/vendors?new=1" },
  { label: "Product or service", href: "/sales/products?new=1" },
];
