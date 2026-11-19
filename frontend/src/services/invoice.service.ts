import { EmailInput, InvoiceInput } from "@/types/inputs";
import { BatchResult, Invoice, InvoicePayment, InvoiceSummary } from "@/types/models";
import { ResourceService } from "./resource.service";

/** Invoices have extra actions on top of the standard ones. */
export class InvoiceService extends ResourceService<Invoice, InvoiceInput> {
  listSummaries(query?: { customer_id?: number; status?: string }): Promise<InvoiceSummary[]> {
    return this.api.get<InvoiceSummary[]>(this.path, query);
  }

  void(id: number): Promise<Invoice> {
    return this.api.post<Invoice>(this.path + "/" + id + "/void");
  }

  listPayments(id: number): Promise<InvoicePayment[]> {
    return this.api.get<InvoicePayment[]>(this.path + "/" + id + "/payments");
  }

  downloadPdf(id: number): Promise<Blob> {
    return this.api.getBlob(this.path + "/" + id + "/pdf");
  }

  email(id: number, input: EmailInput): Promise<{ message: string }> {
    return this.api.post(this.path + "/" + id + "/email", input);
  }

  shareLink(id: number): Promise<{ url: string }> {
    return this.api.post(this.path + "/" + id + "/share-link");
  }

  applyLateFees(): Promise<BatchResult> {
    return this.api.post<BatchResult>(this.path + "/apply-late-fees");
  }

  sendReminders(): Promise<BatchResult> {
    return this.api.post<BatchResult>(this.path + "/send-reminders");
  }
}
