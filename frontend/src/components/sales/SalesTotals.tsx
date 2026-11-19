"use client";

import { Select, TextInput } from "@/components/ui/FormFields";
import { formatMoney, toNumber } from "@/lib/format";
import { SalesAmountsInput, SalesLineInput } from "@/types/inputs";
import { DiscountType } from "@/types/models";
import { salesLineAmount } from "./SalesLinesEditor";

export function emptySalesAmounts(): SalesAmountsInput {
  return { discount_type: null, discount_value: "0", shipping_amount: "0" };
}

/** Same calculation the backend does, so the screen matches the saved total. */
export function computeSalesTotals(lines: SalesLineInput[], amounts: SalesAmountsInput, extraLinesTotal = 0) {
  let subtotal = extraLinesTotal;
  for (const line of lines) {
    subtotal += salesLineAmount(line);
  }
  let discount = 0;
  if (amounts.discount_type === "PERCENT") {
    discount = Math.round(subtotal * toNumber(amounts.discount_value)) / 100;
  } else if (amounts.discount_type === "AMOUNT") {
    discount = toNumber(amounts.discount_value);
  }
  const shipping = toNumber(amounts.shipping_amount);
  return { subtotal, discount, shipping, total: subtotal - discount + shipping };
}

interface SalesTotalsProps {
  lines: SalesLineInput[];
  amounts: SalesAmountsInput;
  onChange: (amounts: SalesAmountsInput) => void;
  currency?: string;
  /** Amount from lines that are not in `lines` (e.g. delayed charges being added). */
  extraLinesTotal?: number;
}

/** Subtotal, discount, shipping and total box shown under the lines. */
export function SalesTotals({ lines, amounts, onChange, currency, extraLinesTotal = 0 }: SalesTotalsProps) {
  const totals = computeSalesTotals(lines, amounts, extraLinesTotal);

  function setDiscountType(value: string) {
    onChange({ ...amounts, discount_type: value ? (value as DiscountType) : null });
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
      <div className="flex justify-between border-t border-gray-200 pt-2 text-xl font-semibold">
        <span>Total</span>
        <span>{formatMoney(totals.total, currency)}</span>
      </div>
    </div>
  );
}
