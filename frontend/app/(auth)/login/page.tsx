"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { AuthShell } from "@/components/auth/auth-shell";
import { useAuth } from "@/components/providers/auth-provider";
import { FormField } from "@/components/ui/form-field";
import { SubmitButton } from "@/components/ui/submit-button";
import { fieldError, toApiError } from "@/lib/api/client";

const loginSchema = z.object({
  email: z.email("Enter a valid email address."),
  password: z.string().min(1, "Enter your password.").max(128),
});

type LoginValues = z.infer<typeof loginSchema>;

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });

  const submit = handleSubmit(async (values) => {
    try {
      await login(values);
      toast.success("Welcome back.");
      const next = searchParams.get("next");
      router.replace(next?.startsWith("/") && !next.startsWith("//") ? next : "/dashboard");
    } catch (error) {
      const emailError = fieldError(error, "email");
      if (emailError) setError("email", { message: emailError });
      toast.error(toApiError(error).message);
    }
  });

  return (
    <AuthShell eyebrow="Welcome back" title="Sign in to your vault" description="Continue to your private workspaces and knowledge bases.">
      {searchParams.get("registered") && (
        <p className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800" role="status">
          Account created. Check your inbox to verify your email, then sign in.
        </p>
      )}
      {searchParams.get("reset") && (
        <p className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800" role="status">
          Password updated. Sign in with your new password.
        </p>
      )}
      <form className="space-y-5" noValidate onSubmit={submit}>
        <FormField autoComplete="email" error={errors.email?.message} label="Email" type="email" {...register("email")} />
        <div>
          <FormField error={errors.password?.message} label="Password" autoComplete="current-password" type="password" {...register("password")} />
          <div className="mt-2 text-right">
            <Link className="text-sm font-medium text-teal-700 hover:text-teal-900" href="/forgot-password">Forgot password?</Link>
          </div>
        </div>
        <SubmitButton busy={isSubmitting}>Sign in</SubmitButton>
      </form>
      <p className="mt-7 text-center text-sm text-slate-600">New to KnowledgeVault? <Link className="font-semibold text-teal-700 hover:text-teal-900" href="/register">Create an account</Link></p>
    </AuthShell>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-50" />}>
      <LoginForm />
    </Suspense>
  );
}
