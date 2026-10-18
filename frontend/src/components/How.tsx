import { motion } from 'framer-motion';
import { content } from '../content';
import { SectionHeading } from './SectionHeading';

export default function How() {
  return (
    <section id="how" className="mx-auto max-w-5xl px-5 py-20">
      <SectionHeading eyebrow="How it works" title="Three small steps, one big idea" />
      <ol className="grid gap-4 md:grid-cols-3">
        {content.how.map((s, i) => (
          <motion.li key={s.t} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }} className="rounded-card bg-white p-6 shadow-soft transition hover:-translate-y-1">
            <span className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-full bg-sun font-display text-lg">{i + 1}</span>
            <h3 className="font-display text-xl">{s.t}</h3><p className="mt-1 text-sm text-ink/70">{s.d}</p>
          </motion.li>
        ))}
      </ol>
    </section>
  );
}
