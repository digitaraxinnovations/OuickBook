/**
 * Creates every service once and shares it with the whole app.
 * Pages import services from here - they never build ApiClient themselves.
 */
import { appConfig } from "@/config/app.config";
import { ApiClient } from "@/lib/api-client";
import { TokenStorage } from "@/lib/token-storage";
import {
  AccountInput,
  ContactInput,
  ExpenseInput,
  JournalEntryInput,
  ProductInput,
} from "@/types/inputs";
import { Account, Customer, Expense, JournalEntry, Payment, Product, Vendor } from "@/types/models";
import { AuthService } from "./auth.service";
import { InvoiceService } from "./invoice.service";
import { RecurringService } from "./recurring.service";
import { ReportService } from "./report.service";
import { ResourceService } from "./resource.service";

const tokenStorage = new TokenStorage(appConfig.tokenStorageKey);
const api = new ApiClient(appConfig.apiBaseUrl, tokenStorage);

export const authService = new AuthService(api, tokenStorage);
export const accountService = new ResourceService<Account, AccountInput>(api, "/accounts");
export const customerService = new ResourceService<Customer, ContactInput>(api, "/customers");
export const vendorService = new ResourceService<Vendor, ContactInput>(api, "/vendors");
export const productService = new ResourceService<Product, ProductInput>(api, "/products");
export const invoiceService = new InvoiceService(api, "/invoices");
export const paymentService = new ResourceService<Payment, never>(api, "/payments");
export const expenseService = new ResourceService<Expense, ExpenseInput>(api, "/expenses");
export const journalService = new ResourceService<JournalEntry, JournalEntryInput>(api, "/journal-entries");
export const reportService = new ReportService(api);
export const recurringService = new RecurringService(api, "/recurring");
