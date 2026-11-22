"use client";

import { CreditCard } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage, Loading } from "@/components/ui/Feedback";
import { Field, TextInput } from "@/components/ui/FormFields";
import { useLoad } from "@/hooks/useLoad";
import { formatMoney } from "@/lib/format";
import { portalService } from "@/services";

// Test card shown in the simulated form (nothing is sent anywhere).
const DEMO_CARD = { number: "4242 4242 4242 4242", expiry: "12 / 34", cvc: "123" };

/** A pretend card checkout (PAYMENT_PROVIDER=mock). Paying here records a real payment on the invoice; no money moves. */
export default function MockCheckoutPage() {
  const params = useParams<{ token: string }>();
  const router = useRouter();
  const invoice = useLoad(() => portalService.getInvoice(params.token), [params.token]);
  const [amount, setAmount] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [paying, setPaying] = useState(false);

  // The amount comes from the link (?amount=...); empty means the whole balance.
  useEffect(() => {
    setAmount(new URLSearchParams(window.location.search).get("amount") || "");
  }, []);

  if (invoice.loading) {
    return <Loading />;
  }
  if (!invoice.data) {
    return (
      <div className="mx-auto max-w-md p-10">
        <ErrorMessage message={invoice.error} />
      </div>
    );
  }
  const data = invoice.data;
  const toPay = amount || data.balance_due;
  const invoicePage = "/portal/invoices/" + params.token;

  async function pay(event: FormEvent) {
    event.preventDefault();
    setPaying(true);
    setError(null);
    try {
      await portalService.mockPay(params.token, toPay);
      router.push(invoicePage + "?paid=1");
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "The payment could not be made.");
      setPaying(false);
    }
  }

  return (
    <div className="min-h-screen bg-page px-4 py-10">
      <form onSubmit={pay} className="mx-auto max-w-md space-y-4 rounded-lg bg-white p-8 shadow-sm">
        <div className="rounded-md bg-amber-50 p-3 text-sm text-amber-900">
          <strong>Simulated checkout.</strong> This looks like a card payment page, but no card is charged and no money moves.
        </div>
        <div>
          <div className="text-sm text-gray-500">
            {data.company_name} - invoice {data.invoice_number}
          </div>
          <div className="text-3xl font-semibold">{formatMoney(toPay, data.currency)}</div>
        </div>
        <ErrorMessage message={error} />
        <Field label="Card number">
          <TextInput readOnly value={DEMO_CARD.number} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Expires">
            <TextInput readOnly value={DEMO_CARD.expiry} />
          </Field>
          <Field label="Security code">
            <TextInput readOnly value={DEMO_CARD.cvc} />
          </Field>
        </div>
        <Button type="submit" disabled={paying} className="w-full">
          <CreditCard size={16} /> {paying ? "Paying..." : "Pay " + formatMoney(toPay, data.currency) + " (simulated)"}
        </Button>
        <button type="button" onClick={() => router.push(invoicePage)} className="block w-full text-center text-sm text-gray-500 hover:underline">
          Cancel and go back to the invoice
        </button>
      </form>
    </div>
  );
}
