"use client";

import { Select, TextInput } from "@/components/ui/FormFields";
import { formatMoney, toNumber } from "@/lib/format";
import { SalesAmountsInput, SalesLineInput } from "@/types/inputs";
import { DiscountType, TaxCode } from "@/types/models";
import { salesLineAmount } from "./SalesLinesEditor";

export function emptySalesAmounts(): SalesAmountsInput {
  return { tax_code_id: null, discount_type: null, discount_value: "0", shipping_amount: "0" };
}

/** The percentages of the chosen tax code (none for exempt customers). */
export function taxRatesFor(taxCodes: TaxCode[], taxCodeId: number | null, taxExempt: boolean): number[] {
  const code = taxCodes.find((item) => item.id === taxCodeId);
  if (!code || taxExempt) {
    return [];
  }
  return code.components.map((component) => toNumber(component.rate));
}

function roundCents(value: number): number {
  return Math.round(value * 100) / 100;
}

/** Same calculation the backend does, so the screen matches the saved total. */
export function computeSalesTotals(lines: SalesLineInput[], amounts: SalesAmountsInput, extraLinesTotal = 0, taxRates: number[] = []) {
  let subtotal = extraLinesTotal;
  let taxableSubtotal = 0;
  for (const line of lines) {
    subtotal += salesLineAmount(line);
    if (line.taxable) {
      taxableSubtotal += salesLineAmount(line);
    }
  }
  let discount = 0;
  if (amounts.discount_type === "PERCENT") {
    discount = Math.round(subtotal * toNumber(amounts.discount_value)) / 100;
  } else if (amounts.discount_type === "AMOUNT") {
    discount = toNumber(amounts.discount_value);
  }
  const shipping = toNumber(amounts.shipping_amount);

  // Taxable lines lose their fair share of the discount; shipping is not taxed.
  let taxBase = 0;
  if (taxableSubtotal > 0) {
    let discountShare = 0;
    if (discount > 0 && subtotal > 0) {
      discountShare = roundCents((discount * taxableSubtotal) / subtotal);
    }
    taxBase = taxableSubtotal - discountShare;
  }
  let tax = 0;
  for (const rate of taxRates) {
    tax += roundCents((taxBase * rate) / 100);
  }
  return { subtotal, discount, shipping, tax, total: subtotal - discount + shipping + tax };
}

interface SalesTotalsProps {
  lines: SalesLineInput[];
  amounts: SalesAmountsInput;
  onChange: (amounts: SalesAmountsInput) => void;
  taxCodes: TaxCode[];
  /** The chosen customer is tax exempt. */
  taxExempt?: boolean;
  currency?: string;
  /** Amount from lines that are not in `lines` (e.g. delayed charges being added). */
  extraLinesTotal?: number;
}

/** Subtotal, discount, shipping, sales tax and total box shown under the lines. */
export function SalesTotals({ lines, amounts, onChange, taxCodes, taxExempt = false, currency, extraLinesTotal = 0 }: SalesTotalsProps) {
  const taxRates = taxRatesFor(taxCodes, amounts.tax_code_id, taxExempt);
  const totals = computeSalesTotals(lines, amounts, extraLinesTotal, taxRates);
  const taxOptions = taxCodes.map((code) => ({ value: code.id, label: code.name + " (" + toNumber(code.total_rate) + "%)" }));

  function setDiscountType(value: string) {
    onChange({ ...amounts, discount_type: value ? (value as DiscountType) : null });
  }

  function setTaxCode(value: string) {
    onChange({ ...amounts, tax_code_id: value ? Number(value) : null });
  }

  return (
    <div className="w-full max-w-sm space-y-2 text-sm">
      <div className="flex justify-between">
        <span className="text-gray-600">Subtotal</span>
        <span className="font-medium">{formatMoney(totals.subtotal, currency)}</span>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Select
            className="w-36! py-1!"
            value={amounts.discount_type ?? ""}
            onChange={(e) => setDiscountType(e.target.value)}
            placeholder="No discount"
            options={[
              { value: "PERCENT", label: "Discount %" },
              { value: "AMOUNT", label: "Discount $" },
            ]}
          />
          {amounts.discount_type && (
            <TextInput
              className="w-24! py-1!"
              type="number"
              step="0.01"
              min="0"
              value={amounts.discount_value}
              onChange={(e) => onChange({ ...amounts, discount_value: e.target.value })}
            />
          )}
        </div>
        <span>{totals.discount > 0 ? "-" + formatMoney(totals.discount, currency) : ""}</span>
      </div>
      <div className="flex items-center justify-between gap-2">
        <span className="text-gray-600">Shipping</span>
        <TextInput
          className="w-32! py-1! text-right"
          type="number"
          step="0.01"
          min="0"
          value={amounts.shipping_amount}
          onChange={(e) => onChange({ ...amounts, shipping_amount: e.target.value })}
        />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Select className="w-48! py-1!" value={amounts.tax_code_id ?? ""} onChange={(e) => setTaxCode(e.target.value)} placeholder="No sales tax" options={taxOptions} />
        <span>{amounts.tax_code_id ? formatMoney(totals.tax, currency) : ""}</span>
      </div>
      {taxExempt && amounts.tax_code_id && <p className="text-right text-xs text-gray-500">This customer is tax exempt.</p>}
      <div className="flex justify-between border-t border-gray-200 pt-2 text-xl font-semibold">
        <span>Total</span>
        <span>{formatMoney(totals.total, currency)}</span>
      </div>
    </div>
  );
}
