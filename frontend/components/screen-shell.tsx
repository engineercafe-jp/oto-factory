import type { ReactNode } from "react";

interface ScreenShellProps {
  hero: ReactNode;
  children: ReactNode;
}

export function ScreenShell({ hero, children }: ScreenShellProps) {
  return (
    <main className="screen-shell">
      <div className="screen-shell__glow screen-shell__glow--left" aria-hidden="true" />
      <div className="screen-shell__glow screen-shell__glow--right" aria-hidden="true" />
      <section className="screen-shell__hero">{hero}</section>
      <section className="screen-shell__content">{children}</section>
    </main>
  );
}
