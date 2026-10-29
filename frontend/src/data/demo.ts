export type SectionId = 'overview' | 'observatory' | 'correlation' | 'incidents' | 'performance' | 'simulations' | 'whatif' | 'admin';

export interface ActivityEvent {
  time: string;
  source: 'OS' | 'DBMS' | 'CORRELATION';
  title: string;
  detail: string;
  status: 'linked' | 'observed' | 'attention';
}

export interface QueryObservation {
  id: string;
  type: string;
  statement: string;
  duration: string;
  rows: string;
  thread: string;
  state: string;
}

export const sidebarGroups: { label: string; items: { id: SectionId; label: string; icon: string }[] }[] = [
  { label: 'Workspace', items: [{ id: 'overview', label: 'Overview', icon: 'grid' }] },
  { label: 'Observe', items: [
    { id: 'observatory', label: 'Live observatory', icon: 'activity' },
    { id: 'correlation', label: 'Correlation', icon: 'nodes' },
    { id: 'incidents', label: 'Incidents', icon: 'shield' },
    { id: 'performance', label: 'Performance', icon: 'chart' },
  ] },
  { label: 'Explore', items: [
    { id: 'simulations', label: 'Simulation labs', icon: 'flask' },
    { id: 'whatif', label: 'What-if scenarios', icon: 'spark' },
  ] },
  { label: 'Manage', items: [{ id: 'admin', label: 'Administration', icon: 'settings' }] },
];

export const pageMeta: Record<SectionId, { title: string; subtitle: string; tag: string }> = {
  overview: { title: 'Overview', subtitle: 'A shared view of operating system and database activity.', tag: 'Workspace' },
  observatory: { title: 'Live observatory', subtitle: 'Inspect process activity, resource use, filesystem events, and captured SQL.', tag: 'Monitoring' },
  correlation: { title: 'Correlation explorer', subtitle: 'Follow the evidence that connects a process to database work.', tag: 'Cross-layer' },
  incidents: { title: 'Incident center', subtitle: 'Investigate deadlocks and review their supporting trace evidence.', tag: 'Investigation' },
  performance: { title: 'Performance & benchmarks', subtitle: 'Review system and query measurements, then explore workload behavior.', tag: 'Measurement' },
  simulations: { title: 'Simulation labs', subtitle: 'Explore classic OS and DBMS algorithms with transparent inputs and outcomes.', tag: 'Learning lab' },
  whatif: { title: 'What-if analysis', subtitle: 'Compare hypothetical workloads, schedules, and recovery outcomes.', tag: 'Analysis' },
  admin: { title: 'Administration', subtitle: 'Review access, account details, and recorded actions.', tag: 'Workspace controls' },
};

export const events: ActivityEvent[] = [
  { time: '10:42:18.240', source: 'OS', title: 'Process observed', detail: 'checkout-api, Process ID 4211, resource sample', status: 'observed' },
  { time: '10:42:18.311', source: 'DBMS', title: 'Query captured', detail: 'UPDATE inventory, 18.4 ms, 1 row', status: 'observed' },
  { time: '10:42:18.329', source: 'CORRELATION', title: 'Trace link created', detail: 'Process ID 4211 to transaction TX-208, direct identity', status: 'linked' },
  { time: '10:41:55.006', source: 'OS', title: 'File modified', detail: '/srv/app/cache/catalog.json, Process ID unavailable', status: 'attention' },
  { time: '10:41:41.772', source: 'DBMS', title: 'Lock wait observed', detail: 'TX-208 waiting on inventory:sku:104', status: 'attention' },
];

export const observations: QueryObservation[] = [
  { id: 'OBS-8842', type: 'Update', statement: 'UPDATE inventory SET stock = stock - 1 WHERE sku = ?', duration: '18.4 ms', rows: '1', thread: 'THR-73', state: 'Captured' },
  { id: 'OBS-8841', type: 'Select', statement: 'SELECT price, stock FROM inventory WHERE sku = ?', duration: '4.8 ms', rows: '1', thread: 'THR-73', state: 'Captured' },
  { id: 'OBS-8840', type: 'Insert', statement: 'INSERT INTO orders (customer_id, status) VALUES (?, ?)', duration: '12.1 ms', rows: '1', thread: 'THR-68', state: 'Captured' },
  { id: 'OBS-8839', type: 'Select', statement: 'SELECT id, status FROM orders WHERE customer_id = ?', duration: '7.2 ms', rows: '4', thread: 'THR-68', state: 'Captured' },
];

export const scenarioNames = ['Checkout inventory contention', 'Serializable schedule review', 'Crash recovery after checkpoint'];
