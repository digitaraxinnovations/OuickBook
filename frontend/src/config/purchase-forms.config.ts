/**
 * Vendor forms that share one set of pages (/expenses/forms/<slug>).
 * To add a form type, add one entry here.
 */
import { PurchaseDocType } from "@/types/models";

export interface PurchaseFormConfig {
  type: PurchaseDocType;
  slug: string;
  title: string;
  plural: string;
  description: string;
  /** Bills have a due date and terms. */
  hasDueDate: boolean;
  /** Label for the number field. Purchase orders are numbered automatically. */
  numberLabel: string | null;
  /** Used when attaching files. */
  attachmentType: string;
}

export const purchaseForms: PurchaseFormConfig[] = [
  {
    type: "BILL",
    slug: "bills",
    title: "Bill",
    plural: "Bills",
    description: "Bills from vendors that you will pay later.",
    hasDueDate: true,
    numberLabel: "Bill no.",
    attachmentType: "BILL",
  },
  {
    type: "VENDOR_CREDIT",
    slug: "vendor-credits",
    title: "Vendor credit",
    plural: "Vendor credits",
    description: "Credit a vendor gave you. Use it when you pay their bills.",
    hasDueDate: false,
    numberLabel: "Ref no.",
    attachmentType: "VENDOR_CREDIT",
  },
  {
    type: "PURCHASE_ORDER",
    slug: "purchase-orders",
    title: "Purchase order",
    plural: "Purchase orders",
    description: "Orders you send to vendors. Turn them into bills when the goods arrive.",
    hasDueDate: false,
    numberLabel: null,
    attachmentType: "PURCHASE_ORDER",
  },
];

export function findPurchaseFormBySlug(slug: string): PurchaseFormConfig | undefined {
  return purchaseForms.find((form) => form.slug === slug);
}

export function findPurchaseFormByType(type: PurchaseDocType): PurchaseFormConfig {
  const form = purchaseForms.find((item) => item.type === type);
  if (!form) {
    throw new Error("Unknown vendor form type " + type);
  }
  return form;
}
