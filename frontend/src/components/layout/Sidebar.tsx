"use client";

import { BarChart3, BookOpen, Briefcase, ChevronDown, ChevronRight, ChevronsDownUp, ChevronsUpDown, Home, Landmark, Percent, Receipt, Settings, ShoppingCart, Users } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { appConfig } from "@/config/app.config";
import { NavGroup, sidebarMenu } from "@/config/navigation";
import { VISIBLE_MENU } from "@/config/permissions";
import { useAuth } from "@/context/AuthContext";
import { NewMenuButton } from "./NewMenuButton";

const icons = {
  home: Home,
  projects: Briefcase,
  sales: ShoppingCart,
  expenses: Receipt,
  banking: Landmark,
  payroll: Users,
  taxes: Percent,
  accounting: BookOpen,
  reports: BarChart3,
  settings: Settings,
};

const linkClass = "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm";

function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(href + "/");
}

function isLinkActive(pathname: string, href: string): boolean {
  // "/expenses" and "/banking" are parents of other menu links, so they only match exactly.
  return pathname === href || (href !== "/expenses" && href !== "/banking" && isActive(pathname, href));
}

function groupHasPage(group: NavGroup, pathname: string): boolean {
  return (group.links || []).some((link) => isLinkActive(pathname, link.href));
}

/** Which groups the user left open, remembered in the browser between visits. */
class OpenGroupsStore {
  static load(): string[] | null {
    try {
      const saved = window.localStorage.getItem(appConfig.sidebarStorageKey);
      return saved ? (JSON.parse(saved) as string[]) : null;
    } catch {
      return null;
    }
  }

  static save(labels: string[]): void {
    try {
      window.localStorage.setItem(appConfig.sidebarStorageKey, JSON.stringify(labels));
    } catch {
      // Storage can be blocked (private windows); the menu still works, it just forgets.
    }
  }
}

interface GroupProps {
  group: NavGroup;
  pathname: string;
  open: boolean;
  onToggle: () => void;
}

function SidebarGroup({ group, pathname, open, onToggle }: GroupProps) {
  const Icon = icons[group.icon];

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

  const Chevron = open ? ChevronDown : ChevronRight;
  const hasPage = groupHasPage(group, pathname);
  return (
    <div>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className={linkClass + " font-medium hover:bg-sidebar-hover " + (hasPage && !open ? "text-white" : "text-gray-100")}
      >
        <Icon size={18} />
        <span className="flex-1 text-left">{group.label}</span>
        <Chevron size={16} className="text-gray-400" />
      </button>
      {open && (
        <div className="mb-1 ml-9 flex flex-col">
          {group.links?.map((link) => {
            const active = isLinkActive(pathname, link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={
                  "rounded-md px-3 py-1.5 text-sm " + (active ? "bg-sidebar-hover font-semibold text-white" : "text-gray-400 hover:text-white")
                }
              >
                {link.label}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function Sidebar() {
  const { role } = useAuth();
  // Only the menu groups the user's role can open.
  const visible = sidebarMenu.filter((group) => !role || VISIBLE_MENU[role].includes(group.label));
  const folders = visible.filter((group) => !group.href).map((group) => group.label);
  const pathname = usePathname();
  const [openGroups, setOpenGroups] = useState<string[]>([]);

  // First visit: open only the group holding the current page. After that, keep what the user chose.
  useEffect(() => {
    const saved = OpenGroupsStore.load();
    const current = visible.find((group) => groupHasPage(group, pathname));
    const start = saved ?? [];
    setOpenGroups(current && !start.includes(current.label) ? [...start, current.label] : start);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  function update(labels: string[]) {
    setOpenGroups(labels);
    OpenGroupsStore.save(labels);
  }

  function toggle(label: string) {
    update(openGroups.includes(label) ? openGroups.filter((item) => item !== label) : [...openGroups, label]);
  }

  const allOpen = folders.every((label) => openGroups.includes(label));

  return (
    <aside className="no-print sticky top-0 flex h-screen w-60 shrink-0 flex-col bg-sidebar py-4">
      <div className="px-3">
        <div className="mb-5 flex items-center gap-2 px-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-500 text-sm font-bold text-white">
            {appConfig.appName.charAt(0)}
          </div>
          <span className="flex-1 text-lg font-semibold text-white">{appConfig.appName}</span>
          <button
            type="button"
            onClick={() => update(allOpen ? [] : folders)}
            className="rounded p-1 text-gray-400 hover:bg-sidebar-hover hover:text-white"
            title={allOpen ? "Collapse all" : "Expand all"}
            aria-label={allOpen ? "Collapse all" : "Expand all"}
          >
            {allOpen ? <ChevronsDownUp size={16} /> : <ChevronsUpDown size={16} />}
          </button>
        </div>
        <NewMenuButton />
      </div>
      <nav className="sidebar-scroll mt-4 flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto px-3 pb-4">
        {visible.map((group) => (
          <SidebarGroup
            key={group.label}
            group={group}
            pathname={pathname}
            open={openGroups.includes(group.label)}
            onToggle={() => toggle(group.label)}
          />
        ))}
      </nav>
    </aside>
  );
}
