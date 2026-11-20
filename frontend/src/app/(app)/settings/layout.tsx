"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";

const tabs = [
  { label: "Company", href: "/settings" },
  { label: "Sales", href: "/settings/sales" },
  { label: "Expenses & advanced", href: "/settings/advanced" },
  { label: "Users", href: "/settings/users" },
  { label: "Currencies", href: "/settings/currencies" },
  { label: "Payment terms", href: "/settings/terms" },
  { label: "Import & export", href: "/settings/data" },
  { label: "Audit log", href: "/settings/audit-log" },
  { label: "API & webhooks", href: "/settings/integrations" },
  { label: "Email log", href: "/settings/email-log" },
];

export default function SettingsLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold text-gray-900">Settings</h1>
      <div className="mb-6 flex flex-wrap gap-1 border-b border-gray-200">
        {tabs.map((tab) => {
          const active = pathname === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={
                "-mb-px border-b-2 px-4 py-2 text-sm font-medium " +
                (active ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-800")
              }
            >
              {tab.label}
            </Link>
          );
        })}
      </div>
      {children}
    </div>
  );
}
