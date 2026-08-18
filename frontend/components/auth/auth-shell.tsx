import { BookOpenCheck, LockKeyhole, Sparkles } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

export function AuthShell({
  children,
  eyebrow,
  title,
  description,
}: {
  children: ReactNode;
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <main className="grid min-h-screen lg:grid-cols-[1.05fr_0.95fr]">
      <section className="relative hidden overflow-hidden bg-slate-950 px-12 py-10 text-white lg:flex lg:flex-col">
        <div className="absolute inset-0 auth-grid opacity-25" />
        <div className="absolute -right-40 top-32 size-96 rounded-full bg-teal-400/20 blur-3xl" />
        <Link className="relative flex items-center gap-3 font-semibold" href="/">
          <span className="grid size-10 place-items-center rounded-xl bg-teal-400 text-slate-950">
            <BookOpenCheck aria-hidden className="size-5" />
          </span>
          KnowledgeVault AI
        </Link>
        <div className="relative my-auto max-w-xl">
          <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-teal-200">
            <Sparkles aria-hidden className="size-3.5" /> Private knowledge, useful answers
          </p>
          <h2 className="text-balance text-5xl font-semibold leading-[1.08] tracking-tight">
            Your team&apos;s knowledge, grounded and secure.
          </h2>
          <p className="mt-6 max-w-lg text-lg leading-8 text-slate-300">
            Build trusted knowledge bases, ask better questions, and trace every answer back to
            its source.
          </p>
        </div>
        <p className="relative flex items-center gap-2 text-sm text-slate-400">
          <LockKeyhole aria-hidden className="size-4 text-teal-300" /> Short-lived access tokens.
          Protected refresh sessions.
        </p>
      </section>

      <section className="flex min-h-screen items-center justify-center bg-slate-50 px-5 py-10 sm:px-8">
        <div className="w-full max-w-md">
          <Link className="mb-10 flex items-center gap-3 font-semibold text-slate-950 lg:hidden" href="/">
            <span className="grid size-9 place-items-center rounded-xl bg-teal-500 text-slate-950">
              <BookOpenCheck aria-hidden className="size-5" />
            </span>
            KnowledgeVault AI
          </Link>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-700">{eyebrow}</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{title}</h1>
          <p className="mt-3 leading-7 text-slate-600">{description}</p>
          <div className="mt-8">{children}</div>
        </div>
      </section>
    </main>
  );
}
