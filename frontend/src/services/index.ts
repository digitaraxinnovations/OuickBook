/**
 * Creates every service once and shares it with the whole app.
 * Pages import services from here - they never build ApiClient themselves.
 */
import { appConfig } from "@/config/app.config";
import { ApiClient } from "@/lib/api-client";
import { TokenStorage } from "@/lib/token-storage";
import { AccountInput, ContactInput, JournalEntryInput, ProductInput } from "@/types/inputs";
import { Account, JournalEntry, Product, Vendor } from "@/types/models";
import { AuthService } from "./auth.service";
import { InvoiceService } from "./invoice.service";
import {
  AttachmentService,
  BillPaymentService,
  CheckService,
  ExpenseService,
  MileageService,
  PurchaseDocumentService,
} from "./purchase.services";
import { RecurringService } from "./recurring.service";
import { ReportService } from "./report.service";
import { ResourceService } from "./resource.service";
import {
  CompanySettingsService,
  CustomerService,
  DepositService,
  PaymentService,
  PortalService,
  SalesDocumentService,
  TermsService,
} from "./sales.services";

/** Chart of accounts, plus the list of 1099 boxes. */
class AccountService extends ResourceService<Account, AccountInput> {
  boxes1099(): Promise<Record<string, string>> {
    return this.api.get<Record<string, string>>(this.path + "/1099-boxes");
  }
}

const tokenStorage = new TokenStorage(appConfig.tokenStorageKey);
const api = new ApiClient(appConfig.apiBaseUrl, tokenStorage);

export const authService = new AuthService(api, tokenStorage);
export const accountService = new AccountService(api, "/accounts");
export const customerService = new CustomerService(api, "/customers");
export const vendorService = new ResourceService<Vendor, ContactInput>(api, "/vendors");
export const productService = new ResourceService<Product, ProductInput>(api, "/products");
export const termsService = new TermsService(api, "/terms");
export const invoiceService = new InvoiceService(api, "/invoices");
export const salesDocumentService = new SalesDocumentService(api, "/sales-documents");
export const paymentService = new PaymentService(api, "/payments");
export const depositService = new DepositService(api, "/deposits");
export const expenseService = new ExpenseService(api, "/expenses");
export const purchaseService = new PurchaseDocumentService(api, "/purchase-documents");
export const billPaymentService = new BillPaymentService(api, "/bill-payments");
export const checkService = new CheckService(api);
export const attachmentService = new AttachmentService(api);
export const mileageService = new MileageService(api);
export const journalService = new ResourceService<JournalEntry, JournalEntryInput>(api, "/journal-entries");
export const reportService = new ReportService(api);
export const recurringService = new RecurringService(api, "/recurring");
export const companySettingsService = new CompanySettingsService(api);
export const portalService = new PortalService(api);
