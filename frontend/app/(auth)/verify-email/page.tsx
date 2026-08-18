"use client";

import { CircleCheck, CircleX, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { AuthShell } from "@/components/auth/auth-shell";
import { confirmEmailVerification } from "@/services/auth";

type VerificationState = "working" | "verified" | "invalid";

function VerificationResult() {
  const token = useSearchParams().get("token");
  const [state, setState] = useState<VerificationState>(token ? "working" : "invalid");

  useEffect(() => {
    if (!token) return;
    let active = true;
    void confirmEmailVerification(token)
      .then(() => { if (active) setState("verified"); })
      .catch(() => { if (active) setState("invalid"); });
    return () => { active = false; };
  }, [token]);

  return (
    <AuthShell eyebrow="Email verification" title={state === "verified" ? "Email verified" : state === "invalid" ? "Link unavailable" : "Verifying your email"} description={state === "verified" ? "Your account email is confirmed and ready to use." : state === "invalid" ? "This link is invalid, expired, or has already been used." : "Please wait while we validate your secure link."}>
      <div className="rounded-2xl border border-slate-200 bg-white p-7 text-center shadow-sm" aria-live="polite">
        {state === "working" && <LoaderCircle aria-hidden className="mx-auto size-10 animate-spin text-teal-600" />}
        {state === "verified" && <CircleCheck aria-hidden className="mx-auto size-10 text-emerald-600" />}
        {state === "invalid" && <CircleX aria-hidden className="mx-auto size-10 text-rose-600" />}
        <Link className="mt-6 inline-flex min-h-11 items-center rounded-xl bg-slate-950 px-5 text-sm font-semibold text-white" href={state === "verified" ? "/login" : "/dashboard"}>{state === "verified" ? "Continue to sign in" : "Open account settings"}</Link>
      </div>
    </AuthShell>
  );
}

export default function VerifyEmailPage() {
  return <Suspense fallback={<div className="min-h-screen bg-slate-50" />}><VerificationResult /></Suspense>;
}
