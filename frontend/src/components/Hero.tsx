import { motion, useReducedMotion } from 'framer-motion';
import { content } from '../content';
import { Navbar } from './Navbar';
import { Sky } from './Sky';
import { Blimp } from './Blimp';
import { Dashboard } from './Dashboard';
import { ButtonLink } from './Button';

export function Hero() {
  const reduce = useReducedMotion();
  const h = content.hero;
  return (
    <section id="top" className="p-3 md:p-6">
      <div className="relative mx-auto max-w-6xl overflow-hidden rounded-frame shadow-frame">
        <Sky />
        <Navbar />
        <div className="relative z-10 px-5 pt-10 text-center md:pt-16">
          <Blimp className="absolute left-2 top-24 hidden w-44 md:block lg:left-10 lg:top-40 lg:w-60" />
          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }} className="mx-auto max-w-2xl font-display text-4xl font-light leading-[1.1] text-white drop-shadow-sm sm:text-5xl md:text-6xl">
            {h.before}{' '}
            <span className="relative inline-block px-2">
              <motion.span aria-hidden className="absolute inset-x-0 bottom-[6%] top-[10%] -z-0 origin-left -rotate-1 rounded-md bg-sun" initial={{ scaleX: reduce ? 1 : 0 }} animate={{ scaleX: 1 }} transition={{ duration: 0.7, delay: 1, ease: 'easeOut' }} />
              <span className="relative text-ink">{h.mark}</span>
            </span>
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} className="mx-auto mt-5 max-w-md text-sm text-white/90 md:text-base">{h.sub}</motion.p>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }} className="mt-7 flex flex-wrap justify-center gap-3">
            <ButtonLink href="#lab" arrow>Get started</ButtonLink>
            <ButtonLink variant="light" href="#labs">Find a lab</ButtonLink>
          </motion.div>
          <div className="mt-12 md:mt-16"><Dashboard /></div>
        </div>
      </div>
    </section>
  );
}
