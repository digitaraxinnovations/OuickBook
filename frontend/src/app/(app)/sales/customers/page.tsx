"use client";

import { ContactListPage } from "@/components/lists/ContactListPage";
import { ScoreBadge } from "@/components/sales/ScoreBadge";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatMoney } from "@/lib/format";
import { customerService, platformService, taxService, termsService } from "@/services";
import { Customer } from "@/types/models";

export default function CustomersPage() {
  const { company } = useAuth();
  const terms = useLoad(() => termsService.list());
  const taxCodes = useLoad(() => taxService.codes(true));
  const currencies = useLoad(() => platformService.currencies());
  const scores = useLoad(() => customerService.paymentScores());

  function renderScore(customerId: number) {
    const score = (scores.data || []).find((item) => item.customer_id === customerId);
    return score ? <ScoreBadge score={score} /> : null;
  }

  return (
    <ContactListPage<Customer>
      title="Customers"
      subtitle="People and businesses you sell to. Click a customer to see their transactions and statement."
      itemName="Customer"
      service={customerService}
      terms={terms.data || []}
      taxCodes={taxCodes.data || []}
      currencies={currencies.data || []}
      detailHref={(row) => "/sales/customers/" + row.id}
      extraColumns={[
        { header: "Pays", render: (row) => renderScore(row.id) },
        { header: "Open balance", align: "right", render: (row) => formatMoney(row.open_balance, company?.currency) },
      ]}
    />
  );
}
