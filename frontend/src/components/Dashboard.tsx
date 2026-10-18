import { motion } from 'framer-motion';
import { BarChart3, Cpu, Database, Home, Settings, Sparkles } from 'lucide-react';
import { content } from '../content';

const icons = [Home, Cpu, Database, BarChart3, Settings];
const item = { hidden: { opacity: 0, y: 18 }, show: { opacity: 1, y: 0 } };

export function Dashboard() {
  const d = content.dash;
  return (
    <motion.div initial={{ y: 220, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ type: 'spring', stiffness: 70, damping: 18, delay: 0.9 }} className="mx-auto w-full max-w-4xl" role="img" aria-label="Preview of the OS-DBX dashboard">
      <div className="flex h-[300px] overflow-hidden rounded-t-3xl border border-white/70 bg-white/90 shadow-frame backdrop-blur md:h-[340px]" aria-hidden>
        <aside className="hidden w-40 shrink-0 border-r border-ink/5 p-4 sm:block">
          <p className="mb-4 flex items-center gap-1.5 font-display text-sm font-semibold"><Sparkles className="h-3.5 w-3.5 text-sun-deep" />Tutor IQ</p>
          <ul className="space-y-1 text-xs">
            {d.sidebar.map((s, i) => { const I = icons[i]; return <li key={s} className={`flex items-center gap-2 rounded-lg px-2 py-1.5 ${i === 0 ? 'bg-sky-50 font-medium' : 'text-ink/60'}`}><I className="h-3.5 w-3.5" />{s}</li>; })}
          </ul>
        </aside>
        <motion.div variants={{ show: { transition: { staggerChildren: 0.12, delayChildren: 1.4 } } }} initial="hidden" animate="show" className="flex-1 space-y-3 p-4 text-left md:p-5">
          <motion.h3 variants={item} className="font-display text-lg">{d.welcome}</motion.h3>
          <motion.div variants={item} className="flex items-center justify-between gap-3 rounded-2xl bg-sun/90 p-4">
            <div><p className="text-[11px] uppercase tracking-wide text-ink/60">Up next</p><p className="text-sm font-semibold">{d.next.title}</p><p className="text-xs text-ink/70">{d.next.meta}</p></div>
            <span className="hidden rounded-full bg-ink px-3 py-1.5 text-xs text-paper sm:block">Start lab</span>
          </motion.div>
          <div className="grid gap-3 md:grid-cols-[1.3fr_1fr]">
            <motion.div variants={item} className="rounded-2xl border border-ink/10 p-3">
              <p className="mb-2 text-xs font-semibold">This week</p>
              <div className="grid grid-cols-4 gap-2 text-[11px]">{d.week.map((w) => <div key={w.day} className="rounded-lg bg-sky-50 p-2"><p className="text-ink/50">{w.day}</p><p className="mt-1 font-medium leading-tight">{w.items[0]}</p></div>)}</div>
            </motion.div>
            <motion.div variants={item} className="hidden rounded-2xl border border-ink/10 p-3 md:block"><p className="text-xs font-semibold">{d.summary.title}</p><p className="mt-1 text-[11px] leading-snug text-ink/70">{d.summary.body}</p></motion.div>
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}
