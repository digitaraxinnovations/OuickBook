/**
 * Which menu groups each role sees. The backend enforces the real rules
 * (backend/app/core/permissions.py); this only hides what a role cannot open.
 */
import { UserRole } from "@/types/models";

const EVERYTHING = ["Dashboard", "Projects", "Sales", "Expenses", "Banking", "Payroll", "Taxes", "Accounting", "Reports", "Settings"];

export const VISIBLE_MENU: Record<UserRole, string[]> = {
  ADMIN: EVERYTHING,
  ACCOUNTANT: EVERYTHING,
  STANDARD: EVERYTHING,
  SALES: ["Sales"],
  PURCHASES: ["Expenses"],
  REPORTS_ONLY: ["Dashboard", "Reports"],
  TIME_ONLY: ["Payroll"],
};

/** Roles that may manage users and change settings. */
export const ADMIN_ROLES: UserRole[] = ["ADMIN"];
