import { Instagram, Twitter, Youtube } from "lucide-react";
import { footerGroups } from "@/lib/content";
import { IconButton } from "@/components/ui";

export function Footer() {
  return (
    <footer className="border-t border-white/10 bg-brand-black px-5 py-14 sm:px-8">
      <div className="mx-auto grid max-w-7xl gap-10 sm:grid-cols-2 lg:grid-cols-[1.2fr_0.75fr_0.75fr_1.1fr]">
        <div>
          <p className="text-lg font-black tracking-widest text-white">智泳云枢</p>
          <p className="mt-4 max-w-sm text-sm leading-7 text-brand-muted">
            移动式双摄泳姿采集与AI姿态分析系统，服务竞技游泳训练、教练复盘与体育科研。
          </p>
          <div className="mt-6 flex gap-3">
            <IconButton label="Instagram">
              <Instagram size={17} />
            </IconButton>
            <IconButton label="YouTube">
              <Youtube size={17} />
            </IconButton>
            <IconButton label="Twitter">
              <Twitter size={17} />
            </IconButton>
          </div>
        </div>

        {footerGroups.map((group) => (
          <div key={group.title}>
            <p className="text-xs font-black uppercase tracking-ultra text-white">{group.title}</p>
            <ul className="mt-5 space-y-3">
              {group.links.map((link) => (
                <li key={link}>
                  <a href="#top" className="text-sm text-brand-muted transition hover:text-white">
                    {link}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}

        <div>
          <p className="text-xs font-black uppercase tracking-ultra text-white">SUBSCRIBE</p>
          <p className="mt-5 text-sm leading-7 text-brand-muted">
            获取系统演示、训练场景更新与产品测试信息。
          </p>
          <form className="mt-5 flex border border-white/15" action="#">
            <input
              aria-label="Email"
              type="email"
              placeholder="EMAIL"
              className="min-w-0 flex-1 bg-transparent px-4 text-xs font-bold uppercase tracking-widest text-white outline-none placeholder:text-brand-muted"
            />
            <button
              type="submit"
              className="border-l border-white/15 px-4 text-xs font-black uppercase tracking-widest text-white transition hover:bg-white hover:text-black"
            >
              Join
            </button>
          </form>
        </div>
      </div>
      <p className="mx-auto mt-12 max-w-7xl border-t border-white/10 pt-6 text-center text-[10px] uppercase tracking-ultra text-brand-muted">
        © 2026 ZHIYONG YUNSHU. All rights reserved.
      </p>
    </footer>
  );
}
