"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { AuthShell } from "@/components/auth/auth-shell";
import { FormField } from "@/components/ui/form-field";
import { SubmitButton } from "@/components/ui/submit-button";
import { fieldError, toApiError } from "@/lib/api/client";
import { confirmPasswordReset } from "@/services/auth";

const schema = z.object({
  password: z.string().min(8, "Use at least 8 characters.").max(128),
  confirmation: z.string().min(1, "Confirm your new password."),
}).refine((value) => value.password === value.confirmation, {
  message: "The passwords do not match.",
  path: ["confirmation"],
});

type Values = z.infer<typeof schema>;

function ResetPasswordForm() {
  const router = useRouter();
  const token = useSearchParams().get("token");
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<Values>({ resolver: zodResolver(schema) });

  const submit = handleSubmit(async (values) => {
    if (!token) return;
    try {
      await confirmPasswordReset({ token, new_password: values.password, new_password_confirmation: values.confirmation });
      router.replace("/login?reset=1");
    } catch (error) {
      const tokenMessage = fieldError(error, "token");
      const passwordMessage = fieldError(error, "new_password");
      if (passwordMessage) setError("password", { message: passwordMessage });
      toast.error(tokenMessage ?? toApiError(error).message);
    }
  });

  return (
    <AuthShell eyebrow="Secure recovery" title="Choose a new password" description="This link is single-use and expires one hour after it was requested.">
      {!token ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900" role="alert">This recovery link is incomplete. Request a new password-reset email.</div>
      ) : (
        <form className="space-y-5" noValidate onSubmit={submit}>
          <FormField autoComplete="new-password" error={errors.password?.message} label="New password" type="password" {...register("password")} />
          <FormField autoComplete="new-password" error={errors.confirmation?.message} label="Confirm new password" type="password" {...register("confirmation")} />
          <SubmitButton busy={isSubmitting}>Update password</SubmitButton>
        </form>
      )}
      <p className="mt-7 text-center text-sm text-slate-600"><Link className="font-semibold text-teal-700" href="/forgot-password">Request another link</Link></p>
    </AuthShell>
  );
}

export default function ResetPasswordPage() {
  return <Suspense fallback={<div className="min-h-screen bg-slate-50" />}><ResetPasswordForm /></Suspense>;
}
