/**
 * The sales forms that share one set of pages (/sales/forms/<slug>).
 * To add a form type, add one entry here - the pages read everything from it.
 */
import { SalesDocType } from "@/types/models";

export interface SalesFormConfig {
  type: SalesDocType;
  slug: string;
  title: string;
  plural: string;
  description: string;
  /** Show an expiration date (estimates). */
  hasExpirationDate: boolean;
  /** Which money account field to show, if any. */
  moneyAccount: "none" | "depositTo" | "refundFrom";
}

export const salesForms: SalesFormConfig[] = [
  {
    type: "ESTIMATE",
    slug: "estimates",
    title: "Estimate",
    plural: "Estimates",
    description: "Quotes for customers. Accept them and turn them into invoices - all at once or in parts.",
    hasExpirationDate: true,
    moneyAccount: "none",
  },
  {
    type: "SALES_RECEIPT",
    slug: "sales-receipts",
    title: "Sales receipt",
    plural: "Sales receipts",
    description: "Sales paid on the spot - no invoice needed.",
    hasExpirationDate: false,
    moneyAccount: "depositTo",
  },
  {
    type: "CREDIT_MEMO",
    slug: "credit-memos",
    title: "Credit memo",
    plural: "Credit memos",
    description: "Credit you give a customer. Use it on their invoices when you receive a payment.",
    hasExpirationDate: false,
    moneyAccount: "none",
  },
  {
    type: "REFUND_RECEIPT",
    slug: "refund-receipts",
    title: "Refund receipt",
    plural: "Refund receipts",
    description: "Money you give back to a customer.",
    hasExpirationDate: false,
    moneyAccount: "refundFrom",
  },
  {
    type: "DELAYED_CHARGE",
    slug: "delayed-charges",
    title: "Delayed charge",
    plural: "Delayed charges",
    description: "Charges to add to a customer's next invoice. They do not affect your books until invoiced.",
    hasExpirationDate: false,
    moneyAccount: "none",
  },
  {
    type: "DELAYED_CREDIT",
    slug: "delayed-credits",
    title: "Delayed credit",
    plural: "Delayed credits",
    description: "Credits to subtract on a customer's next invoice.",
    hasExpirationDate: false,
    moneyAccount: "none",
  },
];

export function findFormBySlug(slug: string): SalesFormConfig | undefined {
  return salesForms.find((form) => form.slug === slug);
}

export function findFormByType(type: SalesDocType): SalesFormConfig {
  const form = salesForms.find((item) => item.type === type);
  if (!form) {
    throw new Error("Unknown sales form type " + type);
  }
  return form;
}
