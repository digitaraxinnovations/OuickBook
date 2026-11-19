"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { newMenu } from "@/config/navigation";

/** The "+ New" button at the top of the sidebar. */
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
        <div className="absolute left-1 right-1 z-20 mt-2 rounded-md bg-white py-1 shadow-lg">
          {newMenu.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setOpen(false)}
              className="block px-4 py-2 text-sm text-gray-700 hover:bg-brand-50"
            >
              {item.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
