export const content = {
  brand: 'Tutor IQ',
  nav: [
    { label: 'About us', href: '#how' },
    { label: 'For students', href: '#lab' },
    { label: 'For teachers', href: '#trust' },
    { label: 'How it works', href: '#how' },
  ],
  resources: [
    { label: 'All nine labs', href: '#labs' },
    { label: 'Common questions', href: '#faq' },
    { label: 'Process lab', href: '#lab' },
  ],
  hero: {
    before: 'Helping every student see how computers',
    mark: 'think',
    sub: 'Friendly hands-on labs that show what your computer does behind the scenes. Run it, watch it, and learn why, one small step at a time.',
  },
  dash: {
    welcome: 'Welcome to OS-DBX Lab!',
    sidebar: ['Home', 'Process lab', 'Query watcher', 'Progress', 'Settings'],
    next: { title: 'Process lab: who does the cashier serve next?', meta: 'Round robin · about 10 minutes' },
    week: [
      { day: 'Mon', items: ['Process lab'] }, { day: 'Tue', items: ['Query watcher'] },
      { day: 'Wed', items: ['Transactions'] }, { day: 'Thu', items: ['Deadlock graph'] },
    ],
    summary: { title: 'Last run', body: 'FCFS made processes wait 3.25 time units on average. Shortest job first did better at 2.00. Why do you think that happened?' },
  },
  how: [
    { t: 'Add some processes', d: 'Imagine customers arriving at a cashier, each needing a different amount of time.' },
    { t: 'Choose a rule', d: 'Try first come first served, shortest job first, priority or round robin.' },
    { t: 'Watch and learn', d: 'Every step comes with a plain-English reason so you know why the CPU chose it.' },
  ],
  trust: [
    { t: 'A safe sandbox', d: 'Everything runs in your browser. Nothing is uploaded and nothing can break.' },
    { t: 'Plain-English help', d: 'No jargon walls. Hard words come with a short, friendly explanation.' },
    { t: 'Works offline', d: 'Once loaded, the labs keep working without a connection.' },
    { t: 'Any device', d: 'Designed for phones, tablets and laptops, with keyboard support throughout.' },
  ],
  labs: [
    { n: '01', t: 'Process lab', d: 'Schedule processes on the CPU.', live: true },
    { n: '02', t: 'Query watcher', d: 'See how long each database question takes.' },
    { n: '03', t: 'Transactions', d: 'Try BEGIN, READ, WRITE and COMMIT.' },
    { n: '04', t: 'Connect the dots', d: 'Link a program to the query it sent.' },
    { n: '05', t: 'Deadlock graph', d: 'Spot the circle of waiting.' },
    { n: '06', t: 'Incident replay', d: 'Rewind a problem to its cause.' },
    { n: '07', t: 'Conflict checker', d: 'Can these transactions run together?' },
    { n: '08', t: 'Recovery sandbox', d: 'Crash it, then watch REDO and UNDO.' },
    { n: '09', t: 'Impact & speed', d: 'Which slow query hurts most?' },
  ],
  faq: [
    { q: 'Do I need to install anything?', a: 'No. The labs run in your browser and need no account.' },
    { q: 'Is it safe to experiment?', a: 'Yes. It is a sandbox, so you can try anything and press replay.' },
    { q: 'What is a process?', a: 'A running program. In the lab, each process is a customer waiting for the CPU cashier.' },
    { q: 'When do the other labs arrive?', a: 'Lab 01 is ready now. The others unlock as they are built.' },
  ],
  footer: 'OS-DBX · A friendly sandbox for learning operating systems and databases.',
};
