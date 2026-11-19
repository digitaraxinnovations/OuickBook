"use client";

import { ContactListPage } from "@/components/lists/ContactListPage";
import { useAuth } from "@/context/AuthContext";
import { formatMoney } from "@/lib/format";
import { customerService } from "@/services";
import { Customer } from "@/types/models";

export default function CustomersPage() {
  const { company } = useAuth();
  return (
    <ContactListPage<Customer>
      title="Customers"
      subtitle="People and businesses you sell to. Click a row to edit."
      itemName="Customer"
      service={customerService}
      extraColumns={[
        { header: "Open balance", align: "right", render: (row) => formatMoney(row.open_balance, company?.currency) },
      ]}
    />
  );
}
