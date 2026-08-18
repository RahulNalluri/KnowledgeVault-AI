"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { BadgeCheck, KeyRound, Mail } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/ui/form-field";
import { SubmitButton } from "@/components/ui/submit-button";
import { fieldError, toApiError } from "@/lib/api/client";
import {
  changePassword,
  resendEmailVerification,
  updateCurrentUser,
} from "@/services/auth";

const profileSchema = z.object({
  full_name: z.string().trim().min(1, "Enter your name.").max(255),
});

const passwordSchema = z
  .object({
    current_password: z.string().min(1, "Enter your current password.").max(128),
    new_password: z.string().min(8, "Use at least 8 characters.").max(128),
    new_password_confirmation: z.string().min(1, "Confirm your new password."),
  })
  .refine((value) => value.new_password === value.new_password_confirmation, {
    message: "The passwords do not match.",
    path: ["new_password_confirmation"],
  });

type ProfileValues = z.infer<typeof profileSchema>;
type PasswordValues = z.infer<typeof passwordSchema>;

export default function ProfileSettingsPage() {
  const { user, setUser, logout } = useAuth();
  const profileForm = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    values: { full_name: user?.full_name ?? "" },
  });
  const passwordForm = useForm<PasswordValues>({ resolver: zodResolver(passwordSchema) });

  const saveProfile = profileForm.handleSubmit(async ({ full_name }) => {
    try {
      const updated = await updateCurrentUser(full_name);
      setUser(updated);
      toast.success("Profile updated.");
    } catch (error) {
      const message = fieldError(error, "full_name");
      if (message) profileForm.setError("full_name", { message });
      toast.error(toApiError(error).message);
    }
  });

  const savePassword = passwordForm.handleSubmit(async (values) => {
    try {
      await changePassword(values);
      toast.success("Password changed. Sign in again to continue.");
      await logout();
    } catch (error) {
      for (const field of [
        "current_password",
        "new_password",
        "new_password_confirmation",
      ] as const) {
        const message = fieldError(error, field);
        if (message) passwordForm.setError(field, { message });
      }
      toast.error(toApiError(error).message);
    }
  });

  const resend = async () => {
    try {
      const response = await resendEmailVerification();
      toast.success(response.message);
    } catch (error) {
      toast.error(toApiError(error).message);
    }
  };

  return (
    <div className="mx-auto max-w-3xl">
      <p className="text-sm font-medium text-teal-700">Account settings</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
        Profile & security
      </h1>
      <p className="mt-3 leading-7 text-slate-600">
        Manage your identity and keep access to your vault protected.
      </p>

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-7">
        <div className="flex items-start gap-3">
          <Mail aria-hidden className="mt-0.5 size-5 text-teal-600" />
          <div className="min-w-0 flex-1">
            <h2 className="font-semibold text-slate-950">Email address</h2>
            <p className="mt-1 truncate text-sm text-slate-600">{user?.email}</p>
          </div>
          {user?.is_email_verified ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
              <BadgeCheck aria-hidden className="size-3.5" /> Verified
            </span>
          ) : (
            <Button onClick={() => void resend()} variant="secondary">
              Resend link
            </Button>
          )}
        </div>
      </section>

      <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-7">
        <h2 className="text-lg font-semibold text-slate-950">Personal details</h2>
        <form className="mt-5 space-y-5" noValidate onSubmit={saveProfile}>
          <FormField
            autoComplete="name"
            error={profileForm.formState.errors.full_name?.message}
            label="Full name"
            {...profileForm.register("full_name")}
          />
          <SubmitButton busy={profileForm.formState.isSubmitting}>Save profile</SubmitButton>
        </form>
      </section>

      <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-7">
        <div className="flex items-center gap-3">
          <KeyRound aria-hidden className="size-5 text-teal-600" />
          <h2 className="text-lg font-semibold text-slate-950">Change password</h2>
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Changing your password signs out every active session, including this one.
        </p>
        <form className="mt-5 space-y-5" noValidate onSubmit={savePassword}>
          <FormField
            autoComplete="current-password"
            error={passwordForm.formState.errors.current_password?.message}
            label="Current password"
            type="password"
            {...passwordForm.register("current_password")}
          />
          <FormField
            autoComplete="new-password"
            error={passwordForm.formState.errors.new_password?.message}
            label="New password"
            type="password"
            {...passwordForm.register("new_password")}
          />
          <FormField
            autoComplete="new-password"
            error={passwordForm.formState.errors.new_password_confirmation?.message}
            label="Confirm new password"
            type="password"
            {...passwordForm.register("new_password_confirmation")}
          />
          <SubmitButton busy={passwordForm.formState.isSubmitting}>Change password</SubmitButton>
        </form>
      </section>
    </div>
  );
}
