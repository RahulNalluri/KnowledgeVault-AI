import { LoaderCircle } from "lucide-react";

import { Button } from "@/components/ui/button";

export function SubmitButton({
  busy,
  children,
}: {
  busy: boolean;
  children: React.ReactNode;
}) {
  return (
    <Button className="w-full" disabled={busy} type="submit">
      {busy && <LoaderCircle aria-hidden className="size-4 animate-spin" />}
      {children}
    </Button>
  );
}
