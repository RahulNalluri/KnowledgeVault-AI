"use client";

import { ArrowRight, BookOpen, CircleCheck, FileText } from "lucide-react";
import Link from "next/link";

import { useAuth } from "@/components/providers/auth-provider";

export default function DashboardPage() {
  const { user } = useAuth();
  return (
    <div className="mx-auto max-w-6xl">
      <p className="text-sm font-medium text-teal-700">Workspace overview</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Welcome, {user?.full_name.split(" ")[0]}</h1>
      <p className="mt-3 max-w-2xl leading-7 text-slate-600">Your secure account foundation is ready. Organization and knowledge-base tools arrive in the next phase.</p>
      {!user?.is_email_verified && (
        <Link href="/settings/profile" className="mt-7 flex items-center justify-between rounded-2xl border border-amber-200 bg-amber-50 p-5 text-amber-950">
          <div><p className="font-semibold">Verify your email</p><p className="mt-1 text-sm text-amber-800">Confirm your address before inviting teammates.</p></div><ArrowRight aria-hidden className="size-5" />
        </Link>
      )}
      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        {[{ icon: BookOpen, label: "Knowledge bases", value: "Coming next" }, { icon: FileText, label: "Documents", value: "No uploads yet" }, { icon: CircleCheck, label: "Account", value: user?.is_email_verified ? "Verified" : "Verification pending" }].map(({ icon: Icon, label, value }) => (
          <div key={label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><Icon aria-hidden className="size-5 text-teal-600" /><p className="mt-6 text-sm text-slate-500">{label}</p><p className="mt-1 font-semibold text-slate-950">{value}</p></div>
        ))}
      </div>
    </div>
  );
}
