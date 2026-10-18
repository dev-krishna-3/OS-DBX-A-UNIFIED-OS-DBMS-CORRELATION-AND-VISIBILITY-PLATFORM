import { useRef } from 'react';
import { ChevronLeft, ChevronRight, Lock } from 'lucide-react';
import { content } from '../content';
import { SectionHeading } from './SectionHeading';

const tints = ['bg-sun', 'bg-sky-200', 'bg-white'];

export default function LabsCarousel() {
  const ref = useRef<HTMLUListElement>(null);
  const scroll = (dir: number) => ref.current?.scrollBy({ left: dir * 300, behavior: 'smooth' });
  return (
    <section id="labs" className="py-20">
      <SectionHeading eyebrow="Nine labs" title="Pick a lab to explore" sub="Start with the Process lab. The rest unlock as they are built." />
      <div className="mx-auto max-w-6xl px-5">
        <ul ref={ref} className="no-scrollbar flex snap-x snap-mandatory gap-4 overflow-x-auto pb-4" aria-label="Labs">
          {content.labs.map((l, i) => (
            <li key={l.n} className="w-64 shrink-0 snap-start">
              <a href={l.live ? '#lab' : undefined} className={`flex h-48 flex-col justify-between rounded-card p-5 shadow-soft transition duration-200 hover:-translate-y-1 ${l.live ? 'bg-sun' : tints[i % 3]}`}>
                <div className="flex items-center justify-between"><b className="font-display">{l.n}</b>{!l.live && <span className="flex items-center gap-1 text-xs text-ink/50"><Lock className="h-3 w-3" aria-hidden />Coming soon</span>}</div>
                <div><h3 className="font-display text-xl">{l.t}</h3><p className="mt-1 text-sm text-ink/70">{l.d}</p></div>
              </a>
            </li>
          ))}
        </ul>
        <div className="mt-2 flex justify-end gap-2">
          <button aria-label="Previous labs" onClick={() => scroll(-1)} className="rounded-full bg-white p-2 shadow-soft transition hover:-translate-y-0.5"><ChevronLeft className="h-5 w-5" /></button>
          <button aria-label="Next labs" onClick={() => scroll(1)} className="rounded-full bg-white p-2 shadow-soft transition hover:-translate-y-0.5"><ChevronRight className="h-5 w-5" /></button>
        </div>
      </div>
    </section>
  );
}
