import { ArrowRight } from 'lucide-react';
import type { ButtonHTMLAttributes, AnchorHTMLAttributes, ReactNode } from 'react';

type Variant = 'dark' | 'light' | 'ghost';
const styles: Record<Variant, string> = {
  dark: 'bg-ink text-paper hover:bg-ink-700',
  light: 'bg-white/80 text-ink hover:bg-white',
  ghost: 'bg-white/70 text-ink border border-ink/15 hover:bg-white',
};
const base = 'group inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition duration-200 hover:-translate-y-0.5 active:translate-y-0 active:scale-[.97] disabled:opacity-50 disabled:pointer-events-none';
interface Common { variant?: Variant; arrow?: boolean; children: ReactNode }
const Arrow = () => <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" aria-hidden />;
export function Button({ variant = 'dark', arrow, children, className = '', ...r }: Common & ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={`${base} ${styles[variant]} ${className}`} {...r}>{children}{arrow && <Arrow />}</button>;
}
export function ButtonLink({ variant = 'dark', arrow, children, className = '', ...r }: Common & AnchorHTMLAttributes<HTMLAnchorElement>) {
  return <a className={`${base} ${styles[variant]} ${className}`} {...r}>{children}{arrow && <Arrow />}</a>;
}
