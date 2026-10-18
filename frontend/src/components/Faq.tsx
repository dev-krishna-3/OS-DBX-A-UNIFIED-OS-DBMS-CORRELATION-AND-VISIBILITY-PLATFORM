import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Plus } from 'lucide-react';
import { content } from '../content';
import { SectionHeading } from './SectionHeading';

export default function Faq() {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <section id="faq" className="mx-auto max-w-2xl px-5 pb-20">
      <SectionHeading eyebrow="Questions" title="Good to know" />
      <ul className="space-y-3">
        {content.faq.map((f, i) => (
          <li key={f.q} className="rounded-card bg-white shadow-soft">
            <h3><button className="flex w-full items-center justify-between gap-4 p-5 text-left font-medium" aria-expanded={open === i} aria-controls={`faq-${i}`} onClick={() => setOpen(open === i ? null : i)}>
              {f.q}<Plus className={`h-5 w-5 shrink-0 transition-transform ${open === i ? 'rotate-45' : ''}`} aria-hidden />
            </button></h3>
            <AnimatePresence initial={false}>
              {open === i && <motion.div id={`faq-${i}`} role="region" initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden"><p className="px-5 pb-5 text-sm text-ink/70">{f.a}</p></motion.div>}
            </AnimatePresence>
          </li>
        ))}
      </ul>
    </section>
  );
}
