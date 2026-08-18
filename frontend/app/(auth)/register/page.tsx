"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { AuthShell } from "@/components/auth/auth-shell";
import { FormField } from "@/components/ui/form-field";
import { SubmitButton } from "@/components/ui/submit-button";
import { fieldError, toApiError } from "@/lib/api/client";
import { register as registerAccount } from "@/services/auth";

const registrationSchema = z.object({
  full_name: z.string().trim().min(1, "Enter your name.").max(255),
  email: z.email("Enter a valid email address."),
  password: z.string().min(8, "Use at least 8 characters.").max(128),
});

type RegistrationValues = z.infer<typeof registrationSchema>;

export default function RegistrationPage() {
  const router = useRouter();
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<RegistrationValues>({ resolver: zodResolver(registrationSchema) });

  const submit = handleSubmit(async (values) => {
    try {
      await registerAccount(values);
      router.replace("/login?registered=1");
    } catch (error) {
      for (const field of ["full_name", "email", "password"] as const) {
        const message = fieldError(error, field);
        if (message) setError(field, { message });
      }
      toast.error(toApiError(error).message);
    }
  });

  return (
    <AuthShell eyebrow="Create your account" title="Build a trusted knowledge hub" description="Start with your profile. You can create or join an organization next.">
      <form className="space-y-5" noValidate onSubmit={submit}>
        <FormField autoComplete="name" error={errors.full_name?.message} label="Full name" {...register("full_name")} />
        <FormField autoComplete="email" error={errors.email?.message} label="Email" type="email" {...register("email")} />
        <FormField autoComplete="new-password" error={errors.password?.message} hint="Use a strong password that you do not reuse elsewhere." label="Password" type="password" {...register("password")} />
        <SubmitButton busy={isSubmitting}>Create account</SubmitButton>
      </form>
      <p className="mt-7 text-center text-sm text-slate-600">Already have an account? <Link className="font-semibold text-teal-700 hover:text-teal-900" href="/login">Sign in</Link></p>
    </AuthShell>
  );
}
