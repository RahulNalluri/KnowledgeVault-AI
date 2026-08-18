"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, MailCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { AuthShell } from "@/components/auth/auth-shell";
import { FormField } from "@/components/ui/form-field";
import { SubmitButton } from "@/components/ui/submit-button";
import { toApiError } from "@/lib/api/client";
import { requestPasswordReset } from "@/services/auth";

const schema = z.object({ email: z.email("Enter a valid email address.") });
type Values = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Values>({ resolver: zodResolver(schema) });

  const submit = handleSubmit(async ({ email }) => {
    try {
      await requestPasswordReset(email);
      setSent(true);
    } catch (error) {
      toast.error(toApiError(error).message);
    }
  });

  return (
    <AuthShell eyebrow="Account recovery" title="Reset your password" description="Enter your account email. We will send recovery instructions if an active account exists.">
      {sent ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6 text-center" role="status">
          <MailCheck aria-hidden className="mx-auto size-9 text-emerald-700" />
          <h2 className="mt-4 font-semibold text-emerald-950">Check your inbox</h2>
          <p className="mt-2 text-sm leading-6 text-emerald-800">If an active account exists for that email, a secure one-hour recovery link is on its way.</p>
        </div>
      ) : (
        <form className="space-y-5" noValidate onSubmit={submit}>
          <FormField autoComplete="email" error={errors.email?.message} label="Email" type="email" {...register("email")} />
          <SubmitButton busy={isSubmitting}>Send recovery link</SubmitButton>
        </form>
      )}
      <Link className="mt-7 flex items-center justify-center gap-2 text-sm font-semibold text-teal-700 hover:text-teal-900" href="/login"><ArrowLeft aria-hidden className="size-4" /> Back to sign in</Link>
    </AuthShell>
  );
}
