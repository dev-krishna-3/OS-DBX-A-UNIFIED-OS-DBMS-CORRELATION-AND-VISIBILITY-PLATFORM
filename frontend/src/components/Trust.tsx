import { motion } from 'framer-motion';
import { BookOpen, ShieldCheck, Smartphone, WifiOff } from 'lucide-react';
import { content } from '../content';
import { SectionHeading } from './SectionHeading';

const icons = [ShieldCheck, BookOpen, WifiOff, Smartphone];

export default function Trust() {
  return (
    <section id="trust" className="bg-white/60 px-5 py-20">
      <SectionHeading eyebrow="Built for trust" title="Safe, clear and kind to beginners" />
      <ul className="mx-auto grid max-w-5xl gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {content.trust.map((t, i) => { const I = icons[i]; return (
          <motion.li key={t.t} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.08 }} className="rounded-card bg-sky-50 p-5">
            <I className="mb-3 h-6 w-6" aria-hidden /><h3 className="font-display text-lg">{t.t}</h3><p className="mt-1 text-sm text-ink/70">{t.d}</p>
          </motion.li>); })}
      </ul>
    </section>
  );
}
