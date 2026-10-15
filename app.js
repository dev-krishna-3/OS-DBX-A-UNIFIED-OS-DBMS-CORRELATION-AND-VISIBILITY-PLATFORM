(() => {
  'use strict';

  /* ==========================================================
     1. DATA + SMALL HELPERS
     ========================================================== */
  const palette = ['#d9ee78', '#ffb19d', '#d8dcb1', '#f0cf74', '#c2dfcd', '#f2b9c8'];
  const NAMES = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6'];
  const MAX_PROCESSES = 6;
  const LIMITS = { at: [0, 30], bt: [1, 30], priority: [1, 9], quantum: [1, 10] };
  const RULES = {
    FCFS: { label: 'First come, first served' },
    SJF: { label: 'Shortest job first' },
    PRIORITY: { label: 'Priority' },
    RR: { label: 'Round robin' },
  };
  const DEFAULT_STATUS = 'Press “Run simulation” above to see the CPU at work.';

  const sampleProcesses = () => [
    { name: 'P1', at: 0, bt: 7, priority: 2 },
    { name: 'P2', at: 1, bt: 4, priority: 3 },
    { name: 'P3', at: 2, bt: 1, priority: 4 },
    { name: 'P4', at: 3, bt: 2, priority: 1 },
  ];

  const $ = (id) => document.getElementById(id);
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const colorOf = (name) => palette[(Number(name.slice(1)) - 1) % palette.length];
  const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
  const units = (n) => plural(n, 'time unit');
  const byName = (a, b) => a.name.localeCompare(b.name);

  function el(tag, className, html) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (html !== undefined) node.innerHTML = html;
    return node;
  }
  const icon = (id, cls = '') =>
    `<svg class="icon ${cls}" viewBox="0 0 24 24" aria-hidden="true"><use href="#i-${id}"/></svg>`;

  function restartClass(node, cls) {
    node.classList.remove(cls);
    void node.offsetWidth; // let the browser notice, so the animation can play again
    node.classList.add(cls);
  }

  /* ==========================================================
     2. STATE
     ========================================================== */
  let processes = sampleProcesses();
  let quantum = 2;
  let result = null;   // the finished schedule for the current run
  let shown = 0;       // how many timeline blocks are visible
  let playing = false;
  let timer = null;
  let tickMs = 1200;
  let prevZone = {};   // which zone each chip was in last render, so only movers animate
  const tried = new Set();

  const rows = $('process-rows');
  const toast = $('toast');
  let toastTimer;

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 2800);
  }

  /* ==========================================================
     3. + / − STEPPER
     ========================================================== */
  function createStepper({ value, min, max, label, onCommit }) {
    const wrap = el('div', 'stepper');
    const input = el('input', 'stepper-input');
    input.type = 'number';
    input.inputMode = 'numeric';
    input.min = min;
    input.max = max;
    input.step = 1;
    input.value = value;
    input.setAttribute('aria-label', label);
    let current = value;

    const commit = (raw) => {
      const n = Math.round(Number(raw));
      if (raw === '' || !Number.isFinite(n)) {
        input.value = current;
        restartClass(wrap, 'shake');
        return;
      }
      const v = Math.min(max, Math.max(min, n));
      if (v !== n) {
        restartClass(wrap, 'shake');
        showToast(`${label} can be ${min} to ${max}.`);
      }
      input.value = v;
      if (v !== current) {
        current = v;
        restartClass(input, 'bump');
        onCommit(v);
      }
    };

    const button = (dir) => {
      const b = el('button', 'stepper-btn', icon(dir > 0 ? 'plus' : 'minus'));
      b.type = 'button';
      b.setAttribute('aria-label', `${dir > 0 ? 'Increase' : 'Decrease'} ${label}`);
      b.addEventListener('click', () => commit(current + dir));
      return b;
    };

    input.addEventListener('change', () => commit(input.value));
    wrap.append(button(-1), input, button(1));
    return { el: wrap, set(v) { current = v; input.value = v; } };
  }

  const quantumStepper = createStepper({
    value: quantum, min: LIMITS.quantum[0], max: LIMITS.quantum[1], label: 'Turn length',
    onCommit: (v) => { quantum = v; invalidateResults(); },
  });
  $('quantum-mount').append(quantumStepper.el);

  /* ==========================================================
     4. PROCESS TABLE
     ========================================================== */
  function renderRows(justAdded) {
    rows.innerHTML = '';
    if (!processes.length) {
      rows.append(el('tr', 'empty-row', '<td colspan="5">No processes yet. Add one to begin.</td>'));
    }
    processes.forEach((p) => {
      const tr = el('tr', 'proc-row');
      tr.dataset.name = p.name;
      if (p.name === justAdded) tr.classList.add('row-in');

      const nameCell = el('td', '', `<span class="process-name"><i class="process-dot" style="background:${colorOf(p.name)}"></i>${p.name}</span>`);
      tr.append(nameCell);

      [
        ['at', 'Arrives', 'arrival time'],
        ['bt', 'Needs', 'CPU time needed'],
        ['priority', 'Priority', 'priority'],
      ].forEach(([key, shortLabel, longLabel]) => {
        const td = el('td', key === 'priority' ? 'col-priority' : '');
        td.dataset.label = shortLabel;
        const stepper = createStepper({
          value: p[key], min: LIMITS[key][0], max: LIMITS[key][1],
          label: `${p.name} ${longLabel}`,
          onCommit: (v) => { p[key] = v; invalidateResults(); },
        });
        td.append(stepper.el);
        tr.append(td);
      });

      const action = el('td', 'cell-remove');
      const remove = el('button', 'remove-button', icon('trash'));
      remove.type = 'button';
      remove.setAttribute('aria-label', `Remove ${p.name}`);
      remove.addEventListener('click', () => removeProcess(p.name));
      action.append(remove);
      tr.append(action);
      rows.append(tr);
    });

    $('process-count').textContent = `${processes.length} process${processes.length === 1 ? '' : 'es'}`;
    $('add-process').disabled = processes.length >= MAX_PROCESSES;
    $('table-note').textContent = processes.length >= MAX_PROCESSES
      ? `That's the maximum: ${MAX_PROCESSES} processes keeps the timeline easy to read.`
      : 'Tip: use + and − to change a number.';
  }

  function removeProcess(name) {
    const finish = () => {
      processes = processes.filter((p) => p.name !== name);
      renderRows();
      invalidateResults();
    };
    const tr = rows.querySelector(`[data-name="${name}"]`);
    if (tr && !reduceMotion.matches) {
      tr.classList.add('row-out');
      setTimeout(finish, 220);
    } else {
      finish();
    }
  }

  $('add-process').addEventListener('click', () => {
    if (processes.length >= MAX_PROCESSES) return;
    const name = NAMES.find((n) => !processes.some((p) => p.name === n));
    processes.push({ name, at: Math.min(processes.length, LIMITS.at[1]), bt: 3, priority: Math.min(processes.length + 1, LIMITS.priority[1]) });
    renderRows(name);
    invalidateResults();
    showToast(`${name} added. Change its numbers to make it yours.`);
  });

  /* ==========================================================
     5. RULE PICKER
     ========================================================== */
  const getRule = () => document.querySelector('input[name="rule"]:checked').value;

  function onRuleChange() {
    const mode = getRule();
    $('quantum-field').dataset.open = String(mode === 'RR');
    $('process-card').dataset.rule = mode;
    $('priority-hint').textContent = mode === 'PRIORITY' ? '1 goes first' : 'not used by this rule';
    invalidateResults();
  }
  document.querySelectorAll('input[name="rule"]').forEach((r) => r.addEventListener('change', onRuleChange));

  function selectRule(mode) {
    document.querySelector(`input[name="rule"][value="${mode}"]`).checked = true;
    onRuleChange();
  }

  $('sample-button').addEventListener('click', () => {
    processes = sampleProcesses();
    quantum = 2;
    quantumStepper.set(2);
    selectRule('FCFS');
    renderRows();
    showToast('Example loaded. Try a different rule and compare.');
  });

  /* ==========================================================
     6. SCHEDULERS  (each block also says WHY it was picked)
     ========================================================== */
  const idle = (start, end) => ({ name: 'IDLE', start, end, queue: [], reason: 'Nobody is here yet, so the CPU waits.' });

  function scheduleFCFS(list) {
    const ordered = [...list].sort((a, b) => a.at - b.at || byName(a, b));
    const segments = [];
    let time = 0;
    ordered.forEach((p, i) => {
      let wasIdle = false;
      if (p.at > time) { segments.push(idle(time, p.at)); time = p.at; wasIdle = true; }
      const end = time + p.bt;
      const queue = ordered.slice(i + 1).filter((q) => q.at <= end).map((q) => q.name);
      const reason = wasIdle
        ? `The CPU was free when ${p.name} arrived, so it starts right away.`
        : i === 0
          ? `${p.name} arrived first, so it gets the CPU first.`
          : `${p.name} has been waiting the longest, so it is next in line.`;
      segments.push({ name: p.name, start: time, end, queue, reason });
      time = end;
    });
    return segments;
  }

  function scheduleNonPreemptive(list, mode) {
    const cmp = mode === 'SJF'
      ? (a, b) => a.bt - b.bt || a.at - b.at || byName(a, b)
      : (a, b) => a.priority - b.priority || a.at - b.at || byName(a, b);
    const pending = list.map((p) => ({ ...p }));
    const segments = [];
    let time = 0;
    while (pending.length) {
      const ready = pending.filter((p) => p.at <= time).sort(cmp);
      if (!ready.length) {
        const next = Math.min(...pending.map((p) => p.at));
        segments.push(idle(time, next));
        time = next;
        continue;
      }
      const p = ready[0];
      pending.splice(pending.indexOf(p), 1);
      const end = time + p.bt;
      const queue = pending.filter((q) => q.at <= end).sort(cmp).map((q) => q.name);
      const tie = ready[1] && (mode === 'SJF' ? ready[1].bt === p.bt : ready[1].priority === p.priority);
      let reason;
      if (ready.length === 1) reason = `${p.name} is the only one waiting, so it goes.`;
      else if (mode === 'SJF') reason = `${p.name} needs just ${units(p.bt)}, the shortest of the ${ready.length} waiting.`;
      else reason = `${p.name} has priority ${p.priority}, the most important of the ${ready.length} waiting.`;
      if (tie) reason += ` It tied with ${ready[1].name} but arrived first.`;
      segments.push({ name: p.name, start: time, end, queue, reason });
      time = end;
    }
    return segments;
  }

  function scheduleRoundRobin(list, q) {
    const pending = [...list].sort((a, b) => a.at - b.at || byName(a, b)).map((p) => ({ ...p, remaining: p.bt }));
    const queue = [];
    const segments = [];
    let time = 0;
    let index = 0;
    const admit = () => { while (index < pending.length && pending[index].at <= time) queue.push(pending[index++]); };
    while (index < pending.length || queue.length) {
      if (!queue.length && pending[index].at > time) {
        segments.push(idle(time, pending[index].at));
        time = pending[index].at;
      }
      admit();
      const current = queue.shift();
      const before = current.remaining;
      const duration = Math.min(q, before);
      const start = time;
      time += duration;
      current.remaining -= duration;
      admit();
      if (current.remaining) queue.push(current);
      const reason = before <= q
        ? `${current.name} needs ${units(before)} and a turn lasts up to ${q}, so it can finish.`
        : `${current.name} gets a turn of ${units(q)}.`;
      segments.push({ name: current.name, start, end: time, queue: queue.map((p) => p.name), reason });
    }
    return segments;
  }

  function buildSchedule(mode, list, q) {
    const segments = mode === 'FCFS' ? scheduleFCFS(list)
      : mode === 'RR' ? scheduleRoundRobin(list, q)
      : scheduleNonPreemptive(list, mode);

    const left = new Map(list.map((p) => [p.name, p.bt]));
    segments.forEach((s) => {
      s.queue = s.queue.filter((n) => n !== s.name); // the running process isn't "waiting"
      if (s.name === 'IDLE') { s.finished = false; s.left = 0; return; }
      const remaining = left.get(s.name) - (s.end - s.start);
      left.set(s.name, remaining);
      s.left = remaining;
      s.finished = remaining === 0;
    });

    const completion = new Map();
    segments.forEach((s) => { if (s.finished) completion.set(s.name, s.end); });
    const stats = list.map((p) => {
      const done = completion.get(p.name);
      const turnaround = done - p.at;
      return { ...p, completion: done, turnaround, waiting: turnaround - p.bt };
    });
    const avg = (key) => stats.reduce((sum, p) => sum + p[key], 0) / stats.length;
    return { mode, quantum: q, segments, stats, total: segments[segments.length - 1].end, avgWait: avg('waiting'), avgTurn: avg('turnaround') };
  }

  /* ==========================================================
     7. RUN + PLAYBACK
     ========================================================== */
  function invalidateResults() {
    stopTimer();
    playing = false;
    result = null;
    shown = 0;
    prevZone = {};
    $('timeline-empty').hidden = false;
    $('stage').hidden = true;
    $('run-status').textContent = DEFAULT_STATUS;
    $('result-detail').hidden = true;
    setTakeaway('Ready to find out?', 'Run the same processes with different rules. Notice how the order changes, and who has to wait.');
    updateControls();
  }

  function run() {
    if (!processes.length) {
      showToast('Add at least one process first.');
      restartClass($('add-process'), 'shake');
      return;
    }
    stopTimer();
    result = buildSchedule(getRule(), processes, quantum);
    shown = 1;
    prevZone = {};
    $('timeline-empty').hidden = true;
    $('stage').hidden = false;
    markTried(result.mode);
    render({ animate: true });
    $('results').scrollIntoView({ behavior: reduceMotion.matches ? 'auto' : 'smooth', block: 'start' });
    if (shown < result.segments.length) startPlayback();
  }

  function stopTimer() { clearTimeout(timer); timer = null; }

  function startPlayback() {
    if (!result || shown >= result.segments.length) return;
    playing = true;
    updateControls();
    scheduleTick();
  }

  function scheduleTick() {
    stopTimer();
    timer = setTimeout(() => {
      if (!playing) return;
      advance();
      if (shown < result.segments.length) scheduleTick();
      else { playing = false; updateControls(); }
    }, tickMs);
  }

  function pause() {
    playing = false;
    stopTimer();
    updateControls();
  }

  function advance() {
    if (!result || shown >= result.segments.length) return;
    shown += 1;
    render({ animate: true });
  }

  function replay() {
    if (!result) return;
    stopTimer();
    shown = 1;
    prevZone = {};
    render({ animate: true });
    startPlayback();
  }

  $('run-button').addEventListener('click', run);
  $('play-button').addEventListener('click', () => {
    if (!result) return;
    if (playing) pause();
    else if (shown >= result.segments.length) replay();
    else startPlayback();
  });
  $('step-button').addEventListener('click', () => { pause(); advance(); });
  $('replay-button').addEventListener('click', replay);
  document.querySelectorAll('.speed button').forEach((b) => {
    b.addEventListener('click', () => {
      tickMs = Number(b.dataset.speed);
      document.querySelectorAll('.speed button').forEach((o) => o.setAttribute('aria-pressed', String(o === b)));
    });
  });

  function updateControls() {
    const total = result ? result.segments.length : 0;
    const complete = !!result && shown >= total;
    const play = $('play-button');
    play.disabled = !result;
    $('step-button').disabled = !result || complete;
    $('replay-button').disabled = !result;
    const label = playing ? 'Pause' : complete ? 'Play again' : shown > 1 ? 'Resume' : 'Play';
    if (play.dataset.label !== label) {
      play.dataset.label = label;
      play.innerHTML = `${icon(playing ? 'pause' : complete ? 'replay' : 'play', complete && !playing ? '' : 'fill')}<span>${label}</span>`;
      play.querySelector('.icon').classList.add('swap');
    }
    $('zone-cpu').classList.toggle('busy', playing && !!result && result.segments[shown - 1]?.name !== 'IDLE' && !complete);
  }

  /* ==========================================================
     8. RENDERING THE STAGE
     ========================================================== */
  const INSIGHTS = {
    FCFS: ['First in, first served.', 'Everyone is served in the order they arrived. If a long job is at the front, everyone behind it has to wait.'],
    SJF: ['Short jobs finish sooner.', 'Of the processes already waiting, the shortest one goes next. That usually lowers the average wait, but long jobs can be left waiting.'],
    PRIORITY: ['Important jobs go first.', 'The waiting process with the best priority goes next. In this lab, 1 is the most important.'],
    RR: ['Everyone gets a turn.', null],
  };

  function setTakeaway(title, copy) {
    const t = $('insight-title');
    const c = $('insight-copy');
    if (t.textContent === title && c.textContent === copy) return;
    t.textContent = title;
    c.textContent = copy;
    restartClass(t, 'swap');
    restartClass(c, 'swap');
  }

  function makeChip(name, zone, sub) {
    const chip = el('span', 'chip', sub ? `${name}<small>${sub}</small>` : name);
    chip.style.setProperty('--c', colorOf(name));
    if (zone === 'later') chip.classList.add('ghost');
    else if (prevZone[name] !== zone) chip.classList.add(`in-${zone}`);
    return chip;
  }

  function fillZone(container, nodes, emptyText) {
    container.innerHTML = '';
    if (!nodes.length) container.append(el('p', 'zone-empty', emptyText));
    else container.append(...nodes);
  }

  function render({ animate }) {
    const segs = result.segments;
    const total = segs.length;
    const complete = shown >= total;
    const seg = segs[shown - 1];

    renderStage(seg, complete);
    renderNarration(seg, complete);
    renderTimeline(animate, complete);

    $('run-status').textContent = complete
      ? `${RULES[result.mode].label}: finished at time ${result.total}.`
      : `${RULES[result.mode].label}${result.mode === 'RR' ? `, turns of ${units(result.quantum)}` : ''}. Step ${shown} of ${total}.`;

    renderTakeaway(complete);
    updateControls();
  }

  function renderStage(seg, complete) {
    const segs = result.segments;
    const idx = shown - 1;

    const doneOrder = [];
    for (let i = 0; i < idx; i++) if (segs[i].finished) doneOrder.push(segs[i].name);
    if (complete && seg.finished) doneOrder.push(seg.name);
    const doneSet = new Set(doneOrder);

    const waiting = complete ? [] : seg.queue;
    const waitSet = new Set(waiting);
    const current = !complete && seg.name !== 'IDLE' ? seg.name : null;
    const later = processes.filter((p) => !doneSet.has(p.name) && !waitSet.has(p.name) && p.name !== current);

    const zoneOf = {};
    doneOrder.forEach((n) => { zoneOf[n] = 'done'; });
    waiting.forEach((n) => { zoneOf[n] = 'waiting'; });
    later.forEach((p) => { zoneOf[p.name] = 'later'; });
    if (current) zoneOf[current] = 'cpu';

    fillZone($('chips-later'), later.map((p) => makeChip(p.name, 'later', `at ${p.at}`)), 'Everyone is here');
    fillZone($('chips-waiting'), waiting.map((n) => makeChip(n, 'waiting')), 'Nobody is waiting');
    fillZone($('chips-done'), doneOrder.map((n) => makeChip(n, 'done')), 'None yet');

    const cpuZone = $('zone-cpu');
    const body = $('cpu-body');
    body.innerHTML = '';
    cpuZone.style.setProperty('--c', current ? colorOf(current) : '#d9ee78');
    $('stage').style.setProperty('--tick', `${tickMs}ms`);

    if (complete) {
      body.append(el('div', 'cpu-done', icon('check')), el('p', 'cpu-label', '<b>All done!</b>'), el('p', 'clock', `Finished at time ${result.total}`));
    } else if (seg.name === 'IDLE') {
      body.append(el('div', 'cpu-idle', icon('cpu')), el('p', 'cpu-label', 'The CPU is idle'), el('p', 'clock', `Time ${seg.start} to ${seg.end}`));
    } else {
      const chip = makeChip(seg.name, 'cpu');
      chip.classList.add('lg');
      const bar = el('div', 'cpu-progress', '<i></i>');
      bar.style.setProperty('--c', colorOf(seg.name));
      body.append(chip, el('p', 'cpu-label', `<b>${seg.name}</b> is running`), bar, el('p', 'clock', `Time ${seg.start} to ${seg.end}`));
    }
    prevZone = zoneOf;
  }

  function renderNarration(seg, complete) {
    const total = result.segments.length;
    $('step-count').textContent = `Step ${shown} of ${total}`;
    let title;
    let text;
    if (seg.name === 'IDLE') {
      title = `Time ${seg.start} to ${seg.end}: the CPU is idle`;
      text = seg.reason;
    } else {
      title = `${seg.name} uses the CPU from ${seg.start} to ${seg.end}`;
      text = `${seg.reason} ${seg.finished
        ? `It finishes at time ${seg.end}.`
        : `It still needs ${units(seg.left)}, so it goes to the back of the line.`}`;
    }
    if (complete) text += ' That is every process done.';
    $('narration-title').textContent = title;
    $('narration-text').textContent = text;
    restartClass($('narration'), 'swap');
  }

  function renderTimeline(animate, complete) {
    const wrap = $('gantt-scroll');
    wrap.innerHTML = '';
    const gantt = el('div', 'gantt');
    gantt.setAttribute('role', 'img');
    gantt.setAttribute('aria-label', 'CPU schedule timeline');
    gantt.style.minWidth = `${Math.max(360, result.segments.length * 56)}px`;
    const last = result.segments.length - 1;

    result.segments.forEach((s, i) => {
      const seg = el('div', 'seg');
      seg.style.setProperty('--span', s.end - s.start);
      if (s.name === 'IDLE') seg.classList.add('idle');
      else seg.style.setProperty('--c', colorOf(s.name));
      if (i >= shown) seg.classList.add('pending');
      if (i === shown - 1) {
        if (!complete) seg.classList.add('current');
        if (animate) seg.classList.add('enter');
      }
      seg.title = s.name === 'IDLE'
        ? `CPU idle from ${s.start} to ${s.end}`
        : `${s.name} uses the CPU from ${s.start} to ${s.end}`;
      seg.innerHTML = `<div class="seg-bar">${s.name === 'IDLE' ? 'Idle' : s.name}</div><span class="seg-tick">${s.start}</span>${i === last ? `<span class="seg-tick end">${s.end}</span>` : ''}`;
      gantt.append(seg);
    });
    wrap.append(gantt);
  }

  /* ==========================================================
     9. TAKEAWAY: numbers, bars, comparison
     ========================================================== */
  function countUp(node, to) {
    if (reduceMotion.matches) { node.textContent = to.toFixed(1); return; }
    const t0 = performance.now();
    const step = (t) => {
      const k = Math.min(1, (t - t0) / 800);
      node.textContent = (to * (1 - Math.pow(1 - k, 3))).toFixed(1);
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  function renderTakeaway(complete) {
    const detail = $('result-detail');
    if (!complete) {
      detail.hidden = true;
      setTakeaway('Watch the line move.', 'Follow the coloured blocks. The CPU picks who goes next, one step at a time.');
      return;
    }
    const mode = result.mode;
    const [title, copy] = INSIGHTS[mode];
    setTakeaway(title, copy || `Each process gets up to ${units(result.quantum)}. If it needs more, it goes to the back of the line.`);
    detail.hidden = false;

    // headline numbers
    const metrics = $('metrics');
    metrics.innerHTML = `
      <div class="metric"><strong><span data-count>0.0</span> <small>units</small></strong><b>Average wait</b><em>Time spent in line</em></div>
      <div class="metric"><strong><span data-count>0.0</span> <small>units</small></strong><b>Average turnaround</b><em>From arriving to finishing</em></div>`;
    const counters = metrics.querySelectorAll('[data-count]');
    countUp(counters[0], result.avgWait);
    countUp(counters[1], result.avgTurn);

    // one bar per process: waiting + running
    const bars = $('bars');
    bars.innerHTML = '';
    const longest = Math.max(...result.stats.map((p) => p.turnaround));
    result.stats.forEach((p, i) => {
      const row = el('div', 'bar-row');
      row.innerHTML = `
        <span class="bar-name">${p.name}</span>
        <div class="bar-track"><div class="bar-fill" style="--w:${(p.turnaround / longest) * 100};--wait:${p.waiting};--run:${p.bt};--c:${colorOf(p.name)};--i:${i}"><span class="bar-wait"></span><span class="bar-run"></span></div></div>
        <span class="bar-note">waited <b>${p.waiting}</b></span>`;
      bars.append(row);
    });

    // how every rule did on the same processes
    const compare = $('compare');
    compare.innerHTML = '';
    const results = Object.keys(RULES).map((m) => (m === mode ? result : buildSchedule(m, processes, quantum)));
    const worst = Math.max(...results.map((r) => r.avgWait), 0.001);
    const best = Math.min(...results.map((r) => r.avgWait));
    results.forEach((r, i) => {
      const isBest = r.avgWait === best;
      const row = el('button', `compare-row${isBest ? ' best' : ''}`);
      row.type = 'button';
      row.setAttribute('aria-current', String(r.mode === mode));
      row.setAttribute('aria-label', `${RULES[r.mode].label}: average wait ${r.avgWait.toFixed(1)}${r.mode === mode ? ', the rule you just ran' : ''}${isBest ? ', lowest wait' : ''}`);
      const tag = r.mode === mode ? 'you ran this' : isBest ? 'lowest wait' : '';
      row.innerHTML = `
        <span class="compare-label">${RULES[r.mode].label}${tag ? `<small>${tag}</small>` : ''}</span>
        <span class="compare-bar"><i style="--w:${Math.max(5, (r.avgWait / worst) * 100)};--i:${i}"></i></span>
        <span class="compare-val">${r.avgWait.toFixed(1)}</span>`;
      if (r.mode !== mode) row.addEventListener('click', () => { selectRule(r.mode); run(); });
      compare.append(row);
    });
  }

  /* ==========================================================
     10. SIDEBAR CHALLENGE
     ========================================================== */
  function burst(host) {
    if (reduceMotion.matches) return;
    for (let i = 0; i < 8; i++) {
      const s = el('i', 'spark');
      const angle = (Math.PI * 2 * i) / 8;
      s.style.setProperty('--dx', `${Math.cos(angle) * 30}px`);
      s.style.setProperty('--dy', `${Math.sin(angle) * 30}px`);
      s.style.background = palette[i % palette.length];
      host.append(s);
      setTimeout(() => s.remove(), 800);
    }
  }

  function markTried(mode) {
    if (tried.has(mode)) return;
    tried.add(mode);
    const li = document.querySelector(`#challenge-list [data-rule="${mode}"]`);
    li.classList.add('done', 'just-done');
    burst(li);
    $('challenge-count').textContent = `${tried.size} of 4 tried`;
    if (tried.size === 4) {
      $('challenge-note').textContent = 'You have seen them all! Which rule had the lowest average wait?';
      showToast('You tried all four rules. Which one made people wait the least?');
      burst($('challenge-count'));
    }
  }

  /* ==========================================================
     11. HELP DIALOG, NAV HIGHLIGHT, KEYBOARD
     ========================================================== */
  const dialog = $('help-dialog');
  $('help-button').addEventListener('click', () => dialog.showModal());
  $('help-close').addEventListener('click', () => dialog.close());
  $('help-done').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.close(); });

  /* ---- views: home dashboard and the process lab ---- */
  const LAB_IDS = ['lab', 'setup', 'run', 'results', 'words'];
  let currentView = null;

  function showView(name) {
    const isLab = name === 'lab';
    $('view-home').hidden = isLab;
    $('view-lab').hidden = !isLab;
    $('challenge').hidden = !isLab;
    $('crumb').textContent = isLab ? 'Process lab' : 'Home';
    const [on, off] = isLab ? [$('nav-lab'), $('nav-home')] : [$('nav-home'), $('nav-lab')];
    on.setAttribute('aria-current', 'page');
    off.removeAttribute('aria-current');
    currentView = name;
  }

  function route() {
    const id = location.hash.slice(1);
    const next = LAB_IDS.includes(id) ? 'lab' : 'home';
    const changed = next !== currentView;
    if (changed) showView(next);
    if (next === 'lab' && id && (changed || id === 'lab')) {
      $(id).scrollIntoView({ behavior: 'auto', block: 'start' });
    } else if (changed) {
      window.scrollTo(0, 0);
    }
  }
  window.addEventListener('hashchange', route);
  $('cta-lab').addEventListener('click', () => { location.hash = 'lab'; });

  // labs that are still being built
  document.querySelectorAll('[data-soon]').forEach((b) => {
    b.addEventListener('click', () => showToast(`Coming soon. ${b.dataset.soon}`));
  });

  // is the backend running? the lab works either way
  async function checkBackend() {
    const dot = $('api-dot');
    const text = $('api-text');
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 1500);
    try {
      const res = await fetch('http://127.0.0.1:8000/health', { signal: ctrl.signal });
      if (!res.ok) throw new Error('bad status');
      dot.dataset.state = 'on';
      text.textContent = 'Connected and healthy';
    } catch (e) {
      dot.dataset.state = 'off';
      text.textContent = 'Not running. The process lab still works.';
    } finally {
      clearTimeout(t);
    }
  }

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    if (['INPUT', 'SELECT', 'BUTTON', 'A', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
    if (document.querySelector('dialog[open]') || $('view-lab').hidden) return;
    run();
  });

  /* ==========================================================
     12. START
     ========================================================== */
  renderRows();
  onRuleChange();
  route();
  checkBackend();
})();
