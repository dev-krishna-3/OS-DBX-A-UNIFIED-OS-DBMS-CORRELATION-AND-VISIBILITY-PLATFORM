import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChevronDown, Menu, Sparkles, X } from 'lucide-react';
import { content } from '../content';
import { ButtonLink } from './Button';

export function Navbar() {
  const [open, setOpen] = useState(false);
  const [dd, setDd] = useState(false);
  return (
    <motion.header initial={{ opacity: 0, y: -14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="relative z-30">
      <div className="flex items-center justify-between px-5 py-4 md:px-8">
        <a href="#top" className="flex items-center gap-2 font-display text-lg font-semibold" aria-label="Tutor IQ home">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-sun"><Sparkles className="h-4 w-4" aria-hidden /></span>{content.brand}
        </a>
        <nav aria-label="Main" className="hidden items-center gap-7 text-sm text-white lg:flex">
          {content.nav.map((l) => <a key={l.label} href={l.href} className="link-u">{l.label}</a>)}
          <div className="relative" onMouseLeave={() => setDd(false)}>
            <button className="flex items-center gap-1" aria-expanded={dd} aria-haspopup="true" onClick={() => setDd(!dd)} onMouseEnter={() => setDd(true)}>Resources<ChevronDown className={`h-4 w-4 transition-transform ${dd ? 'rotate-180' : ''}`} aria-hidden /></button>
            <AnimatePresence>
              {dd && (
                <motion.ul initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} className="absolute left-0 top-full mt-2 w-48 rounded-2xl bg-white p-2 text-ink shadow-soft">
                  {content.resources.map((r) => <li key={r.label}><a href={r.href} className="block rounded-lg px-3 py-2 hover:bg-sky-50" onClick={() => setDd(false)}>{r.label}</a></li>)}
                </motion.ul>
              )}
            </AnimatePresence>
          </div>
        </nav>
        <div className="hidden items-center gap-3 lg:flex">
          <ButtonLink variant="light" href="#labs" className="!py-1.5">Browse labs</ButtonLink>
          <ButtonLink variant="dark" href="#lab" className="!py-1.5">Get started</ButtonLink>
        </div>
        <button className="rounded-md p-2 text-white lg:hidden" aria-label={open ? 'Close menu' : 'Open menu'} aria-expanded={open} onClick={() => setOpen(!open)}><Menu /></button>
      </div>
      <AnimatePresence>
        {open && (
          <>
            <motion.div className="fixed inset-0 z-40 bg-ink/40" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setOpen(false)} />
            <motion.nav aria-label="Mobile" className="fixed right-0 top-0 z-50 flex h-full w-72 max-w-[85%] flex-col gap-1 bg-white p-5 shadow-frame" initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ type: 'spring', stiffness: 300, damping: 32 }}>
              <button className="mb-4 self-end rounded-md p-2" aria-label="Close menu" onClick={() => setOpen(false)}><X /></button>
              {[...content.nav, ...content.resources].map((l) => <a key={l.label} href={l.href} onClick={() => setOpen(false)} className="rounded-xl px-3 py-3 hover:bg-sky-50">{l.label}</a>)}
              <ButtonLink variant="dark" href="#lab" onClick={() => setOpen(false)} className="mt-4">Get started</ButtonLink>
            </motion.nav>
          </>
        )}
      </AnimatePresence>
    </motion.header>
  );
}
