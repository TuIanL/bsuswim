"use client";

import { Plus, X } from "lucide-react";
import { useState } from "react";
import { faqItems } from "@/lib/content";
import { Section } from "@/components/ui";

export function FAQ() {
  const [openIndex, setOpenIndex] = useState(0);

  return (
    <Section id="faq" eyebrow="FAQ" title="常见问题">
      <div className="mx-auto max-w-4xl border-y border-white/10">
        {faqItems.map((item, index) => {
          const open = openIndex === index;

          return (
            <div key={item.question} className="border-b border-white/10 last:border-b-0">
              <button
                type="button"
                onClick={() => setOpenIndex(open ? -1 : index)}
                aria-expanded={open}
                className="flex w-full items-center justify-between gap-6 py-6 text-left"
              >
                <span className="text-base font-bold tracking-widest text-white sm:text-lg">{item.question}</span>
                <span className="shrink-0 text-white">{open ? <X size={18} /> : <Plus size={18} />}</span>
              </button>
              <div
                className={`grid transition-all duration-300 ease-out ${
                  open ? "grid-rows-[1fr] pb-6" : "grid-rows-[0fr]"
                }`}
              >
                <div className="overflow-hidden">
                  <p className="max-w-3xl text-sm leading-7 text-brand-light">{item.answer}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Section>
  );
}
