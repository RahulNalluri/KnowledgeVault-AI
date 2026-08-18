import { ArrowRight, BookOpenCheck, ShieldCheck } from "lucide-react";
import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-6">
        <Link className="flex items-center gap-3 font-semibold" href="/">
          <span className="grid size-10 place-items-center rounded-xl bg-teal-400 text-slate-950">
            <BookOpenCheck aria-hidden className="size-5" />
          </span>
          KnowledgeVault AI
        </Link>
        <div className="flex items-center gap-2">
          <Link className="rounded-xl px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-white/10" href="/login">
            Sign in
          </Link>
          <Link className="rounded-xl bg-teal-400 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-teal-300" href="/register">
            Create account
          </Link>
        </div>
      </nav>
      <section className="mx-auto grid max-w-7xl gap-14 px-6 pb-24 pt-20 lg:grid-cols-[1.1fr_0.9fr] lg:pt-32">
        <div>
          <p className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-sm text-teal-200">
            <ShieldCheck aria-hidden className="size-4" /> Secure by architecture
          </p>
          <h1 className="mt-7 max-w-4xl text-balance text-5xl font-semibold leading-tight tracking-tight sm:text-7xl">
            Answers your team can verify.
          </h1>
          <p className="mt-7 max-w-2xl text-lg leading-8 text-slate-300">
            Turn private documents into a searchable knowledge layer with grounded AI answers and precise source citations.
          </p>
          <Link className="mt-10 inline-flex items-center gap-2 rounded-xl bg-teal-400 px-5 py-3 font-semibold text-slate-950 hover:bg-teal-300" href="/register">
            Start building <ArrowRight aria-hidden className="size-4" />
          </Link>
        </div>
      </section>
    </main>
  );
}
