import { ApiClient } from "@/lib/api-client";
import { SalesTaxAdjustmentInput, SalesTaxPaymentInput, TaxAgencyInput, TaxCodeInput, TaxRateInput } from "@/types/inputs";
import { SalesTaxAdjustment, SalesTaxPayment, TaxAgency, TaxCode, TaxPeriod, TaxRate } from "@/types/models";

/** Sales tax setup (agencies, rates, codes) and filing (periods, payments, adjustments). */
export class TaxService {
  private api: ApiClient;

  constructor(api: ApiClient) {
    this.api = api;
  }

  // ----- setup -----

  agencies(): Promise<TaxAgency[]> {
    return this.api.get<TaxAgency[]>("/taxes/agencies");
  }

  saveAgency(input: TaxAgencyInput, id?: number): Promise<TaxAgency> {
    if (id) {
      return this.api.put<TaxAgency>("/taxes/agencies/" + id, input);
    }
    return this.api.post<TaxAgency>("/taxes/agencies", input);
  }

  rates(): Promise<TaxRate[]> {
    return this.api.get<TaxRate[]>("/taxes/rates");
  }

  saveRate(input: TaxRateInput, id?: number): Promise<TaxRate> {
    if (id) {
      return this.api.put<TaxRate>("/taxes/rates/" + id, input);
    }
    return this.api.post<TaxRate>("/taxes/rates", input);
  }

  codes(activeOnly = false): Promise<TaxCode[]> {
    return this.api.get<TaxCode[]>("/taxes/codes", { active_only: activeOnly });
  }

  saveCode(input: TaxCodeInput, id?: number): Promise<TaxCode> {
    if (id) {
      return this.api.put<TaxCode>("/taxes/codes/" + id, input);
    }
    return this.api.post<TaxCode>("/taxes/codes", input);
  }

  // ----- filing -----

  periods(): Promise<TaxPeriod[]> {
    return this.api.get<TaxPeriod[]>("/taxes/periods");
  }

  payments(): Promise<SalesTaxPayment[]> {
    return this.api.get<SalesTaxPayment[]>("/taxes/payments");
  }

  recordPayment(input: SalesTaxPaymentInput): Promise<SalesTaxPayment> {
    return this.api.post<SalesTaxPayment>("/taxes/payments", input);
  }

  adjustments(): Promise<SalesTaxAdjustment[]> {
    return this.api.get<SalesTaxAdjustment[]>("/taxes/adjustments");
  }

  recordAdjustment(input: SalesTaxAdjustmentInput): Promise<SalesTaxAdjustment> {
    return this.api.post<SalesTaxAdjustment>("/taxes/adjustments", input);
  }

  // ----- income tax categories -----

  taxLines(): Promise<Record<string, string>> {
    return this.api.get<Record<string, string>>("/taxes/tax-lines");
  }
}
