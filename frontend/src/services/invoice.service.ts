import { InvoiceInput, PaymentInput } from "@/types/inputs";
import { Invoice, InvoiceSummary, Payment } from "@/types/models";
import { ResourceService } from "./resource.service";

/** Invoices have extra actions on top of the standard ones. */
export class InvoiceService extends ResourceService<Invoice, InvoiceInput> {
  listSummaries(query?: { customer_id?: number; status?: string }): Promise<InvoiceSummary[]> {
    return this.api.get<InvoiceSummary[]>(this.path, query);
  }

  void(id: number): Promise<Invoice> {
    return this.api.post<Invoice>(this.path + "/" + id + "/void");
  }

  listPayments(id: number): Promise<Payment[]> {
    return this.api.get<Payment[]>(this.path + "/" + id + "/payments");
  }

  receivePayment(input: PaymentInput): Promise<Payment> {
    return this.api.post<Payment>("/payments", input);
  }
}
