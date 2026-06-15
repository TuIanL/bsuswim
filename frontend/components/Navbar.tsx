"use client";

import { Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import { navLinks } from "@/lib/content";
import { AnchorButton, IconButton } from "@/components/ui";

export function Navbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 border-b transition ${
        scrolled
          ? "border-white/10 bg-black/75 shadow-white-glow backdrop-blur-xl"
          : "border-transparent bg-transparent"
      }`}
    >
      <nav className="mx-auto flex h-20 max-w-7xl items-center justify-between px-5 sm:px-8">
        <a href="#top" className="group flex items-center gap-3" aria-label="智泳云枢首页">
          <span className="grid size-8 place-items-center border border-white text-[10px] font-black tracking-widest">
            ZY
          </span>
          <span>
            <span className="block text-sm font-black tracking-widest text-white">智泳云枢</span>
            <span className="block text-[9px] font-bold uppercase tracking-ultra text-brand-light">
              SmartSwim Axis
            </span>
          </span>
        </a>

        <div className="hidden items-center gap-8 lg:flex">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-[11px] font-bold uppercase tracking-ultra text-brand-light transition hover:text-white"
            >
              {link.label}
            </a>
          ))}
        </div>

        <div className="hidden lg:block">
          <AnchorButton href="/platform" variant="outline" className="min-h-10 px-5">
            Start Analysis
          </AnchorButton>
        </div>

        <div className="lg:hidden">
          <IconButton label={open ? "关闭菜单" : "打开菜单"} onClick={() => setOpen((value) => !value)}>
            {open ? <X size={18} /> : <Menu size={18} />}
          </IconButton>
        </div>
      </nav>

      {open ? (
        <div className="border-t border-white/10 bg-black/95 px-5 py-5 backdrop-blur-xl lg:hidden">
          <div className="mx-auto flex max-w-7xl flex-col gap-4">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="border-b border-white/10 py-3 text-xs font-bold uppercase tracking-ultra text-brand-light transition hover:text-white"
              >
                {link.label}
              </a>
            ))}
            <AnchorButton href="/platform" onClick={() => setOpen(false)}>
              Start Analysis
            </AnchorButton>
          </div>
        </div>
      ) : null}
    </header>
  );
}
