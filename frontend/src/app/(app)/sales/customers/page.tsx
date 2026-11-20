"use client";

import { ContactListPage } from "@/components/lists/ContactListPage";
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
        { header: "Open balance", align: "right", render: (row) => formatMoney(row.open_balance, company?.currency) },
      ]}
    />
  );
}
