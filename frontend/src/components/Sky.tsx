import { useEffect } from 'react';
import { motion, useMotionValue, type MotionValue, useScroll, useSpring, useTransform, useReducedMotion } from 'framer-motion';

const LAYERS = [
  { top: '6%', left: '-6%', w: 300, depth: 10, dur: 70, op: 0.85 },
  { top: '30%', left: '62%', w: 240, depth: 18, dur: 55, op: 0.9 },
  { top: '56%', left: '-10%', w: 380, depth: 30, dur: 48, op: 1 },
  { top: '70%', left: '40%', w: 460, depth: 42, dur: 40, op: 1 },
];

function CloudShape({ w, op }: { w: number; op: number }) {
  return (
    <svg width={w} viewBox="0 0 320 140" aria-hidden style={{ opacity: op, filter: 'drop-shadow(0 12px 18px rgba(60,140,210,.35))' }}>
      <g fill="#fff"><circle cx="80" cy="90" r="45" /><circle cx="140" cy="60" r="55" /><circle cx="210" cy="80" r="50" /><circle cx="265" cy="100" r="36" /><rect x="40" y="95" width="250" height="40" rx="20" /></g>
    </svg>
  );
}

function Layer({ l, mx, my }: { l: (typeof LAYERS)[number]; mx: MotionValue<number>; my: MotionValue<number> }) {
  const { scrollY } = useScroll();
  const x = useTransform(mx, (v) => v * l.depth);
  const mouseY = useTransform(my, (v) => v * l.depth * 0.5);
  const scrollOffset = useTransform(scrollY, [0, 800], [0, -l.depth * 3]);
  const y = useTransform([mouseY, scrollOffset], ([a, b]: number[]) => a + b);
  return (
    <motion.div className="absolute" style={{ top: l.top, left: l.left, x, y }}>
      <motion.div animate={{ x: [0, 40, 0] }} transition={{ duration: l.dur, repeat: Infinity, ease: 'easeInOut' }}><CloudShape w={l.w} op={l.op} /></motion.div>
    </motion.div>
  );
}

export function Sky() {
  const reduce = useReducedMotion();
  const rawX = useMotionValue(0), rawY = useMotionValue(0);
  const mx = useSpring(rawX, { stiffness: 40, damping: 20 }), my = useSpring(rawY, { stiffness: 40, damping: 20 });
  useEffect(() => {
    if (reduce) return;
    const move = (e: PointerEvent) => { rawX.set(e.clientX / window.innerWidth - 0.5); rawY.set(e.clientY / window.innerHeight - 0.5); };
    window.addEventListener('pointermove', move);
    return () => window.removeEventListener('pointermove', move);
  }, [reduce, rawX, rawY]);
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
      <div className="absolute inset-0 bg-gradient-to-b from-sky-400 via-sky-200 to-sky-50" />
      <motion.div className="absolute -bottom-40 -right-40 h-[520px] w-[520px] rounded-full" style={{ background: 'radial-gradient(circle, #ffd84d 0%, #ffb938 35%, rgba(255,185,56,0) 70%)' }} animate={reduce ? undefined : { scale: [1, 1.08, 1], opacity: [0.85, 1, 0.85] }} transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }} />
      {LAYERS.map((l, i) => <Layer key={i} l={l} mx={mx} my={my} />)}
    </div>
  );
}
