/**
 * Services for Phase 3 (vendor side) features.
 */
import { ApiClient } from "@/lib/api-client";
import {
  BatchBillPaymentInput,
  BillPaymentInput,
  ExpenseInput,
  PurchaseDocumentInput,
  TripInput,
} from "@/types/inputs";
import {
  Attachment,
  BillPayment,
  BillPaymentForBill,
  CheckToPrint,
  Expense,
  MileageSummary,
  PurchaseDocType,
  PurchaseDocument,
  PurchaseDocumentSummary,
  Trip,
} from "@/types/models";
import { ResourceService } from "./resource.service";

export class ExpenseService extends ResourceService<Expense, ExpenseInput> {
  void(id: number): Promise<Expense> {
    return this.api.post<Expense>(this.path + "/" + id + "/void");
  }
}

export class PurchaseDocumentService extends ResourceService<PurchaseDocument, PurchaseDocumentInput> {
  listByType(docType: PurchaseDocType, query?: { vendor_id?: number; status?: string }): Promise<PurchaseDocumentSummary[]> {
    return this.api.get<PurchaseDocumentSummary[]>(this.path, { doc_type: docType, ...query });
  }

  void(id: number): Promise<PurchaseDocument> {
    return this.api.post<PurchaseDocument>(this.path + "/" + id + "/void");
  }

  convertToBill(id: number, billDate: string, billNumber: string): Promise<PurchaseDocument> {
    return this.api.post<PurchaseDocument>(this.path + "/" + id + "/convert-to-bill", { bill_date: billDate, bill_number: billNumber });
  }

  close(id: number): Promise<PurchaseDocument> {
    return this.api.post<PurchaseDocument>(this.path + "/" + id + "/close");
  }

  payments(id: number): Promise<BillPaymentForBill[]> {
    return this.api.get<BillPaymentForBill[]>(this.path + "/" + id + "/payments");
  }
}

export class BillPaymentService extends ResourceService<BillPayment, BillPaymentInput> {
  payBatch(input: BatchBillPaymentInput): Promise<BillPayment[]> {
    return this.api.post<BillPayment[]>(this.path + "/batch", input);
  }

  remove(id: number): Promise<void> {
    return this.api.delete<void>(this.path + "/" + id);
  }
}

export class CheckService {
  private api: ApiClient;

  constructor(api: ApiClient) {
    this.api = api;
  }

  toPrint(): Promise<CheckToPrint[]> {
    return this.api.get<CheckToPrint[]>("/checks/to-print");
  }

  nextNumber(bankAccountId: number): Promise<{ bank_account_id: number; next_check_number: number }> {
    return this.api.get("/checks/next-number/" + bankAccountId);
  }

  /** Numbers and prints the checks. Returns the PDF. */
  print(bankAccountId: number, firstNumber: number, items: { source_type: string; source_id: number }[]): Promise<Blob> {
    return this.api.postForBlob("/checks/print", {
      bank_account_id: bankAccountId,
      first_check_number: firstNumber,
      items: items,
    });
  }

  reprint(sourceType: string, sourceId: number): Promise<Blob> {
    return this.api.getBlob("/checks/" + sourceType + "/" + sourceId + "/pdf");
  }
}

export class AttachmentService {
  private api: ApiClient;

  constructor(api: ApiClient) {
    this.api = api;
  }

  list(entityType: string, entityId: number): Promise<Attachment[]> {
    return this.api.get<Attachment[]>("/attachments", { entity_type: entityType, entity_id: entityId });
  }

  receipts(): Promise<Attachment[]> {
    return this.api.get<Attachment[]>("/attachments/receipts");
  }

  upload(entityType: string, entityId: number | null, file: File, dataBase64: string): Promise<Attachment> {
    return this.api.post<Attachment>("/attachments", {
      entity_type: entityType,
      entity_id: entityId,
      filename: file.name,
      mime_type: file.type || "application/octet-stream",
      data_base64: dataBase64,
    });
  }

  download(id: number): Promise<Blob> {
    return this.api.getBlob("/attachments/" + id + "/content");
  }

  link(id: number, entityType: string, entityId: number): Promise<Attachment> {
    return this.api.put<Attachment>("/attachments/" + id + "/link", { entity_type: entityType, entity_id: entityId });
  }

  remove(id: number): Promise<void> {
    return this.api.delete<void>("/attachments/" + id);
  }
}

export class MileageService {
  private api: ApiClient;

  constructor(api: ApiClient) {
    this.api = api;
  }

  trips(year: number): Promise<Trip[]> {
    return this.api.get<Trip[]>("/mileage/trips", { year: year });
  }

  createTrip(input: TripInput): Promise<Trip> {
    return this.api.post<Trip>("/mileage/trips", input);
  }

  updateTrip(id: number, input: TripInput): Promise<Trip> {
    return this.api.put<Trip>("/mileage/trips/" + id, input);
  }

  deleteTrip(id: number): Promise<void> {
    return this.api.delete<void>("/mileage/trips/" + id);
  }

  summary(year: number): Promise<MileageSummary> {
    return this.api.get<MileageSummary>("/mileage/summary", { year: year });
  }

  setRate(rate: string): Promise<MileageSummary> {
    return this.api.put<MileageSummary>("/mileage/rate", { mileage_rate: rate });
  }
}
