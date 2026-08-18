"use client";

import { BookOpenCheck, LayoutDashboard, LogOut, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const links = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/settings/profile", label: "Profile & security", icon: Settings },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen bg-slate-50 lg:grid lg:grid-cols-[260px_1fr]">
      <aside className="border-b border-slate-200 bg-white lg:min-h-screen lg:border-b-0 lg:border-r">
        <div className="flex h-20 items-center justify-between px-5 lg:px-6">
          <Link className="flex items-center gap-3 font-semibold text-slate-950" href="/dashboard">
            <span className="grid size-9 place-items-center rounded-xl bg-teal-500 text-slate-950"><BookOpenCheck aria-hidden className="size-5" /></span>
            KnowledgeVault
          </Link>
        </div>
        <nav aria-label="Application" className="flex gap-2 overflow-x-auto px-4 pb-4 lg:block lg:space-y-1 lg:pb-0">
          {links.map(({ href, icon: Icon, label }) => (
            <Link key={href} href={href} className={cn("flex min-w-max items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium", pathname === href ? "bg-slate-950 text-white" : "text-slate-600 hover:bg-slate-100 hover:text-slate-950")}>
              <Icon aria-hidden className="size-4" /> {label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto hidden border-t border-slate-200 p-4 lg:absolute lg:bottom-0 lg:block lg:w-[259px]">
          <p className="truncate px-2 text-sm font-medium text-slate-800">{user?.full_name}</p>
          <p className="truncate px-2 text-xs text-slate-500">{user?.email}</p>
          <Button className="mt-3 w-full justify-start" onClick={() => void logout()} variant="ghost"><LogOut aria-hidden className="size-4" /> Sign out</Button>
        </div>
      </aside>
      <main className="px-5 py-8 sm:px-8 lg:px-12 lg:py-10">{children}</main>
    </div>
  );
}
