"use client";

import { Bell, Building2, Check, ChevronDown, Clock, LogOut, Plus, Search } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { formatDate, formatMoney } from "@/lib/format";
import { platformService } from "@/services";
import { AppNotification, RecentTransaction, SearchResult } from "@/types/models";

/** Closes a dropdown when the user clicks anywhere else. */
function useClickOutside(onOutside: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    function handle(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        onOutside();
      }
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, [onOutside]);
  return ref;
}

function CompanySwitcher() {
  const { company, companies, switchCompany, createCompany } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const ref = useClickOutside(() => setOpen(false));

  async function choose(companyId: number) {
    setOpen(false);
    await switchCompany(companyId);
    router.push("/dashboard");
  }

  async function addCompany() {
    const name = window.prompt("Name of the new company:");
    if (name && name.trim()) {
      setOpen(false);
      await createCompany(name.trim());
      router.push("/dashboard");
    }
  }

  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen(!open)} className="flex max-w-56 shrink-0 items-center gap-2 whitespace-nowrap rounded px-2 py-1 text-sm font-semibold text-gray-800 hover:bg-gray-100">
        <Building2 size={16} className="shrink-0" /> <span className="truncate">{company?.name}</span> <ChevronDown size={14} className="shrink-0" />
      </button>
      {open && (
        <div className="absolute left-0 z-30 mt-1 w-72 rounded-md border border-gray-200 bg-white py-1 shadow-lg">
          {companies.map((item) => (
            <button key={item.company_id} onClick={() => choose(item.company_id)} className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-gray-50">
              <span>{item.company_name}</span>
              {item.is_current && <Check size={14} className="text-brand-600" />}
            </button>
          ))}
          <button onClick={addCompany} className="flex w-full items-center gap-2 border-t border-gray-100 px-3 py-2 text-left text-sm text-brand-700 hover:bg-gray-50">
            <Plus size={14} /> Add a company
          </button>
        </div>
      )}
    </div>
  );
}

function GlobalSearch() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useClickOutside(() => setOpen(false));

  // Search a moment after the user stops typing.
  useEffect(() => {
    if (text.trim().length < 2) {
      setResults([]);
      return;
    }
    const timer = setTimeout(() => {
      platformService
        .search(text)
        .then((found) => {
          setResults(found);
          setOpen(true);
        })
        .catch(() => setResults([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [text]);

  function go(result: SearchResult) {
    setOpen(false);
    setText("");
    router.push(result.href);
  }

  return (
    <div ref={ref} className="relative w-full max-w-md">
      <Search size={16} className="absolute top-2 left-3 text-gray-400" />
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        onFocus={() => results.length > 0 && setOpen(true)}
        placeholder="Search customers, vendors, invoices, amounts..."
        className="w-full rounded-md border border-gray-300 py-1.5 pr-3 pl-9 text-sm focus:border-brand-500 focus:outline-none"
      />
      {open && (
        <div className="absolute z-30 mt-1 max-h-96 w-full overflow-y-auto rounded-md border border-gray-200 bg-white py-1 shadow-lg">
          {results.length === 0 && <div className="px-3 py-2 text-sm text-gray-500">Nothing found.</div>}
          {results.map((result, index) => (
            <button key={index} onClick={() => go(result)} className="block w-full px-3 py-2 text-left hover:bg-gray-50">
              <div className="text-sm">
                <span className="mr-2 rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">{result.kind}</span>
                {result.title}
              </div>
              {result.subtitle && <div className="text-xs text-gray-500">{result.subtitle}</div>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function RecentMenu() {
  const { company } = useAuth();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<RecentTransaction[] | null>(null);
  const ref = useClickOutside(() => setOpen(false));

  async function toggle() {
    if (!open) {
      setItems(await platformService.recent().catch(() => []));
    }
    setOpen(!open);
  }

  return (
    <div ref={ref} className="relative">
      <button onClick={toggle} className="rounded p-1.5 text-gray-500 hover:bg-gray-100" title="Recent transactions" aria-label="Recent transactions">
        <Clock size={18} />
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-1 w-96 rounded-md border border-gray-200 bg-white py-1 shadow-lg">
          <div className="px-3 py-1 text-xs font-semibold uppercase text-gray-500">Recent transactions</div>
          {(items || []).length === 0 && <div className="px-3 py-2 text-sm text-gray-500">No transactions yet.</div>}
          {(items || []).map((item, index) => {
            const content = (
              <div className="flex items-center justify-between gap-3 px-3 py-2 text-sm hover:bg-gray-50">
                <div>
                  <div>
                    {item.type_label} {item.number}
                  </div>
                  <div className="text-xs text-gray-500">
                    {formatDate(item.entry_date)} · {item.name}
                  </div>
                </div>
                <div className="font-medium">{formatMoney(item.amount, company?.currency)}</div>
              </div>
            );
            return item.href ? (
              <Link key={index} href={item.href} onClick={() => setOpen(false)}>
                {content}
              </Link>
            ) : (
              <div key={index}>{content}</div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function NotificationBell() {
  const [items, setItems] = useState<AppNotification[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useClickOutside(() => setOpen(false));

  useEffect(() => {
    platformService
      .notifications()
      .then(setItems)
      .catch(() => setItems([]));
  }, []);

  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen(!open)} className="relative rounded p-1.5 text-gray-500 hover:bg-gray-100" title="Notifications" aria-label="Notifications">
        <Bell size={18} />
        {items.length > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-bold text-white">
            {items.length}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-1 w-80 rounded-md border border-gray-200 bg-white py-1 shadow-lg">
          <div className="px-3 py-1 text-xs font-semibold uppercase text-gray-500">Needs your attention</div>
          {items.length === 0 && <div className="px-3 py-2 text-sm text-gray-500">All caught up.</div>}
          {items.map((item) => (
            <Link key={item.kind + item.message} href={item.href} onClick={() => setOpen(false)} className="block px-3 py-2 text-sm hover:bg-gray-50">
              <span className={item.level === "warning" ? "text-amber-700" : "text-gray-700"}>{item.message}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function TopBar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  return (
    <header className="no-print flex h-14 items-center justify-between gap-4 border-b border-gray-200 bg-white px-6">
      <CompanySwitcher />
      <GlobalSearch />
      <div className="flex items-center gap-3 text-sm text-gray-600">
        <NotificationBell />
        <RecentMenu />
        <span className="hidden whitespace-nowrap lg:inline">{user?.full_name}</span>
        <button onClick={handleLogout} className="flex items-center gap-1 rounded px-2 py-1 hover:bg-gray-100" title="Sign out">
          <LogOut size={16} /> <span className="whitespace-nowrap">Sign out</span>
        </button>
      </div>
    </header>
  );
}
