"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { newMenuGroups } from "@/config/navigation";

/** The "+ New" button at the top of the sidebar. Opens a menu grouped in columns. */
export function NewMenuButton() {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative px-1">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-center gap-2 rounded-full border border-white/30 py-2 text-sm font-semibold text-white hover:bg-sidebar-hover"
      >
        <Plus size={18} /> New
      </button>
      {open && (
        <>
          {/* Clicking anywhere outside closes the menu */}
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-1 z-20 mt-2 flex w-[520px] gap-6 rounded-md bg-white p-4 shadow-xl">
            {newMenuGroups.map((group) => (
              <div key={group.title} className="min-w-0 flex-1">
                <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">{group.title}</div>
                {group.links.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setOpen(false)}
                    className="block rounded px-2 py-1.5 text-sm text-gray-700 hover:bg-brand-50"
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
