"use client";

import { LoaderCircle } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/components/providers/auth-provider";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [pathname, router, status]);

  if (status !== "authenticated") {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-50" aria-live="polite">
        <div className="flex items-center gap-3 text-sm font-medium text-slate-600">
          <LoaderCircle aria-hidden className="size-5 animate-spin text-teal-600" /> Restoring your secure session…
        </div>
      </main>
    );
  }

  return children;
}
