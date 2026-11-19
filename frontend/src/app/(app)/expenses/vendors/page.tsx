"use client";

import { ContactListPage } from "@/components/lists/ContactListPage";
import { vendorService } from "@/services";
import { Vendor } from "@/types/models";

export default function VendorsPage() {
  return (
    <ContactListPage<Vendor>
      title="Vendors"
      subtitle="People and businesses you buy from. Click a row to edit."
      itemName="Vendor"
      service={vendorService}
    />
  );
}
