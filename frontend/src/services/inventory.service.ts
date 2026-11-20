import { ApiClient } from "@/lib/api-client";
import { CategoryInput, InventoryAdjustmentInput, PriceRuleInput } from "@/types/inputs";
import {
  InventoryAdjustment,
  PriceRule,
  ProductCategory,
  ProductImportResult,
  ProductPrice,
  StockMovement,
} from "@/types/models";

/** Product categories, price rules, inventory adjustments, stock history and import/export. */
export class InventoryService {
  private api: ApiClient;

  constructor(api: ApiClient) {
    this.api = api;
  }

  // ----- categories -----

  categories(): Promise<ProductCategory[]> {
    return this.api.get<ProductCategory[]>("/product-categories");
  }

  saveCategory(input: CategoryInput, id?: number): Promise<ProductCategory> {
    if (id) {
      return this.api.put<ProductCategory>("/product-categories/" + id, input);
    }
    return this.api.post<ProductCategory>("/product-categories", input);
  }

  // ----- price rules -----

  priceRules(): Promise<PriceRule[]> {
    return this.api.get<PriceRule[]>("/price-rules");
  }

  savePriceRule(input: PriceRuleInput, id?: number): Promise<PriceRule> {
    if (id) {
      return this.api.put<PriceRule>("/price-rules/" + id, input);
    }
    return this.api.post<PriceRule>("/price-rules", input);
  }

  /** Each item's price after price rules for this customer and date. */
  prices(customerId: number | null, onDate: string): Promise<ProductPrice[]> {
    const query: Record<string, string | number> = { on_date: onDate };
    if (customerId) {
      query.customer_id = customerId;
    }
    return this.api.get<ProductPrice[]>("/product-prices", query);
  }

  // ----- adjustments and history -----

  adjustments(): Promise<InventoryAdjustment[]> {
    return this.api.get<InventoryAdjustment[]>("/inventory-adjustments");
  }

  createAdjustment(input: InventoryAdjustmentInput): Promise<InventoryAdjustment> {
    return this.api.post<InventoryAdjustment>("/inventory-adjustments", input);
  }

  voidAdjustment(id: number): Promise<InventoryAdjustment> {
    return this.api.post<InventoryAdjustment>("/inventory-adjustments/" + id + "/void");
  }

  stockHistory(productId: number): Promise<StockMovement[]> {
    return this.api.get<StockMovement[]>("/products/" + productId + "/stock-history");
  }

  // ----- import / export -----

  exportProducts(): Promise<Blob> {
    return this.api.getBlob("/products/export");
  }

  importProducts(content: string): Promise<ProductImportResult> {
    return this.api.post<ProductImportResult>("/products/import", { content: content });
  }
}
