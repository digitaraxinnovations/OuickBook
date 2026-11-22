"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/Feedback";
import { Field, Select, TextArea } from "@/components/ui/FormFields";
import { Modal } from "@/components/ui/Modal";
import { SimulatedBadge } from "@/components/ui/SimulatedBadge";
import { toNumber } from "@/lib/format";
import { taxService } from "@/services";
import { FoundTaxRate, TaxAgency } from "@/types/models";

interface RateLookupDialogProps {
  open: boolean;
  agencies: TaxAgency[];
  /** Filled in from the company address. */
  defaultAddress: string;
  simulated: boolean;
  onClose: () => void;
  onAdded: () => void;
}

/** Find the sales tax rates that apply at an address, and add them under a tax agency. */
export function RateLookupDialog({ open, agencies, defaultAddress, simulated, onClose, onAdded }: RateLookupDialogProps) {
  const [address, setAddress] = useState(defaultAddress);
  const [found, setFound] = useState<FoundTaxRate[] | null>(null);
  const [agencyId, setAgencyId] = useState(agencies.length === 1 ? String(agencies[0].id) : "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function lookUp(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setFound(await taxService.lookupRates(address));
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not look up the rates.");
    }
    setBusy(false);
  }

  async function addAll() {
    if (!found || !agencyId) {
      setError("Choose the tax agency these rates belong to.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      for (const item of found) {
        await taxService.saveRate({ name: item.name, agency_id: Number(agencyId), rate: item.rate, is_active: true, create_code: true });
      }
      onAdded();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Could not add the rates.");
      setBusy(false);
    }
  }

  return (
    <Modal title="Look up sales tax rates" open={open} onClose={onClose}>
      <form onSubmit={lookUp} className="space-y-4">
        <ErrorMessage message={error} />
        <p className="text-sm text-gray-600">
          Enter the address where you sell. The rates that apply there are found for you.
          {simulated && <SimulatedBadge title="Simulated: the rates are sample values worked out from the state and ZIP code." />}
        </p>
        <Field label="Address (with state and ZIP code)" required>
          <TextArea rows={2} required value={address} onChange={(e) => setAddress(e.target.value)} placeholder="120 Maple Street, Springfield, IL 62701" />
        </Field>
        <Button type="submit" variant="secondary" disabled={busy}>
          {busy ? "Looking up..." : "Look up rates"}
        </Button>
      </form>

      {found && (
        <div className="mt-6 space-y-4 border-t border-gray-200 pt-4">
          <table className="w-full text-sm">
            <tbody>
              {found.map((item) => (
                <tr key={item.name} className="border-b border-gray-100">
                  <td className="py-2">{item.name}</td>
                  <td className="py-2 text-right font-medium">{toNumber(item.rate)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Field label="Add these rates under agency" required>
            <Select value={agencyId} onChange={(e) => setAgencyId(e.target.value)} placeholder="Choose an agency" options={agencies.map((agency) => ({ value: agency.id, label: agency.name }))} />
          </Field>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="button" onClick={addAll} disabled={busy}>
              Add these rates
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
