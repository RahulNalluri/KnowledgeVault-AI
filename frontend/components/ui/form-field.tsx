import { forwardRef, type InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: string;
}

export const FormField = forwardRef<HTMLInputElement, FormFieldProps>(
  ({ className, error, hint, id, label, ...props }, ref) => {
    const inputId = id ?? props.name;
    const descriptionId = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined;
    return (
      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-800" htmlFor={inputId}>
          {label}
        </label>
        <input
          ref={ref}
          id={inputId}
          aria-describedby={descriptionId}
          aria-invalid={Boolean(error)}
          className={cn(
            "min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3.5 text-sm text-slate-950 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-teal-600 focus:ring-3 focus:ring-teal-100",
            error && "border-rose-500 focus:border-rose-500 focus:ring-rose-100",
            className,
          )}
          {...props}
        />
        {error ? (
          <p className="text-sm text-rose-700" id={descriptionId} role="alert">
            {error}
          </p>
        ) : hint ? (
          <p className="text-xs leading-5 text-slate-500" id={descriptionId}>
            {hint}
          </p>
        ) : null}
      </div>
    );
  },
);

FormField.displayName = "FormField";
