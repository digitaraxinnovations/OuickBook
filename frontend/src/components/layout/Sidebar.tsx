"use client";

import { BarChart3, BookOpen, Home, Landmark, Percent, Receipt, Settings, ShoppingCart, Users } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { appConfig } from "@/config/app.config";
import { NavGroup, sidebarMenu } from "@/config/navigation";
import { NewMenuButton } from "./NewMenuButton";

const icons = {
  home: Home,
  sales: ShoppingCart,
  expenses: Receipt,
  banking: Landmark,
  payroll: Users,
  taxes: Percent,
  accounting: BookOpen,
  reports: BarChart3,
  settings: Settings,
};

function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(href + "/");
}

function SidebarGroup({ group, pathname }: { group: NavGroup; pathname: string }) {
  const Icon = icons[group.icon];
  const linkClass = "flex items-center gap-3 rounded-md px-3 py-2 text-sm";

  if (group.href) {
    const active = isActive(pathname, group.href);
    return (
      <Link
        href={group.href}
        className={linkClass + (active ? " bg-sidebar-hover font-semibold text-white" : " text-gray-300 hover:bg-sidebar-hover")}
      >
        <Icon size={18} />
        {group.label}
      </Link>
    );
  }

  return (
    <div className="mt-2">
      <div className={linkClass + " font-medium text-gray-100"}>
        <Icon size={18} />
        {group.label}
      </div>
      <div className="ml-9 flex flex-col">
        {group.links?.map((link) => {
          const active = pathname === link.href || (link.href !== "/expenses" && link.href !== "/banking" && isActive(pathname, link.href));
          return (
            <Link
              key={link.href}
              href={link.href}
              className={
                "rounded-md px-3 py-1.5 text-sm " +
                (active ? "bg-sidebar-hover font-semibold text-white" : "text-gray-400 hover:text-white")
              }
            >
              {link.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="no-print flex w-60 shrink-0 flex-col bg-sidebar px-3 py-4">
      <div className="mb-5 flex items-center gap-2 px-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-500 text-sm font-bold text-white">
          {appConfig.appName.charAt(0)}
        </div>
        <span className="text-lg font-semibold text-white">{appConfig.appName}</span>
      </div>
      <NewMenuButton />
      <nav className="mt-4 flex flex-col gap-1">
        {sidebarMenu.map((group) => (
          <SidebarGroup key={group.label} group={group} pathname={pathname} />
        ))}
      </nav>
    </aside>
  );
}
