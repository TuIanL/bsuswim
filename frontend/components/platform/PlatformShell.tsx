"use client";

import { Activity, BarChart3, ClipboardCheck, Home, Menu, Upload, Waves, X } from "lucide-react";
import { useState, type ReactNode } from "react";
import type { SwimPlatformView } from "@/lib/swim-types";

export type PlatformNavItem = {
  id: SwimPlatformView;
  label: string;
  shortLabel: string;
  Icon: typeof Home;
};

export const platformNavigation: PlatformNavItem[] = [
  { id: "upload", label: "视频分析", shortLabel: "上传", Icon: Upload },
  { id: "tasks", label: "任务管理", shortLabel: "任务", Icon: Activity },
  { id: "workspace", label: "视觉工作台", shortLabel: "工作台", Icon: Waves },
  { id: "report", label: "分析报告", shortLabel: "报告", Icon: BarChart3 },
  { id: "training", label: "训练反馈", shortLabel: "训练", Icon: ClipboardCheck }
];

interface PlatformShellProps {
  activeView: SwimPlatformView;
  children: ReactNode;
  onNavigate: (view: SwimPlatformView) => void;
}

export function PlatformShell({ activeView, children, onNavigate }: PlatformShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleNavigate = (view: SwimPlatformView) => {
    onNavigate(view);
    setMobileOpen(false);
  };

  return (
    <div className="min-h-screen overflow-x-hidden bg-brand-black text-white">
      <header className="sticky top-0 z-50 border-b border-white/10 bg-black/85 backdrop-blur-xl">
        <div className="mx-auto flex h-20 max-w-[1480px] items-center gap-4 px-5 sm:px-8">
          <a className="group flex min-w-0 items-center gap-3" href="/" aria-label="返回智泳云枢首页">
            <span className="grid size-10 shrink-0 place-items-center border border-white/30 text-xs font-black tracking-widest transition group-hover:border-white">
              ZY
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-black tracking-widest">智泳云枢</span>
              <span className="block truncate text-[9px] font-bold uppercase tracking-ultra text-brand-light">
                Swim Analysis Platform
              </span>
            </span>
          </a>

          <nav className="hidden flex-1 justify-center xl:flex" aria-label="分析平台导航">
            <div className="flex items-center gap-px border border-white/10 bg-white/[0.03] p-1">
              {platformNavigation.map(({ id, label, Icon }) => (
                <button
                  className={`inline-flex min-h-10 items-center gap-2 px-4 text-[11px] font-black uppercase tracking-widest transition ${
                    activeView === id
                      ? "bg-white text-black"
                      : "text-brand-light hover:bg-white/10 hover:text-white"
                  }`}
                  key={id}
                  onClick={() => handleNavigate(id)}
                  type="button"
                >
                  <Icon size={15} aria-hidden="true" />
                  {label}
                </button>
              ))}
            </div>
          </nav>

          <div className="ml-auto hidden items-center gap-2 md:flex">
            <a
              className="inline-flex min-h-10 items-center gap-2 border border-white/15 px-4 text-[11px] font-black uppercase tracking-widest text-brand-light transition hover:border-white hover:text-white"
              href="/"
            >
              <Home size={15} aria-hidden="true" />
              官网首页
            </a>
            <button
              className="inline-flex min-h-10 items-center gap-2 border border-white bg-white px-4 text-[11px] font-black uppercase tracking-widest text-black transition hover:bg-transparent hover:text-white"
              onClick={() => handleNavigate("upload")}
              type="button"
            >
              <Upload size={15} aria-hidden="true" />
              新建分析
            </button>
          </div>

          <button
            aria-label={mobileOpen ? "关闭平台菜单" : "打开平台菜单"}
            className="ml-auto inline-flex size-11 items-center justify-center border border-white/20 text-white transition hover:border-white hover:bg-white hover:text-black md:hidden"
            onClick={() => setMobileOpen((value) => !value)}
            type="button"
          >
            {mobileOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>

        <div className="mx-auto flex max-w-[1480px] gap-2 overflow-x-auto px-5 pb-4 sm:px-8 xl:hidden">
          {platformNavigation.map(({ id, shortLabel }) => (
            <button
              className={`shrink-0 border px-3 py-2 text-[10px] font-black uppercase tracking-widest transition ${
                activeView === id
                  ? "border-white bg-white text-black"
                  : "border-white/15 bg-white/[0.03] text-brand-light"
              }`}
              key={id}
              onClick={() => handleNavigate(id)}
              type="button"
            >
              {shortLabel}
            </button>
          ))}
        </div>

        {mobileOpen ? (
          <div className="border-t border-white/10 bg-black px-5 py-4 md:hidden">
            <div className="grid gap-2">
              <a className="border border-white/10 px-4 py-3 text-xs font-black tracking-widest" href="/">
                官网首页
              </a>
              {platformNavigation.map(({ id, label }) => (
                <button
                  className="border border-white/10 px-4 py-3 text-left text-xs font-black tracking-widest"
                  key={id}
                  onClick={() => handleNavigate(id)}
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </header>

      <main className="mx-auto min-h-[calc(100vh-5rem)] max-w-[1480px] px-5 py-8 sm:px-8 lg:py-10">
        {children}
      </main>
    </div>
  );
}

export function PlatformPageHeader({
  eyebrow,
  title,
  description,
  action
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-7 flex flex-col gap-5 border-b border-white/10 pb-7 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p className="text-[10px] font-black uppercase tracking-ultra text-brand-light">{eyebrow}</p>
        <h1 className="mt-3 max-w-4xl text-3xl font-black uppercase tracking-widest text-white sm:text-5xl">
          {title}
        </h1>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-brand-light sm:text-base">{description}</p>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function PlatformPanel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`border border-white/10 bg-white/[0.035] ${className}`}>{children}</section>;
}
