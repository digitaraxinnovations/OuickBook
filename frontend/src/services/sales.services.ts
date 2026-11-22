/**
 * Services for Phase 2 sales features.
 */
import { ApiClient } from "@/lib/api-client";
import {
  CompanyInput,
  ContactInput,
  DepositInput,
  EmailInput,
  PaymentInput,
  PaymentTermInput,
  SalesDocumentInput,
  StatementEmailInput,
} from "@/types/inputs";
import {
  Company,
  Customer,
  CustomerCredit,
  Deposit,
  EmailLogEntry,
  Invoice,
  Payment,
  PaymentTerm,
  PublicInvoice,
  SalesDocType,
  SalesDocument,
  SalesDocumentSummary,
  SalesDocStatus,
  SalesSettings,
  Statement,
  StatementType,
  UndepositedItem,
} from "@/types/models";
import { ResourceService } from "./resource.service";

export class SalesDocumentService extends ResourceService<SalesDocument, SalesDocumentInput> {
  listByType(docType: SalesDocType, query?: { customer_id?: number; status?: string }): Promise<SalesDocumentSummary[]> {
    return this.api.get<SalesDocumentSummary[]>(this.path, { doc_type: docType, ...query });
  }

  void(id: number): Promise<SalesDocument> {
    return this.api.post<SalesDocument>(this.path + "/" + id + "/void");
  }

  setEstimateStatus(id: number, status: SalesDocStatus): Promise<SalesDocument> {
    return this.api.post<SalesDocument>(this.path + "/" + id + "/status", { status: status });
  }

  convertToInvoice(id: number, invoiceDate: string, percent: string): Promise<Invoice> {
    return this.api.post<Invoice>(this.path + "/" + id + "/convert-to-invoice", { invoice_date: invoiceDate, percent: percent });
  }

  downloadPdf(id: number): Promise<Blob> {
    return this.api.getBlob(this.path + "/" + id + "/pdf");
  }

  email(id: number, input: EmailInput): Promise<{ message: string }> {
    return this.api.post(this.path + "/" + id + "/email", input);
  }
}

export class PaymentService extends ResourceService<Payment, PaymentInput> {}

export class CustomerService extends ResourceService<Customer, ContactInput> {
  credits(customerId: number): Promise<CustomerCredit[]> {
    return this.api.get<CustomerCredit[]>(this.path + "/" + customerId + "/credits");
  }

  statement(customerId: number, type: StatementType, startDate: string, endDate: string): Promise<Statement> {
    return this.api.get<Statement>(this.path + "/" + customerId + "/statement", {
      statement_type: type,
      start_date: startDate,
      end_date: endDate,
    });
  }

  statementPdf(customerId: number, type: StatementType, startDate: string, endDate: string): Promise<Blob> {
    return this.api.getBlob(this.path + "/" + customerId + "/statement/pdf", {
      statement_type: type,
      start_date: startDate,
      end_date: endDate,
    });
  }

  emailStatement(customerId: number, input: StatementEmailInput): Promise<{ message: string }> {
    return this.api.post(this.path + "/" + customerId + "/statement/email", input);
  }
}

export class DepositService extends ResourceService<Deposit, DepositInput> {
  undeposited(): Promise<UndepositedItem[]> {
    return this.api.get<UndepositedItem[]>(this.path + "/undeposited");
  }
}

export class TermsService extends ResourceService<PaymentTerm, PaymentTermInput> {}

export class CompanySettingsService {
  private api: ApiClient;

  constructor(api: ApiClient) {
    this.api = api;
  }

  updateCompany(input: CompanyInput): Promise<Company> {
    return this.api.put<Company>("/company", input);
  }

  getSalesSettings(): Promise<SalesSettings> {
    return this.api.get<SalesSettings>("/company/sales-settings");
  }

  updateSalesSettings(input: SalesSettings): Promise<SalesSettings> {
    return this.api.put<SalesSettings>("/company/sales-settings", input);
  }

  getLogo(): Promise<{ data_url: string | null }> {
    return this.api.get("/company/logo");
  }

  uploadLogo(mimeType: string, dataBase64: string): Promise<{ data_url: string | null }> {
    return this.api.put("/company/logo", { mime_type: mimeType, data_base64: dataBase64 });
  }

  removeLogo(): Promise<{ data_url: string | null }> {
    return this.api.delete("/company/logo");
  }

  emailLog(): Promise<EmailLogEntry[]> {
    return this.api.get<EmailLogEntry[]>("/email-log");
  }
}

/** Customer-facing invoice page. Works without signing in. */
export class PortalService {
  private api: ApiClient;

  constructor(api: ApiClient) {
    this.api = api;
  }

  getInvoice(token: string): Promise<PublicInvoice> {
    return this.api.get<PublicInvoice>("/public/invoices/" + token);
  }

  downloadPdf(token: string): Promise<Blob> {
    return this.api.getBlob("/public/invoices/" + token + "/pdf");
  }

  pay(token: string): Promise<{ checkout_url: string }> {
    return this.api.post("/public/invoices/" + token + "/pay", {});
  }

  /** The "Pay" button of the simulated checkout (only works when PAYMENT_PROVIDER=mock). */
  mockPay(token: string, amount?: string): Promise<PublicInvoice> {
    return this.api.post<PublicInvoice>("/public/invoices/" + token + "/mock-pay", amount ? { amount: amount } : {});
  }
}
