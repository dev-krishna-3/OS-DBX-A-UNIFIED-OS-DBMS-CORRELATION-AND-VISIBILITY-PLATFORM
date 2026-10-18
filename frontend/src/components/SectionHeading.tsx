import { motion } from 'framer-motion';
export function SectionHeading({ eyebrow, title, sub }: { eyebrow?: string; title: string; sub?: string }) {
  return (
    <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: '-80px' }} transition={{ duration: 0.6 }} className="mx-auto mb-10 max-w-2xl text-center">
      {eyebrow && <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-ink-500">{eyebrow}</p>}
      <h2 className="font-display text-3xl font-light md:text-4xl">{title}</h2>
      {sub && <p className="mt-3 text-ink/70">{sub}</p>}
    </motion.div>
  );
}
