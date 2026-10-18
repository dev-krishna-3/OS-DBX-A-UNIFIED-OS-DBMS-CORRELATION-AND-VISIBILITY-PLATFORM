export type Rule = 'FCFS' | 'SJF' | 'PRIORITY' | 'RR';
export interface Proc { name: string; at: number; bt: number; priority: number }
export interface Seg { name: string; start: number; end: number; queue: string[]; reason: string; left: number; finished: boolean }
export interface Stat extends Proc { completion: number; turnaround: number; waiting: number }
export interface Schedule { rule: Rule; segments: Seg[]; stats: Stat[]; total: number; avgWait: number; avgTurn: number }
type Raw = Omit<Seg, 'left' | 'finished'>;

export const RULES: Record<Rule, string> = {
  FCFS: 'First come, first served', SJF: 'Shortest job first', PRIORITY: 'Priority', RR: 'Round robin',
};
export const LIMITS = { at: [0, 30], bt: [1, 30], priority: [1, 9], quantum: [1, 10] } as const;
export const MAX_PROCESSES = 6;
export const PALETTE = ['#ffd84d', '#ff9f8a', '#9ad7f7', '#b9e6a8', '#d9c2f5', '#ffc6dd'];
export const colorOf = (name: string) => PALETTE[(Number(name.slice(1)) - 1) % PALETTE.length] ?? '#ddd';
export const sampleProcesses = (): Proc[] => [
  { name: 'P1', at: 0, bt: 7, priority: 2 }, { name: 'P2', at: 1, bt: 4, priority: 3 },
  { name: 'P3', at: 2, bt: 1, priority: 4 }, { name: 'P4', at: 3, bt: 2, priority: 1 },
];

const byName = (a: Proc, b: Proc) => a.name.localeCompare(b.name);
const units = (n: number) => `${n} time unit${n === 1 ? '' : 's'}`;
const idle = (start: number, end: number): Raw => ({ name: 'IDLE', start, end, queue: [], reason: 'Nobody is here yet, so the CPU waits.' });

function fcfs(list: Proc[]): Raw[] {
  const ordered = [...list].sort((a, b) => a.at - b.at || byName(a, b));
  const out: Raw[] = [];
  let time = 0;
  ordered.forEach((p, i) => {
    let wasIdle = false;
    if (p.at > time) { out.push(idle(time, p.at)); time = p.at; wasIdle = true; }
    const end = time + p.bt;
    const queue = ordered.slice(i + 1).filter((q) => q.at <= end).map((q) => q.name);
    const reason = wasIdle ? `The CPU was free when ${p.name} arrived, so it starts right away.`
      : i === 0 ? `${p.name} arrived first, so it gets the CPU first.`
      : `${p.name} has been waiting the longest, so it is next in line.`;
    out.push({ name: p.name, start: time, end, queue, reason });
    time = end;
  });
  return out;
}

function nonPreemptive(list: Proc[], mode: 'SJF' | 'PRIORITY'): Raw[] {
  const cmp = mode === 'SJF'
    ? (a: Proc, b: Proc) => a.bt - b.bt || a.at - b.at || byName(a, b)
    : (a: Proc, b: Proc) => a.priority - b.priority || a.at - b.at || byName(a, b);
  const pending = list.map((p) => ({ ...p }));
  const out: Raw[] = [];
  let time = 0;
  while (pending.length) {
    const ready = pending.filter((p) => p.at <= time).sort(cmp);
    if (!ready.length) {
      const next = Math.min(...pending.map((p) => p.at));
      out.push(idle(time, next)); time = next; continue;
    }
    const p = ready[0];
    pending.splice(pending.indexOf(p), 1);
    const end = time + p.bt;
    const queue = pending.filter((q) => q.at <= end).sort(cmp).map((q) => q.name);
    const tie = ready[1] && (mode === 'SJF' ? ready[1].bt === p.bt : ready[1].priority === p.priority);
    let reason = ready.length === 1 ? `${p.name} is the only one waiting, so it goes.`
      : mode === 'SJF' ? `${p.name} needs just ${units(p.bt)}, the shortest of the ${ready.length} waiting.`
      : `${p.name} has priority ${p.priority}, the most important of the ${ready.length} waiting.`;
    if (tie) reason += ` It tied with ${ready[1].name} but arrived first.`;
    out.push({ name: p.name, start: time, end, queue, reason });
    time = end;
  }
  return out;
}

function roundRobin(list: Proc[], q: number): Raw[] {
  const pending = [...list].sort((a, b) => a.at - b.at || byName(a, b)).map((p) => ({ ...p, remaining: p.bt }));
  const queue: typeof pending = [];
  const out: Raw[] = [];
  let time = 0, index = 0;
  const admit = () => { while (index < pending.length && pending[index].at <= time) queue.push(pending[index++]); };
  while (index < pending.length || queue.length) {
    if (!queue.length && pending[index].at > time) { out.push(idle(time, pending[index].at)); time = pending[index].at; }
    admit();
    const cur = queue.shift()!;
    const before = cur.remaining;
    const start = time;
    time += Math.min(q, before);
    cur.remaining -= Math.min(q, before);
    admit();
    if (cur.remaining) queue.push(cur);
    const reason = before <= q
      ? `${cur.name} needs ${units(before)} and a turn lasts up to ${q}, so it can finish.`
      : `${cur.name} gets a turn of ${units(q)}.`;
    out.push({ name: cur.name, start, end: time, queue: queue.map((p) => p.name), reason });
  }
  return out;
}

export function buildSchedule(rule: Rule, list: Proc[], q: number): Schedule {
  const raw = rule === 'FCFS' ? fcfs(list) : rule === 'RR' ? roundRobin(list, q) : nonPreemptive(list, rule);
  const left = new Map(list.map((p) => [p.name, p.bt]));
  const segments: Seg[] = raw.map((s) => {
    const queue = s.queue.filter((n) => n !== s.name);
    if (s.name === 'IDLE') return { ...s, queue, left: 0, finished: false };
    const rem = (left.get(s.name) ?? 0) - (s.end - s.start);
    left.set(s.name, rem);
    return { ...s, queue, left: rem, finished: rem === 0 };
  });
  const done = new Map<string, number>();
  segments.forEach((s) => { if (s.finished) done.set(s.name, s.end); });
  const stats: Stat[] = list.map((p) => {
    const completion = done.get(p.name) ?? 0;
    const turnaround = completion - p.at;
    return { ...p, completion, turnaround, waiting: turnaround - p.bt };
  });
  const avg = (k: 'waiting' | 'turnaround') => stats.reduce((s, p) => s + p[k], 0) / stats.length;
  return { rule, segments, stats, total: segments[segments.length - 1].end, avgWait: avg('waiting'), avgTurn: avg('turnaround') };
}
