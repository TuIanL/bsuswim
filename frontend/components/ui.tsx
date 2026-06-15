import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";

type SectionProps = {
  id?: string;
  eyebrow?: string;
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
};

export function Section({
  id,
  eyebrow,
  title,
  description,
  children,
  className = ""
}: SectionProps) {
  return (
    <section id={id} className={`section-border px-5 py-20 sm:px-8 lg:py-28 ${className}`}>
      <div className="mx-auto max-w-7xl">
        {(eyebrow || title || description) && (
          <div className="mx-auto mb-14 max-w-3xl text-center">
            {eyebrow ? <Eyebrow>{eyebrow}</Eyebrow> : null}
            {title ? (
              <h2 className="mt-4 text-3xl font-black uppercase tracking-widest text-white sm:text-5xl">
                {title}
              </h2>
            ) : null}
            {description ? (
              <p className="mx-auto mt-5 max-w-2xl text-sm leading-7 text-brand-light sm:text-base">
                {description}
              </p>
            ) : null}
          </div>
        )}
        {children}
      </div>
    </section>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <p className="text-xs font-bold uppercase tracking-ultra text-brand-light">
      {children}
    </p>
  );
}

type ButtonBaseProps = {
  variant?: "solid" | "outline";
};

type AnchorButtonProps = AnchorHTMLAttributes<HTMLAnchorElement> &
  ButtonBaseProps & {
    children: ReactNode;
  };

export function AnchorButton({
  children,
  variant = "solid",
  className = "",
  ...props
}: AnchorButtonProps) {
  const styles =
    variant === "solid"
      ? "border-white bg-white text-black hover:bg-transparent hover:text-white"
      : "border-white/70 bg-transparent text-white hover:bg-white hover:text-black";

  return (
    <a
      className={`inline-flex min-h-11 items-center justify-center border px-6 text-xs font-black uppercase tracking-widest transition ${styles} ${className}`}
      {...props}
    >
      {children}
    </a>
  );
}

type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  children: ReactNode;
};

export function IconButton({ label, children, className = "", ...props }: IconButtonProps) {
  return (
    <button
      aria-label={label}
      title={label}
      className={`inline-flex size-11 items-center justify-center border border-white/20 bg-black/40 text-white transition hover:border-white hover:bg-white hover:text-black ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function MediaFrame({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`relative overflow-hidden border border-white/15 bg-brand-dark ${className}`}>
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.045)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px)] bg-[size:42px_42px]" />
      {children}
    </div>
  );
}

export function Divider() {
  return <div className="h-px w-full bg-white/10" />;
}
