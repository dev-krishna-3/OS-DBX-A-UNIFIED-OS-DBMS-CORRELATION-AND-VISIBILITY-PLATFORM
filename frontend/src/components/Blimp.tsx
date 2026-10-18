import { motion, useReducedMotion } from 'framer-motion';

export function Blimp({ className = '' }: { className?: string }) {
  const reduce = useReducedMotion();
  return (
    <motion.div className={className} animate={reduce ? undefined : { y: [0, -14, 0], rotate: [-1.5, 1.5, -1.5] }} transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }} aria-hidden>
      <svg viewBox="0 0 260 150" className="h-auto w-full drop-shadow-xl">
        <defs><clipPath id="env"><ellipse cx="130" cy="62" rx="105" ry="48" /></clipPath></defs>
        <path d="M222 62 L252 30 L252 94 Z" fill="#d6453d" />
        <ellipse cx="130" cy="62" rx="105" ry="48" fill="#fff" />
        <g clipPath="url(#env)" fill="#d6453d">{[40, 75, 110, 145, 180, 215].map((x) => <rect key={x} x={x} y="10" width="17" height="110" transform={`skewX(-6)`} />)}</g>
        <ellipse cx="130" cy="62" rx="105" ry="48" fill="none" stroke="#b83a33" strokeWidth="2" />
        <path d="M100 108 L112 124 M160 108 L148 124" stroke="#6b4a2f" strokeWidth="3" />
        <rect x="104" y="122" width="52" height="16" rx="6" fill="#8a5a36" />
        <circle cx="12" cy="68" r="5" fill="#444" />
      </svg>
    </motion.div>
  );
}
