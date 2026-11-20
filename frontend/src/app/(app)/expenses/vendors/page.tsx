"use client";

import { ContactListPage } from "@/components/lists/ContactListPage";
import { useAuth } from "@/context/AuthContext";
import { useLoad } from "@/hooks/useLoad";
import { formatMoney } from "@/lib/format";
import { termsService, vendorService } from "@/services";
import { Vendor } from "@/types/models";

export default function VendorsPage() {
  const { company } = useAuth();
  const terms = useLoad(() => termsService.list());
  return (
    <ContactListPage<Vendor>
      title="Vendors"
      subtitle="People and businesses you buy from. Click a vendor to see their bills and payments."
      itemName="Vendor"
      service={vendorService}
      terms={terms.data || []}
      vendorFields
      detailHref={(row) => "/expenses/vendors/" + row.id}
      extraColumns={[
        { header: "1099", render: (row) => (row.track_1099 ? "Yes" : "") },
        { header: "Open balance", align: "right", render: (row) => formatMoney(row.open_balance, company?.currency) },
      ]}
    />
  );
}
