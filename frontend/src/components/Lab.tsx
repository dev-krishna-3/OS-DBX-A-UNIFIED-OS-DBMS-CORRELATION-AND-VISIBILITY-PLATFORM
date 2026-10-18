import { useEffect, useMemo, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Play, Pause, SkipForward, RotateCcw, Plus, Trash2, Cpu } from 'lucide-react';
import { Button } from './Button';
import { SectionHeading } from './SectionHeading';
import { LIMITS, MAX_PROCESSES, RULES, buildSchedule, colorOf, sampleProcesses } from '../lib/scheduler';
import type { Proc, Rule, Schedule } from '../lib/scheduler';

const clamp = (v: number, [lo, hi]: readonly [number, number]) => Math.min(hi, Math.max(lo, Number.isNaN(v) ? lo : Math.round(v)));

function Chip({ name }: { name: string }) {
  return <motion.span layout initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="inline-flex h-9 w-9 items-center justify-center rounded-full text-xs font-semibold text-ink" style={{ background: colorOf(name) }}>{name}</motion.span>;
}
function Zone({ title, names, empty }: { title: string; names: string[]; empty: string }) {
  return (
    <div className="rounded-2xl bg-white/70 p-4">
      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">{title}</h4>
      <div className="flex min-h-9 flex-wrap gap-2">{names.length ? names.map((n) => <Chip key={n} name={n} />) : <span className="text-sm text-ink/50">{empty}</span>}</div>
    </div>
  );
}

export function Lab() {
  const reduce = useReducedMotion();
  const [procs, setProcs] = useState<Proc[]>(sampleProcesses);
  const [rule, setRule] = useState<Rule>('FCFS');
  const [quantum, setQuantum] = useState(2);
  const [result, setResult] = useState<Schedule | null>(null);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);

  const edit = (fn: () => void) => { fn(); setResult(null); setPlaying(false); };
  const run = (r: Rule = rule) => { setRule(r); setResult(buildSchedule(r, procs, quantum)); setStep(0); setPlaying(true); };
  const last = result ? result.segments.length - 1 : 0;
  const done = !!result && step === last;

  useEffect(() => {
    if (!playing || !result) return;
    const t = setTimeout(() => (step < last ? setStep(step + 1) : setPlaying(false)), reduce ? 400 : 1100);
    return () => clearTimeout(t);
  }, [playing, step, result, last, reduce]);

  const compare = useMemo(() => (result ? (Object.keys(RULES) as Rule[]).map((r) => buildSchedule(r, procs, quantum)) : []), [result, procs, quantum]);
  const seg = result?.segments[step];
  const finished = result ? result.segments.slice(0, step + 1).filter((s) => s.finished).map((s) => s.name) : [];
  const notYet = result ? procs.filter((p) => p.at >= (seg?.end ?? 0) && !finished.includes(p.name) && p.name !== seg?.name).map((p) => p.name) : [];

  const setField = (i: number, k: 'at' | 'bt' | 'priority', v: number) => edit(() => setProcs(procs.map((p, j) => (j === i ? { ...p, [k]: clamp(v, LIMITS[k]) } : p))));
  const addProc = () => edit(() => {
    const name = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6'].find((n) => !procs.some((p) => p.name === n))!;
    setProcs([...procs, { name, at: 0, bt: 3, priority: 5 }]);
  });
  const field = 'w-16 rounded-lg border border-ink/20 bg-white px-2 py-1.5 text-center text-sm';

  return (
    <section id="lab" className="mx-auto max-w-5xl px-5 py-20">
      <SectionHeading eyebrow="Lab 01 · Operating system" title="Process lab" sub="The CPU is a cashier and every process is a customer. Choose who gets served next." />
      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <div className="rounded-card bg-white p-5 shadow-soft">
          <h3 className="mb-3 font-display text-lg">1 · Your processes</h3>
          <div role="table" aria-label="Processes" className="space-y-2">
            <div role="row" className="grid grid-cols-[2.5rem_1fr_1fr_1fr_2rem] items-center gap-2 text-xs text-ink/60"><span /><span>Arrives</span><span>Needs</span><span>Priority</span><span /></div>
            {procs.map((p, i) => (
              <motion.div role="row" layout key={p.name} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} className="grid grid-cols-[2.5rem_1fr_1fr_1fr_2rem] items-center gap-2">
                <Chip name={p.name} />
                {(['at', 'bt', 'priority'] as const).map((k) => (
                  <input key={k} type="number" inputMode="numeric" className={field} value={p[k]} min={LIMITS[k][0]} max={LIMITS[k][1]} aria-label={`${p.name} ${k === 'at' ? 'arrival time' : k === 'bt' ? 'burst time' : 'priority'}`} onChange={(e) => setField(i, k, e.target.valueAsNumber)} />
                ))}
                <button aria-label={`Remove ${p.name}`} disabled={procs.length <= 1} onClick={() => edit(() => setProcs(procs.filter((_, j) => j !== i)))} className="rounded-md p-1 text-ink/60 hover:text-ink disabled:opacity-30"><Trash2 className="h-4 w-4" /></button>
              </motion.div>
            ))}
          </div>
          <Button variant="ghost" className="mt-3" onClick={addProc} disabled={procs.length >= MAX_PROCESSES}><Plus className="h-4 w-4" aria-hidden />Add process</Button>

          <h3 className="mb-3 mt-6 font-display text-lg">2 · Pick a rule</h3>
          <fieldset className="grid grid-cols-2 gap-2">
            <legend className="sr-only">Scheduling rule</legend>
            {(Object.keys(RULES) as Rule[]).map((r) => (
              <label key={r} className={`cursor-pointer rounded-xl border px-3 py-2 text-sm transition hover:-translate-y-0.5 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ink ${rule === r ? 'border-ink bg-sky-50' : 'border-ink/15'}`}>
                <input type="radio" name="rule" className="sr-only" checked={rule === r} onChange={() => edit(() => setRule(r))} />{RULES[r]}
              </label>
            ))}
          </fieldset>
          {rule === 'RR' && (
            <label className="mt-3 flex items-center gap-3 text-sm">Turn length
              <input type="number" className={field} value={quantum} min={1} max={10} onChange={(e) => edit(() => setQuantum(clamp(e.target.valueAsNumber, LIMITS.quantum)))} /> time units
            </label>
          )}
          <Button className="mt-6 w-full" arrow onClick={() => run()}>Run simulation</Button>
        </div>

        <div className="rounded-card bg-gradient-to-b from-sky-50 to-white p-5 shadow-soft" aria-live="polite">
          <h3 className="mb-3 flex items-center gap-2 font-display text-lg"><Cpu className="h-5 w-5" aria-hidden />3 · Watch the CPU</h3>
          {!result || !seg ? (
            <p className="rounded-2xl bg-white/70 p-6 text-sm text-ink/70">Press “Run simulation” to see the CPU at work.</p>
          ) : (
            <div className="space-y-3">
              <Zone title="Not here yet" names={notYet} empty="Everyone has arrived" />
              <Zone title="Waiting line" names={seg.queue} empty="Nobody waiting" />
              <div className="rounded-2xl bg-ink p-4 text-paper">
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-sun">On the CPU · time {seg.start}–{seg.end}</h4>
                {seg.name === 'IDLE' ? <span>Idle</span> : <Chip key={seg.start} name={seg.name} />}
                <p className="mt-2 text-sm text-paper/85">{seg.reason}</p>
              </div>
              <Zone title="Finished" names={finished} empty="Nobody finished yet" />
              <div className="flex gap-2">
                <Button variant="ghost" onClick={() => setPlaying(!playing)} disabled={done}>{playing ? <Pause className="h-4 w-4" aria-hidden /> : <Play className="h-4 w-4" aria-hidden />}{playing ? 'Pause' : 'Play'}</Button>
                <Button variant="ghost" onClick={() => { setPlaying(false); setStep(Math.min(last, step + 1)); }} disabled={done}><SkipForward className="h-4 w-4" aria-hidden />Step</Button>
                <Button variant="ghost" onClick={() => run(rule)}><RotateCcw className="h-4 w-4" aria-hidden />Replay</Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {result && (
        <div className="mt-6 rounded-card bg-white p-5 shadow-soft">
          <h3 className="mb-3 font-display text-lg">Timeline</h3>
          <div className="flex h-12 overflow-hidden rounded-xl bg-paper" role="img" aria-label="Timeline of CPU blocks">
            {result.segments.map((s, i) => (
              <motion.div key={`${rule}-${i}`} initial={{ scaleX: 0 }} animate={{ scaleX: i <= step ? 1 : 0 }} style={{ width: `${((s.end - s.start) / result.total) * 100}%`, originX: 0, background: s.name === 'IDLE' ? '#e5e5dc' : colorOf(s.name) }} className={`flex items-center justify-center border-r border-white text-xs font-semibold ${i === step ? 'ring-2 ring-inset ring-ink' : ''}`}>{s.name === 'IDLE' ? '' : s.name}</motion.div>
            ))}
          </div>
          <div className="mt-1 flex justify-between text-xs text-ink/60"><span>0</span><span>{result.total}</span></div>
          {done && (
            <div className="mt-5">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[420px] text-left text-sm">
                  <thead className="text-xs text-ink/60"><tr><th className="py-1">Process</th><th>Finished at</th><th>Total time</th><th>Waited</th></tr></thead>
                  <tbody>{result.stats.map((s) => <tr key={s.name} className="border-t border-ink/10"><td className="py-1.5"><Chip name={s.name} /></td><td>{s.completion}</td><td>{s.turnaround}</td><td>{s.waiting}</td></tr>)}</tbody>
                </table>
              </div>
              <p className="mt-3 text-sm">On average, a process waited <strong>{result.avgWait.toFixed(2)}</strong> time units.</p>
              <h4 className="mb-2 mt-5 text-sm font-semibold">Compare the four rules on the same processes</h4>
              <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                {compare.map((c) => {
                  const best = Math.min(...compare.map((x) => x.avgWait)) === c.avgWait;
                  return <button key={c.rule} onClick={() => run(c.rule)} className={`rounded-xl border p-3 text-left text-sm transition hover:-translate-y-0.5 ${best ? 'border-ink bg-sky-50' : 'border-ink/15'}`}><span className="block text-xs text-ink/60">{RULES[c.rule]}</span><strong>{c.avgWait.toFixed(2)}</strong> avg wait{best && ' · lowest'}</button>;
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
