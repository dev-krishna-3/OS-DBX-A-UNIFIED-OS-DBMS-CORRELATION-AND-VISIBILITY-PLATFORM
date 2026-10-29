import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, LazyMotion, domAnimation, m, useReducedMotion } from 'framer-motion';
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Bell, BookOpen, Check,
  ChevronDown, ChevronRight, CircleHelp, Clock3, Database, FileClock,
  FlaskConical, GitBranch, LayoutDashboard, ListFilter, LockKeyhole,
  Monitor, Network, Palette, Play, Search, Settings, ShieldAlert, Sparkles,
  Waypoints, X,
} from 'lucide-react';
import { events, pageMeta, sidebarGroups, type ActivityEvent, type SectionId } from './data/demo';
import AuthPage from './features/auth/AuthPage';
import { analysisApi, authApi, checkApiHealth, correlationApi, getJson, hasAccessToken, incidentsApi, observabilityApi, simulationsApi, workflowsApi } from './api';
import type { AuthUser } from './api/auth';

const iconMap = {
  grid: LayoutDashboard, activity: Activity, nodes: Waypoints, shield: ShieldAlert,
  chart: Activity, flask: FlaskConical, spark: Sparkles, settings: Settings,
};

const tabs: Record<SectionId, string[]> = {
  overview: ['Overview'],
  observatory: ['Unified console', 'OS activity', 'Process & resources', 'DBMS observations', 'Transactions & locks'],
  correlation: ['Explorer', 'Manual correlation', 'Identity bridge', 'Trace library'],
  incidents: ['Deadlocks', 'Investigation', 'Blast radius', 'Fingerprints', 'Replay'],
  performance: ['System health', 'Performance records', 'Benchmarks'],
  simulations: ['OS simulations', 'DBMS simulations'],
  whatif: ['Schedule analysis', 'Recovery experiment', 'OS workload', 'Saved scenarios'],
  admin: ['Audit log', 'Accounts & sign-in'],
};

const headings: Record<string, string> = {
  'Unified console': 'Unified OS → DBMS console',
  'OS activity': 'OS event stream',
  'Process & resources': 'Processes & resource usage',
  'DBMS observations': 'DBMS query observations',
  'Transactions & locks': 'Transactions & locks',
  'Manual correlation': 'Manual correlation',
  Explorer: 'Correlation explorer',
  'Identity bridge': 'Identity bridge',
  'Trace library': 'Cross-layer traces',
  Deadlocks: 'Deadlock incidents',
  Investigation: 'Incident investigation',
  'Blast radius': 'Blast radius analysis',
  Fingerprints: 'Incident fingerprints',
  Replay: 'Forensic replay',
  'System health': 'System health',
  'Performance records': 'Performance records',
  Benchmarks: 'Benchmark workload lab',
  'OS simulations': 'OS simulation lab',
  'DBMS simulations': 'DBMS simulation lab',
  'Schedule analysis': 'Schedule analysis',
  'Recovery experiment': 'Recovery experiment',
  'OS workload': 'OS workload & contention',
  'Saved scenarios': 'Saved what-if scenarios',
  'Audit log': 'Audit log',
  'Accounts & sign-in': 'Accounts & sign-in',
};

type ThemeId = 'original' | 'orchid' | 'cobalt' | 'coral';

const themeOptions: { id: ThemeId; name: string; note: string; colors: string[] }[] = [
  { id: 'original', name: 'Lavender', note: 'Soft and calm · Default', colors: ['#f5f4fa', '#eeecf5', '#7665bd', '#dff1e9'] },
  { id: 'orchid', name: 'Violet', note: 'A little richer', colors: ['#e8e3f1', '#d9cfe8', '#7056b3', '#b9cbea'] },
  { id: 'cobalt', name: 'Blue', note: 'Cool and clear', colors: ['#dce6ee', '#c8d8e6', '#2f6298', '#edaa71'] },
  { id: 'coral', name: 'Coral', note: 'Warm with a hint of teal', colors: ['#e8e2dc', '#e9d1c8', '#bb5746', '#c5d9d1'] },
];

function App() {
  const prefersReducedMotion = useReducedMotion();
  const [section, setSection] = useState<SectionId>('overview');
  const [activeTab, setActiveTab] = useState('Overview');
  const [search, setSearch] = useState('');
  const [notice, setNotice] = useState('');
  const [guidedStep, setGuidedStep] = useState(-1);
  const [selectedAlgorithm, setSelectedAlgorithm] = useState('Round Robin');
  const [theme, setTheme] = useState<ThemeId>('original');
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [authReady, setAuthReady] = useState(() => !hasAccessToken());
  const [apiConnected, setApiConnected] = useState(false);

  useEffect(() => {
    const refresh = () => void checkApiHealth().then(setApiConnected);
    refresh();
    const timer = window.setInterval(refresh, 15000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!hasAccessToken()) return;
    let active = true;
    void authApi.currentUser()
      .then((user) => { if (active) setCurrentUser(user); })
      .catch(() => { authApi.signOut(); })
      .finally(() => { if (active) setAuthReady(true); });
    return () => { active = false; };
  }, []);

  const title = section === 'overview' ? pageMeta.overview.title : (headings[activeTab] ?? pageMeta[section].title);
  const filteredEvents = useMemo(() => events.filter((event) => `${event.title} ${event.detail} ${event.source}`.toLowerCase().includes(search.toLowerCase())), [search]);

  const openSection = (id: SectionId) => {
    setSection(id);
    setActiveTab(tabs[id][0]);
    setSearch('');
  };

  const notify = (message: string) => {
    setNotice(message);
    window.setTimeout(() => setNotice(''), 2800);
  };

  if (!authReady) return <main className="auth-session-loading"><span className="brand-mark" aria-hidden="true"><span /><span /><span /></span><p>Restoring your OS-DBX session…</p></main>;

  if (!currentUser) return <AuthPage onAuthenticated={(user, emailNotificationSent) => {
    setCurrentUser(user);
    setAuthReady(true);
    if (!emailNotificationSent) notify('Signed in, but the email alert was not sent. Check the account email and SMTP configuration.');
  }} />;

  return (
    <LazyMotion features={domAnimation}>
    <div className="app-shell" data-theme={theme}>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <div className="workspace">
        <header className="app-header">
          <div className="topbar">
            <a className="brand-lockup" href="#main-content" aria-label="OS-DBX home">
              <div className="brand-mark" aria-hidden="true"><span /><span /><span /></div>
              <span className="brand-wordmark">OS-DBX</span>
              <span className="brand-caption">Cross-layer observability</span>
            </a>
          <div className="breadcrumb"><strong>{title}</strong></div>
          <div className="topbar-actions">
            <label className="search-box"><Search size={16} /><input aria-label="Search sample activity" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search activity" /><kbd>⌘ K</kbd></label>
            <button type="button" className="icon-button header-utility" aria-label="Help" onClick={() => notify('Help is available in the project guide.')}><CircleHelp size={18} /></button>
            <button type="button" className="icon-button header-utility" aria-label="Notifications" onClick={() => notify('You are viewing a local demo workspace.')}><Bell size={18} /></button>
            <span className="topbar-env">{apiConnected ? 'API connected · samples remain labeled' : 'API unavailable'}</span>
            <button type="button" className="profile-mini" aria-label={`Open administration for ${currentUser.username}`} onClick={() => openSection('admin')}><span className="profile-avatar" aria-hidden="true" /> {currentUser.username}</button>
          </div>
          </div>
          <nav id="primary-navigation" className="primary-nav" aria-label="Main navigation">
            {sidebarGroups.flatMap((group) => group.items).map((item) => {
              const Icon = iconMap[item.icon as keyof typeof iconMap];
              return <button type="button" key={item.id} className={`primary-nav-item ${section === item.id ? 'active' : ''}`} onClick={() => openSection(item.id)} aria-current={section === item.id ? 'page' : undefined}>
                <Icon size={16} strokeWidth={1.8} /><span>{item.label}</span>{item.id === 'incidents' && <span className="nav-count">2</span>}
              </button>;
            })}
            <button type="button" className={`primary-nav-item theme-nav-toggle ${paletteOpen ? 'active' : ''}`} aria-expanded={paletteOpen} aria-controls="theme-preview-panel" onClick={() => setPaletteOpen((open) => !open)}><Palette size={16} /><span>Theme preview</span></button>
          </nav>
          <AnimatePresence initial={false}>
          {paletteOpen && <m.section className="theme-preview-panel" id="theme-preview-panel" aria-label="Temporary theme preview"
            initial={prefersReducedMotion ? false : { opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, y: -4 }}
            transition={{ duration: prefersReducedMotion ? 0 : 0.16, ease: 'easeOut' }}>
            <div className="theme-preview-heading"><div><h2>Pick a theme</h2><p>Choose a look for your workspace. Preview resets on reload.</p></div><button type="button" className="icon-button" aria-label="Close theme preview" onClick={() => setPaletteOpen(false)}><X size={17} /></button></div>
            <div className="theme-preview-options" role="group" aria-label="Theme options">
              {themeOptions.map((option) => <button type="button" key={option.id} className={`theme-option ${theme === option.id ? 'selected' : ''}`} aria-pressed={theme === option.id} onClick={() => setTheme(option.id)}>
                <span className="theme-swatches" aria-hidden="true">{option.colors.map((color) => <i key={color} style={{ backgroundColor: color }} />)}</span>
                <span className="theme-option-copy"><strong>{option.name}</strong><small>{option.note}</small></span>
                {theme === option.id && <Check size={16} className="theme-option-check" />}
              </button>)}
            </div>
          </m.section>}
          </AnimatePresence>
        </header>

        <main id="main-content" className="main-content">
          <div className="page-heading">
            <div><h1>{title}</h1><p>{pageMeta[section].subtitle}</p></div>
            <div className="heading-actions">
              <button className="button button-secondary" type="button" onClick={() => notify('Sample view refreshed.')}> <Clock3 size={15} /> 10:30 to 10:45 UTC <ChevronDown size={14} /></button>
              <button className="button button-primary" type="button" onClick={() => { setSection('observatory'); setActiveTab('Unified console'); setGuidedStep(0); }}><Play size={15} fill="currentColor" /> Run guided demo</button>
            </div>
          </div>

          {section !== 'overview' && <div className="tabs-bar" role="tablist" aria-label={`${pageMeta[section].title} views`}>
            {tabs[section].map((tab) => <button key={tab} type="button" role="tab" aria-selected={activeTab === tab} className={`view-tab ${activeTab === tab ? 'selected' : ''}`} onClick={() => setActiveTab(tab)}>{tab}</button>)}
          </div>}

          <AnimatePresence mode="wait" initial={false}>
          <m.div className="view-transition" key={`${section}-${activeTab}`}
            style={{ display: section === 'overview' ? 'contents' : 'block' }}
            initial={prefersReducedMotion ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, y: -4 }}
            transition={{ duration: prefersReducedMotion ? 0 : 0.18, ease: 'easeOut' }}>
            {section === 'overview'
              ? <Overview events={filteredEvents} guidedStep={guidedStep} onRunDemo={() => { setSection('observatory'); setActiveTab('Unified console'); setGuidedStep(0); }} onNextStep={() => setGuidedStep((step) => (step + 1) % 5)} onOpen={(id) => openSection(id)} />
              : <FeaturePage section={section} tab={activeTab} events={filteredEvents} search={search} selectedAlgorithm={selectedAlgorithm} onAlgorithm={setSelectedAlgorithm} onAction={notify} guidedStep={guidedStep} onNextStep={() => setGuidedStep((step) => Math.min(step + 1, 4))} currentUser={currentUser} onSignOut={() => { authApi.signOut(); setCurrentUser(null); }} />}
          </m.div>
          </AnimatePresence>

          <footer className="page-footer"><span>OS-DBX project demonstration</span><span>All sample values are illustrative</span></footer>
        </main>
      </div>
      <AnimatePresence>
        {notice && <m.div className="toast" role="status" key="notice"
          initial={prefersReducedMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, y: 6 }}
          transition={{ duration: prefersReducedMotion ? 0 : 0.18, ease: 'easeOut' }}>
          <Check size={16} />{notice}<button type="button" onClick={() => setNotice('')} aria-label="Dismiss"><X size={15} /></button>
        </m.div>}
      </AnimatePresence>
    </div>
    </LazyMotion>
  );
}

function Overview({ events: visibleEvents, guidedStep, onRunDemo, onNextStep, onOpen }: { events: ActivityEvent[]; guidedStep: number; onRunDemo: () => void; onNextStep: () => void; onOpen: (id: SectionId) => void }) {
  return <>
    <div className="summary-row">
      <Metric label="OS events" value="1,284" change="+8.2%" up detail="Observed in sample window" tone="mint" icon={<Monitor size={17} />} />
      <Metric label="DBMS observations" value="386" change="+4.6%" up detail="Performance Schema sample" tone="lavender" icon={<Database size={17} />} />
      <Metric label="Correlated traces" value="42" change="3 need review" detail="Evidence-based links" tone="blue" icon={<GitBranch size={17} />} />
      <Metric label="Open incidents" value="02" change="1 high priority" detail="Deadlock investigations" tone="peach" icon={<ShieldAlert size={17} />} />
    </div>

    <section className="overview-feature trace-hero">
      <div className="feature-copy">
        <h2>One checkout.<br />Every layer in view.</h2>
        <p>Follow a checkout process from its operating-system identity to the database query and the evidence linking them.</p>
        <div className="feature-facts"><span><Check size={14} /> Process identity</span><span><Check size={14} /> Query evidence</span><span><Check size={14} /> Trace explanation</span></div>
        <button type="button" className="button button-primary feature-cta" onClick={onRunDemo}><Play size={15} fill="currentColor" /> Open guided console <ArrowRight size={15} /></button>
        <span className="sample-note">Local sample data, not connected to the backend</span>
      </div>
      <div className="trace-stage" role="img" aria-label="Illustrative trace connecting operating-system process evidence through a socket identity bridge to a database query">
        <div className="trace-stage-top"><span>Cross-layer trace</span><span className="trace-live-label"><i /> Sample evidence</span></div>
        <LayerDiagram />
        <div className="trace-stage-foot"><span><Monitor size={14} /> Process ID 4211</span><ArrowRight size={15} /><span><Network size={14} /> Socket → PID</span><ArrowRight size={15} /><span><Database size={14} /> OBS-8842</span></div>
      </div>
    </section>

    {guidedStep >= 0 && <section className="guided-strip"><div className="guided-icon"><Sparkles size={17} /></div><div className="guided-text"><strong>Guided demo, step {guidedStep + 1} of 5</strong><span>{['Choose the process identity', 'Inspect the socket-to-PID evidence', 'Review the captured SQL observation', 'Follow the cross-layer trace', 'Read the correlation explanation'][guidedStep]}</span></div><div className="guided-progress">{[0, 1, 2, 3, 4].map((step) => <i className={step <= guidedStep ? 'done' : ''} key={step} />)}</div><button type="button" className="text-action" onClick={onNextStep}>Next step <ArrowRight size={14} /></button></section>}

    <div className="overview-grid">
      <section className="surface-panel activity-panel">
        <div className="panel-heading"><div><h3>Activity across layers</h3><p>Recent events from the local demo dataset</p></div><button type="button" className="button button-quiet" onClick={() => onOpen('observatory')}>Open event stream <ArrowRight size={14} /></button></div>
        <EventList events={visibleEvents.slice(0, 4)} />
      </section>
      <section className="surface-panel incidents-panel">
        <div className="panel-heading"><div><h3>Needs attention</h3><p>Incidents and evidence gaps</p></div><span className="panel-count">02</span></div>
        <button type="button" className="incident-row" aria-label="Open deadlock incident" onClick={() => onOpen('incidents')}><span className="incident-icon warn"><LockKeyhole size={16} /></span><span className="incident-content"><strong>Deadlock</strong><small>High, 10:41:42</small></span><ChevronRight size={15} /></button>
        <button type="button" className="incident-row" aria-label="Review ambiguous query match" onClick={() => onOpen('correlation')}><span className="incident-icon info"><GitBranch size={16} /></span><span className="incident-content"><strong>Ambiguous</strong><small>2 candidates</small></span><ChevronRight size={15} /></button>
        <div className="evidence-note"><span>Filesystem activity may have no process attribution.</span></div>
      </section>
    </div>
  </>;
}

function Metric({ label, value, change, detail, up }: { label: string; value: string; change: string; detail: string; tone: string; icon: React.ReactNode; up?: boolean }) {
  return <div className="metric-block"><div className="metric-top"><span className="metric-label">{label}</span></div><div className="metric-value-row"><strong>{value}</strong><span className={`metric-change ${up ? 'positive' : ''}`}>{up ? <ArrowUpRight size={13} /> : null}{change}</span></div><span className="metric-detail">{detail}</span></div>;
}

function EventList({ events: eventRows }: { events: ActivityEvent[] }) {
  return <div className="event-list">{eventRows.length === 0 ? <div className="empty-state">No sample events match this search.</div> : eventRows.map((event, index) => <div className="event-row" key={`${event.time}-${index}`}>
    <time>{event.time}</time><span className={`event-source source-${event.source.toLowerCase()}`}>{event.source === 'OS' ? 'OS activity' : event.source === 'DBMS' ? 'Database' : 'Correlation'}</span>
    <span className="event-copy"><strong>{event.title}</strong><small>{event.detail}</small></span>{event.status === 'linked' ? <span className="state-label state-linked">Linked</span> : event.status === 'attention' ? <span className="state-label state-review">Review</span> : <span className="state-label state-observed">Observed</span>}
  </div>)}</div>;
}

function FeaturePage({ section, tab, events: visibleEvents, search, selectedAlgorithm, onAlgorithm, onAction, guidedStep, onNextStep, currentUser, onSignOut }: {
  section: SectionId; tab: string; events: ActivityEvent[]; search: string; selectedAlgorithm: string; onAlgorithm: (value: string) => void; onAction: (message: string) => void; guidedStep: number; onNextStep: () => void; currentUser: AuthUser; onSignOut: () => void;
}) {
  if (section === 'observatory' && tab === 'Unified console') return <UnifiedConsole guidedStep={guidedStep} onNextStep={onNextStep} onAction={onAction} />;
  if (section === 'observatory' && tab === 'DBMS observations') return <Observations onAction={onAction} />;
  if (section === 'observatory' && tab === 'Process & resources') return <ProcessView />;
  if (section === 'observatory' && tab === 'Transactions & locks') return <TransactionsLocks />;
  if (section === 'observatory') return <OSActivity events={visibleEvents} search={search} onAction={onAction} />;
  if (section === 'correlation') return <Correlation tab={tab} onAction={onAction} />;
  if (section === 'incidents') return <Incidents tab={tab} onAction={onAction} />;
  if (section === 'performance') return <Performance tab={tab} onAction={onAction} />;
  if (section === 'simulations') return <Simulations tab={tab} selectedAlgorithm={selectedAlgorithm} onAlgorithm={onAlgorithm} onAction={onAction} />;
  if (section === 'whatif') return <WhatIf tab={tab} onAction={onAction} />;
  return <Administration tab={tab} currentUser={currentUser} onSignOut={onSignOut} />;
}

function UnifiedConsole({ guidedStep, onNextStep, onAction }: { guidedStep: number; onNextStep: () => void; onAction: (message: string) => void }) {
  const stages = ['Process', 'Identity', 'Query', 'Trace', 'Explanation'];
  const [selectedProcess, setSelectedProcess] = useState('checkout-api, Process ID 4211');
  const [workflow, setWorkflow] = useState('Direct identity walkthrough');
  return <>
    <div className="console-callout"><div className="callout-mark"><Sparkles size={18} /></div><div><strong>Flagship demo: {workflow}</strong><p>Explore the Phase 2 demonstration paths using local sample data. No backend or live workload is invoked.</p></div><label className="workflow-select"><span>Demo path</span><select value={workflow} onChange={(event) => setWorkflow(event.target.value)}><option>Direct identity walkthrough</option><option>Live streaming observatory</option><option>Ad-hoc SQL causality</option><option>Real-world workload evaluator</option></select></label></div>
    <div className="console-layout">
      <section className="surface-panel console-main">
        <div className="panel-heading"><div><h3>Process-to-query trace</h3><p>Five connected views of one sample transaction</p></div><button type="button" className="button button-secondary" onClick={() => onAction('Trace view refreshed with local sample data.')}><Clock3 size={14} /> Sample, 10:42 UTC</button></div>
        <div className="stage-track">{stages.map((stage, index) => <button type="button" className={`stage-item ${index <= Math.max(guidedStep, 0) ? 'complete' : ''} ${index === guidedStep ? 'current' : ''}`} key={stage} onClick={() => onAction(`${stage} stage selected.`)}><span>{index < Math.max(guidedStep, 0) ? <Check size={13} /> : index + 1}</span><small>{stage}</small></button>)}</div>
        <div className="console-3d"><LayerDiagram compact /></div>
        <div className="trace-summary"><div><span className="summary-label">Identity evidence</span><strong>Socket local port 51,842 → Process ID 4211</strong></div><div><span className="summary-label">Query observation</span><strong>OBS-8842, UPDATE inventory, 18.4 ms</strong></div><div><span className="summary-label">Trace result</span><strong className="linked-text"><Check size={14} /> Direct link, TX-208</strong></div></div>
        <div className="console-footer"><span>Sample evidence, not a live correlation</span><button className="button button-primary" type="button" onClick={onNextStep}>Continue walkthrough <ArrowRight size={14} /></button></div>
      </section>
      <aside className="surface-panel evidence-panel"><div className="panel-heading"><div><h3>Evidence chain</h3><p>Source identifiers kept distinct</p></div></div>
        <label className="field-label" htmlFor="process-select">Observed process</label><select id="process-select" value={selectedProcess} onChange={(event) => setSelectedProcess(event.target.value)}><option>checkout-api, Process ID 4211</option><option>catalog-worker, Process ID 3980</option><option>payment-api, Process ID 4278</option></select>
        <EvidenceItem icon={<Monitor size={15} />} title="Operating system" detail="Process + resource sample" badge="Process ID 4211" tone="mint" />
        <EvidenceItem icon={<Network size={15} />} title="Identity bridge" detail="Socket maps to process" badge="Direct" tone="blue" />
        <EvidenceItem icon={<Database size={15} />} title="MySQL observation" detail="Performance Schema" badge="OBS-8842" tone="lavender" />
        <div className="source-distinction"><strong>Identifier note</strong><p>MySQL thread IDs identify DBMS sessions. They are not operating system PIDs.</p></div>
      </aside>
    </div>
  </>;
}

function LayerDiagram({ compact = false }: { compact?: boolean }) {
  return <div className={`layer-diagram ${compact ? 'compact-diagram' : ''}`} aria-label="Three dimensional stack linking process, identity bridge, and database query">
    <div className="diagram-stack">
      <div className="diagram-slab slab-os"><div className="slab-heading"><span className="slab-icon"><Monitor size={14} /></span><span>OS process</span><small>Process ID 4211</small></div><div className="slab-content"><span className="mini-process"><i /> checkout-api</span><span className="mini-usage">cpu use <b>4.8%</b></span><span className="mini-usage">Memory <b>186 MB</b></span></div><span className="slab-rail" /></div>
      <div className="diagram-thread thread-one" /><div className="diagram-thread thread-two" />
      <div className="diagram-slab slab-identity"><div className="bridge-label"><Waypoints size={15} /><span>Identity bridge</span><b>socket → PID</b></div><span className="bridge-light" /></div>
      <div className="diagram-slab slab-db"><div className="slab-heading"><span className="slab-icon"><Database size={14} /></span><span>DBMS query</span><small>OBS-8842</small></div><div className="slab-content"><span className="query-line"><b>Update</b> inventory</span><span className="query-meta">TX-208  18.4 ms</span></div><span className="db-check"><Check size={13} /></span></div>
    </div>
    {!compact && <div className="diagram-caption"><span>Deterministic identity match</span><span>Timestamp supports ordering, not identity</span></div>}
  </div>;
}

function EvidenceItem({ icon, title, detail, badge, tone }: { icon: React.ReactNode; title: string; detail: string; badge: string; tone: string }) {
  return <div className="evidence-item"><span className={`evidence-icon ${tone}`}>{icon}</span><span><strong>{title}</strong><small>{detail}</small></span><em>{badge}</em></div>;
}

function OSActivity({ search, onAction }: { events: ActivityEvent[]; search: string; onAction: (message: string) => void }) {
  const [collector, setCollector] = useState<{status?: string; is_active?: boolean; watch_paths?: string[]; adapter_health?: {status?: string}} | null>(null);
  const [liveEvents, setLiveEvents] = useState<Array<{id?: number; event_type?: string; timestamp?: string; pid?: number | null; file_path?: string | null}>>([]);
  const [liveError, setLiveError] = useState('');
  const visibleFiles = liveEvents.filter((event) => `${event.event_type ?? ''} ${event.file_path ?? ''} ${event.pid ?? ''}`.toLowerCase().includes(search.toLowerCase()));
  const refresh = () => Promise.all([observabilityApi.osCollectorStatus<NonNullable<typeof collector>>(), observabilityApi.filesystemEvents<(typeof liveEvents)[number]>()])
    .then(([status, files]) => { setCollector(status); setLiveEvents(files); setLiveError(''); })
    .catch((error: unknown) => setLiveError(error instanceof Error ? error.message : 'Unable to reach the OS collector.'));
  useEffect(() => { void refresh(); const timer = window.setInterval(() => void refresh(), 10000); return () => window.clearInterval(timer); }, []);
  return <>
    <div className="stat-inline"><div><span>Filesystem events</span><strong>{liveEvents.length}</strong></div><div><span>Collector</span><strong>{collector?.status ?? 'Unknown'}</strong></div><div><span>Watched paths</span><strong>{collector?.watch_paths?.length ?? 0}</strong></div><div className="inline-status"><span>{liveError ? 'API unavailable' : collector?.is_active ? 'Live collector' : 'Collector stopped'}</span></div></div>
    <div className="content-two-col"><section className="surface-panel"><div className="panel-heading"><div><h3>Filesystem activity</h3><p>Live API records; files may not have process attribution</p></div><button type="button" className="button button-secondary" onClick={() => void refresh()}><ListFilter size={15} /> Refresh</button></div>{liveError ? <div className="empty-state">{liveError}</div> : visibleFiles.length ? <div className="table-wrap"><table><thead><tr><th>Time</th><th>Event</th><th>Path</th><th>Process</th></tr></thead><tbody>{visibleFiles.map((event) => <tr key={event.id}><td>{event.timestamp ? new Date(event.timestamp).toLocaleString() : '—'}</td><td>{event.event_type ?? '—'}</td><td>{event.file_path ?? '—'}</td><td>{event.pid ?? 'Not attributed'}</td></tr>)}</tbody></table></div> : <div className="empty-state">No filesystem events match this filter.</div>}</section>
      <section className="surface-panel narrow-panel"><div className="panel-heading"><div><h3>Collector health</h3><p>Windows OS collector</p></div></div><div className="health-state"><span className="health-symbol"><Monitor size={20} /></span><strong>{collector?.status ?? (liveError ? 'Unavailable' : 'Loading')}</strong><p>{collector?.is_active ? 'The API reports an active collector.' : liveError || 'No collector is active.'}</p></div><div className="health-facts"><span>Adapter state <b>{collector?.adapter_health?.status ?? collector?.status ?? 'Unavailable'}</b></span><span>Watch paths <b>{collector?.watch_paths?.join(', ') || 'Not configured'}</b></span><span>Data source <b>Authenticated API</b></span></div></section>
    </div>
    <section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Filesystem activity</h3><p>Path-level evidence; process attribution may not be available</p></div><div className="heading-actions"><button type="button" className="button button-quiet" onClick={() => onAction('Filesystem capture test is unavailable while the collector is not connected.')}>Run capture test <Play size={13} /></button><button type="button" className="button button-quiet">Open file event view <ArrowRight size={14} /></button></div></div><div className="table-wrap"><table><thead><tr><th>Time</th><th>Event</th><th>Path</th><th>Process</th><th>Detail</th></tr></thead><tbody><tr><td>10:41:55.006</td><td><span className="event-tag tag-mint">Modified</span></td><td>/srv/app/cache/catalog.json</td><td><span className="muted-chip">Not attributed</span></td><td>File watcher sample</td></tr><tr><td>10:41:48.120</td><td><span className="event-tag tag-blue">Created</span></td><td>/srv/app/tmp/export-18.csv</td><td><span className="muted-chip">Not attributed</span></td><td>File watcher sample</td></tr></tbody></table></div></section>
  </>;
}

function ProcessView() {
  const [processes, setProcesses] = useState<Array<{pid: number; name?: string; state?: string; ppid?: number; user?: string; file_path?: string}>>([]);
  const [resources, setResources] = useState<Array<{pid: number; cpu_usage?: number; memory_usage?: number; disk_io?: number | null; name?: string}>>([]);
  const [error, setError] = useState('');
  const refresh = () => Promise.all([observabilityApi.processes<(typeof processes)[number]>(), observabilityApi.resources<(typeof resources)[number][]>()])
    .then(([items, metrics]) => { setProcesses(items); setResources(metrics); setError(''); })
    .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Unable to load processes.'));
  useEffect(() => { void refresh(); const timer = window.setInterval(() => void refresh(), 10000); return () => window.clearInterval(timer); }, []);
  return <><div className="stat-inline"><div><span>Processes returned</span><strong>{processes.length}</strong></div><div><span>Running</span><strong>{processes.filter((item) => item.state?.toLowerCase() === 'running').length}</strong></div><div className="inline-status"><span>{error ? 'API unavailable' : 'Live process snapshot'}</span></div></div>
    <section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Process table</h3><p>Current process snapshot and resource sample from the collector API</p></div><button type="button" className="button button-secondary" onClick={() => void refresh()}><ListFilter size={15} /> Refresh</button></div>{error ? <div className="empty-state">{error}</div> : processes.length ? <div className="table-wrap"><table><thead><tr><th>Process</th><th>Process ID</th><th>State</th><th>CPU %</th><th>Memory %</th><th>Disk I/O bytes</th><th>User</th></tr></thead><tbody>{processes.map((item) => { const metric = resources.find((row) => row.pid === item.pid); return <tr key={item.pid}><td>{item.name ?? 'Unknown'}</td><td>{item.pid}</td><td>{item.state ?? '—'}</td><td>{metric?.cpu_usage ?? '—'}</td><td>{metric?.memory_usage ?? '—'}</td><td>{metric?.disk_io ?? '—'}</td><td>{item.user ?? '—'}</td></tr>; })}</tbody></table></div> : <div className="empty-state">No process snapshot is available.</div>}</section>
  </>;
}

function Observations({ onAction }: { onAction: (message: string) => void }) {
  const [rows, setRows] = useState<Array<{observation_id?: number; source_thread_id: number; source_event_id: number; query_type: string; query_text: string; execution_time_ms: number; rows_affected: number; status: string; observed_at: string}>>([]);
  const [source, setSource] = useState<{status?: string; mode?: string; reason?: string} | null>(null);
  const [error, setError] = useState('');
  const refresh = () => Promise.all([observabilityApi.dbmsObservations<(typeof rows)[number]>(), observabilityApi.collectorStatus<NonNullable<typeof source>>()])
    .then(([items, status]) => { setRows(items); setSource(status); setError(''); })
    .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Unable to load DBMS observations.'));
  useEffect(() => { void refresh(); const timer = window.setInterval(() => void refresh(), 8000); return () => window.clearInterval(timer); }, []);
  const collect = async () => { try { const result = await observabilityApi.collectDbmsEvents<{collected: number; persisted: number}>({limit: 100, persist: true}); onAction(`Collected ${result.collected}; saved ${result.persisted} DBMS observations.`); await refresh(); } catch (cause) { onAction(cause instanceof Error ? cause.message : 'Collection failed.'); } };
  return <><div className="console-callout"><div className="callout-mark"><Database size={18} /></div><div><strong>MySQL statement source: {source?.status ?? 'Loading'}</strong><p>{source?.reason ?? source?.mode ?? 'Thread and event IDs are database source identifiers, not OS process IDs.'}</p></div><button type="button" className="button button-primary" onClick={() => void collect()}><Activity size={15} /> Collect now</button></div>
    <section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Recent statement observations</h3><p>Collected from the authenticated DBMS API</p></div><button type="button" className="button button-secondary" onClick={() => void refresh()}><Play size={14} /> Refresh</button></div>{error ? <div className="empty-state">{error}</div> : rows.length ? <div className="table-wrap"><table><thead><tr><th>Observation</th><th>Type</th><th>Statement</th><th>Duration</th><th>Rows</th><th>DBMS thread</th><th>State</th></tr></thead><tbody>{rows.map((row, index) => <tr key={row.observation_id ?? `${row.source_thread_id}-${row.source_event_id}-${index}`}><td><b>{row.observation_id ?? '—'}</b></td><td><span className="query-kind table-kind">{row.query_type}</span></td><td className="sql-cell">{row.query_text}</td><td>{row.execution_time_ms.toFixed(2)} ms</td><td>{row.rows_affected}</td><td>{row.source_thread_id}</td><td><span className="state-label state-observed">{row.status}</span></td></tr>)}</tbody></table></div> : <div className="empty-state">No DBMS statements are available. Run a workload and collect again.</div>}</section>
    <div className="note-banner"><BookOpen size={16} /><span><strong>Why this source matters</strong> MySQL statement history is bounded. These illustrative records represent observations, not a durable database audit log.</span></div>
  </>;
}

function Correlation({ tab, onAction }: { tab: string; onAction: (message: string) => void }) {
  if (tab === 'Explorer') return <LiveCorrelation onAction={onAction} />;
  if (tab === 'Identity bridge') return <div className="content-two-col"><section className="surface-panel bridge-main"><div className="panel-heading"><div><h3>Application identity path</h3><p>The application supplies process and transaction identity</p></div><span className="event-tag tag-mint">Deterministic</span></div><LayerDiagram /><div className="bridge-steps"><EvidenceItem icon={<Monitor size={15} />} title="Application process" detail="OS PID provided by the application" badge="Process ID 4211" tone="mint" /><EvidenceItem icon={<Network size={15} />} title="Socket mapping" detail="Local connection mapped to owner process" badge="Port 51,842" tone="blue" /><EvidenceItem icon={<Database size={15} />} title="Application transaction" detail="Passed explicitly to query tracking" badge="TX-208" tone="lavender" /></div></section><section className="surface-panel narrow-panel"><div className="panel-heading"><div><h3>Identity rules</h3><p>Evidence, not assumptions</p></div></div><RuleRow n="01" title="PID belongs to the OS" detail="The application supplies its process ID." /><RuleRow n="02" title="Transaction ID belongs to the app" detail="It links query and lock requests." /><RuleRow n="03" title="DBMS IDs stay separate" detail="Thread IDs are not interpreted as PIDs." /><RuleRow n="04" title="Time orders events" detail="A timestamp alone cannot prove identity." /></section></div>;
  if (tab === 'Trace library') return <TraceLibrary />;
  if (tab === 'Manual correlation') return <div className="content-two-col"><section className="surface-panel"><div className="panel-heading"><div><h3>Link OS and DBMS evidence</h3><p>Review identifiers and source records before creating a manual relationship</p></div><span className="demo-pill">Preview</span></div><label className="field-label">OS event<select defaultValue="OS-1938, process_created, Process ID 4211"><option>OS-1938, process_created, Process ID 4211</option><option>OS-1934, resource_usage, Process ID 4211</option><option>FS-0231, file_modified, Process ID unavailable</option></select></label><label className="field-label">DBMS query<select defaultValue="OBS-8842, UPDATE inventory"><option>OBS-8842, UPDATE inventory</option><option>OBS-8841, SELECT inventory</option></select></label><label className="field-label">Relationship<select defaultValue="Process / transaction match"><option>Process / transaction match</option><option>Temporal and resource match</option><option>Filesystem path match</option></select></label><button type="button" className="button button-primary" onClick={() => onAction('Manual correlation preview ready. No record was written.')}>Review correlation <ArrowRight size={14} /></button><div className="match-result"><div className="match-result-top"><span className="incident-icon info"><GitBranch size={15} /></span><div><strong>Evidence can be reviewed</strong><small>PID agrees, query belongs to TX-208, sample timestamps ordered</small></div></div></div></section><section className="surface-panel narrow-panel"><div className="panel-heading"><div><h3>Before linking</h3><p>Confirm the relationship evidence</p></div></div><RuleRow n="1" title="Check source identifiers" detail="PID and app transaction ID must agree when present." /><RuleRow n="2" title="Review event order" detail="Timestamps establish sequence, not identity." /><RuleRow n="3" title="Keep gaps visible" detail="A filesystem event may have no PID." /></section></div>;
  return <div className="content-two-col"><section className="surface-panel"><div className="panel-heading"><div><h3>Match a DBMS observation</h3><p>Candidate matching uses query identity and a bounded time window</p></div><span className="demo-pill">Local example</span></div><div className="correlation-form"><label className="field-label">DBMS observation<select defaultValue="OBS-8842"><option>OBS-8842, UPDATE inventory</option><option>OBS-8841, SELECT inventory</option></select></label><label className="field-label">Time window<select defaultValue="5 minutes"><option>5 minutes</option><option>2 minutes</option><option>10 minutes</option></select></label><label className="field-label">OS process<select defaultValue="Process ID 4211, checkout-api"><option>Process ID 4211, checkout-api</option><option>Process ID 3980, catalog-worker</option><option>Any candidate</option></select></label><button type="button" className="button button-primary" onClick={() => onAction('Preview result: one unique candidate; sample evidence only.')}><GitBranch size={15} /> Preview correlation</button></div><div className="match-result"><div className="match-result-top"><span className="result-check"><Check size={15} /></span><div><strong>One candidate found</strong><small>Preview only, no trace was written</small></div><span className="event-tag tag-mint">Unique match</span></div><div className="match-evidence"><span>Exact query type and text</span><b>Match</b><span>Timestamp within selected window</span><b>3.2 sec</b><span>OS event PID agrees</span><b>4211</b></div></div></section><section className="surface-panel narrow-panel"><div className="panel-heading"><div><h3>Possible outcomes</h3><p>Transparent matching behavior</p></div></div><RuleRow n="✓" title="Unique candidate" detail="Show the evidence and create a trace." /><RuleRow n="0" title="No candidate" detail="Explain which condition failed." /><RuleRow n="2+" title="Ambiguous match" detail="Reject the match; ask for stronger identity evidence." /></section></div>;
}

function TraceLibrary() {
  type Trace = {trace_id: number; pid?: number | null; transaction_id?: number | null; status: string; started_at: string; ended_at?: string | null; summary?: string | null; event_count: number; methods?: string | null};
  const [traces, setTraces] = useState<Trace[]>([]);
  const [error, setError] = useState('');
  const refresh = () => getJson<Trace[]>('/correlations/traces?limit=100').then((items) => { setTraces(items); setError(''); }).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Unable to load persisted traces.'));
  useEffect(() => { void refresh(); }, []);
  return <><section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Cross-layer trace library</h3><p>Persisted correlations from the backend</p></div><button type="button" className="button button-secondary" onClick={() => void refresh()}><ListFilter size={15} /> Refresh</button></div>{error ? <div className="empty-state">{error}</div> : traces.length ? <div className="table-wrap"><table><thead><tr><th>Trace</th><th>Process ID</th><th>Transaction</th><th>Events</th><th>Method</th><th>State</th><th>Started</th></tr></thead><tbody>{traces.map((trace) => <tr key={trace.trace_id}><td><b>TR-{trace.trace_id}</b></td><td>{trace.pid ?? '—'}</td><td>{trace.transaction_id ? `TX-${trace.transaction_id}` : '—'}</td><td>{trace.event_count}</td><td>{trace.methods ?? '—'}</td><td><span className="state-label state-linked">{trace.status}</span></td><td>{new Date(trace.started_at).toLocaleString()}</td></tr>)}</tbody></table></div> : <div className="empty-state">No persisted traces yet. Run automatic correlation after collecting matching OS and DBMS evidence.</div>}</section><div className="note-banner"><GitBranch size={16} /><span>Only persisted traces appear here. Ambiguous and unmatched evidence is not recorded as a confirmed relationship.</span></div></>;
}

function LiveCorrelation({ onAction }: { onAction: (message: string) => void }) {
  const [observations, setObservations] = useState<Array<{observation_id?: number; query_type: string; query_text: string; observed_at: string; source_thread_id: number}>>([]);
  const [observationId, setObservationId] = useState('');
  const [bridge, setBridge] = useState<{active_bridges?: number; warning?: string | null} | null>(null);
  const [result, setResult] = useState<{matched_query_id?: number | null; matched_os_event_ids?: number[]; reason?: string | null; result?: {classification?: string; evidence_summary?: string | null; trace?: {trace_id?: number | null}} | null} | null>(null);
  const [error, setError] = useState('');
  const refresh = () => Promise.all([
    observabilityApi.dbmsObservations<(typeof observations)[number]>(),
    getJson<typeof bridge>('/bridge/live-map'),
  ]).then(([items, map]) => { setObservations(items); setBridge(map); setObservationId((current) => current || String(items.find((item) => item.observation_id)?.observation_id ?? '')); setError(''); })
    .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Unable to load correlation evidence.'));
  useEffect(() => { void refresh(); }, []);
  const correlate = async () => {
    const id = Number(observationId);
    if (!Number.isInteger(id) || id < 1) { onAction('Choose a persisted DBMS observation first.'); return; }
    try { const response = await correlationApi.correlateAutomatically<NonNullable<typeof result>>({observation_id: id, window_ms: 5000, persist: true}); setResult(response); }
    catch (cause) { onAction(cause instanceof Error ? cause.message : 'Automatic correlation failed.'); }
  };
  return <div className="content-two-col"><section className="surface-panel"><div className="panel-heading"><div><h3>Correlate live evidence</h3><p>Match a persisted MySQL observation to OS evidence</p></div><span className="event-tag tag-lavender">Backend analysis</span></div>{error ? <div className="empty-state">{error}</div> : <><label className="field-label">DBMS observation<select value={observationId} onChange={(event) => setObservationId(event.target.value)}><option value="">Choose an observation</option>{observations.filter((item) => item.observation_id).map((item) => <option key={item.observation_id} value={item.observation_id}>#{item.observation_id} · {item.query_type} · {item.query_text.slice(0, 60)}</option>)}</select></label><p className="muted-copy">Identity bridge: {bridge ? `${bridge.active_bridges ?? 0} active PID-to-connection mappings` : 'Loading'}{bridge?.warning ? ` · ${bridge.warning}` : ''}</p><button type="button" className="button button-primary" onClick={() => void correlate()} disabled={!observationId}><GitBranch size={15} /> Run automatic correlation</button>{result && <div className="match-result"><div className="match-result-top"><span className="incident-icon info"><GitBranch size={15} /></span><div><strong>{result.result?.classification ?? 'No confirmed match'}</strong><small>{result.reason ?? result.result?.evidence_summary ?? 'No relationship was established.'}</small></div></div><div className="match-evidence"><span>Matched query</span><b>{result.matched_query_id ?? 'None'}</b><span>OS events</span><b>{result.matched_os_event_ids?.join(', ') || 'None'}</b><span>Trace</span><b>{result.result?.trace?.trace_id ?? 'Not created'}</b></div></div>}</>}</section><section className="surface-panel narrow-panel"><div className="panel-heading"><div><h3>Identity bridge</h3><p>Live mapping status</p></div></div><div className="stat-inline"><div><span>Active mappings</span><strong>{bridge?.active_bridges ?? '—'}</strong></div><div><span>Permission state</span><strong>{bridge ? 'Connected' : 'Loading'}</strong></div></div><RuleRow n="1" title="OS PID" detail="Read from the local host socket owner when privileges allow." /><RuleRow n="2" title="MySQL connection" detail="A DBMS connection ID is kept distinct from the process ID." /><RuleRow n="3" title="Correlation" detail="Unmatched and ambiguous candidates remain unlinked." /></section></div>;
}

function TransactionsLocks() {
  type Transaction = {transaction_id: number; pid: number; status: string; isolation_level: string; start_time: string; end_time?: string | null; operation_count: number};
  type Lock = {lock_id: number; transaction_id: number; data_item: string; lock_type: string; status: string; acquired_at?: string | null};
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [locks, setLocks] = useState<Lock[]>([]);
  const [error, setError] = useState('');
  const refresh = () => Promise.all([workflowsApi.transactions<Transaction>(), workflowsApi.locks<Lock>()])
    .then(([tx, lockRows]) => { setTransactions(tx); setLocks(lockRows); setError(''); })
    .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Unable to load transaction data.'));
  useEffect(() => { void refresh(); const timer = window.setInterval(() => void refresh(), 10000); return () => window.clearInterval(timer); }, []);
  const activeCount = transactions.filter((tx) => tx.status === 'ACTIVE').length;
  const waiting = locks.filter((lock) => lock.status === 'WAITING');
  return <><div className="stat-inline"><div><span>Active transactions</span><strong>{activeCount}</strong></div><div><span>Waiting locks</span><strong>{waiting.length}</strong></div><div><span>Active locks</span><strong>{locks.filter((lock) => ['HELD', 'WAITING'].includes(lock.status)).length}</strong></div><div className="inline-status"><span>{error ? 'API unavailable' : 'Live database records'}</span></div></div>{error && <div className="empty-state">{error}</div>}<div className="content-two-col"><section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Transaction activity</h3><p>Lifecycle, process identity, and operation counts</p></div><button type="button" className="button button-secondary" onClick={() => void refresh()}>Refresh</button></div>{transactions.length ? <div className="table-wrap"><table><thead><tr><th>Transaction</th><th>Process ID</th><th>Status</th><th>Started</th><th>Operations</th></tr></thead><tbody>{transactions.map((tx) => <tr key={tx.transaction_id}><td>#{tx.transaction_id}</td><td>{tx.pid}</td><td>{tx.status}</td><td>{new Date(tx.start_time).toLocaleString()}</td><td>{tx.operation_count}</td></tr>)}</tbody></table></div> : !error && <div className="empty-state">No transactions have been recorded.</div>}</section><section className="surface-panel lock-panel"><div className="panel-heading"><div><h3>Lock waits and ownership</h3><p>Stored lock records</p></div></div>{locks.length ? locks.slice(0, 12).map((lock) => <div className="lock-edge" key={lock.lock_id}><span className={`lock-node ${lock.status === 'WAITING' ? 'waiting' : 'held'}`}>TX-{lock.transaction_id}<small>{lock.status} · {lock.lock_type}</small></span><ArrowRight size={18} /><span className="lock-resource">{lock.data_item}</span></div>) : !error && <div className="empty-state">No locks have been recorded.</div>}</section></div></>;
}

function RuleRow({ n, title, detail }: { n: string; title: string; detail: string }) { return <div className="rule-row"><span>{n}</span><div><strong>{title}</strong><small>{detail}</small></div></div>; }

function Incidents({ tab, onAction }: { tab: string; onAction: (message: string) => void }) {
  if (tab === 'Investigation' || tab === 'Blast radius' || tab === 'Replay') return <LiveIncidentDetail tab={tab} onAction={onAction} />;
  const [incidents, setIncidents] = useState<Array<{incident_id: number; trace_id?: number | null; incident_type: string; description?: string | null; detected_at?: string | null; resolved?: boolean | null}>>([]);
  const [incidentError, setIncidentError] = useState('');
  const refreshIncidents = () => incidentsApi.list<(typeof incidents)[number]>()
    .then((items) => { setIncidents(items); setIncidentError(''); })
    .catch((cause: unknown) => setIncidentError(cause instanceof Error ? cause.message : 'Unable to load incidents.'));
  useEffect(() => { void refreshIncidents(); }, []);
  const detectLiveDeadlock = async () => {
    try { const result = await workflowsApi.detectLiveDeadlock<{deadlock_detected: boolean; incident_id?: number | null}>(); onAction(result.deadlock_detected ? `Deadlock detected and recorded as incident ${result.incident_id ?? 'unknown'}.` : 'No deadlock was detected in the current lock snapshot.'); await refreshIncidents(); }
    catch (cause) { onAction(cause instanceof Error ? cause.message : 'Deadlock scan failed.'); }
  };
  if (tab === 'Investigation') return <div className="investigation-layout"><section className="surface-panel investigation-main"><div className="investigation-title"><span className="incident-icon warn"><LockKeyhole size={17} /></span><div><span className="event-tag">Incident, deadlock</span><h2>Inventory update contention</h2><p>INC-018, Detected 10:41:42 UTC, Status: Open</p></div><span className="severity severity-high">High</span></div><div className="timeline-title"><h3>Evidence timeline</h3><span>Sample trace, TR-042</span></div><div className="investigation-timeline">{[
      ['10:41:40.012', 'Transaction began', 'TX-208, checkout-api, Process ID 4211', 'db'],
      ['10:41:41.772', 'Lock wait observed', 'Waiting on inventory:sku:104', 'warn'],
      ['10:41:42.104', 'Deadlock cycle detected', 'TX-208 ↔ TX-211, wait-for graph contains a cycle', 'alert'],
      ['10:41:42.318', 'Transaction rolled back', 'TX-211 selected as victim, sample outcome', 'done'],
    ].map(([time, title, detail, tone]) => <div className={`timeline-row timeline-${tone}`} key={time}><time>{time}</time><span className="timeline-marker" /><div><strong>{title}</strong><small>{detail}</small></div></div>)}</div><div className="note-banner"><FileClock size={16} /><span>This is a reconstructed sample timeline. Replay displays evidence and does not execute captured SQL.</span></div></section><aside className="surface-panel evidence-panel"><div className="panel-heading"><div><h3>Incident context</h3><p>Records attached to this sample</p></div></div><EvidenceItem icon={<GitBranch size={15} />} title="Cross-layer trace" detail="8 sample events" badge="TR-042" tone="blue" /><EvidenceItem icon={<Database size={15} />} title="Transaction" detail="Rolled back" badge="TX-208" tone="lavender" /><EvidenceItem icon={<LockKeyhole size={15} />} title="Lock resource" detail="Inventory row, sku 104" badge="Waiting" tone="peach" /><button type="button" className="button button-secondary full-button" onClick={() => onAction('Replay preview opened for sample incident INC-018.')}>Open replay <ArrowRight size={14} /></button></aside></div>;
  if (tab === 'Blast radius') return <><section className="surface-panel"><div className="panel-heading"><div><h3>Deadlock impact map</h3><p>Direct and potential impact from the sample wait-for graph</p></div><span className="severity severity-high">High severity</span></div><div className="impact-graph"><div className="impact-node impacted"><span>TX-208</span><small>checkout-api</small><b>Direct impact</b></div><div className="impact-arrow"><ArrowRight size={18} /><span>holds row lock</span></div><div className="impact-node impacted"><span>TX-211</span><small>order-worker</small><b>Direct impact</b></div><div className="impact-loop"><ArrowDownRight size={18} /><span>wait cycle detected</span></div><div className="impact-node potential"><span>TX-214</span><small>inventory-sync</small><b>Potential impact</b></div></div><div className="impact-legend"><span><i className="legend-direct" /> Directly involved</span><span><i className="legend-potential" /> Potentially affected</span></div></section><div className="note-banner"><ShieldAlert size={16} /><span>Impact categories describe the supplied wait graph; they are not a prediction of workload outside this sample.</span></div></>;
  if (tab === 'Fingerprints') return <section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Structural incident fingerprints</h3><p>Similar lock-cycle shapes grouped across sample incidents</p></div><button type="button" className="button button-secondary"><ListFilter size={15} /> Group by shape</button></div><div className="fingerprint-card"><div className="fingerprint-visual"><span>Tx-A</span><span className="fingerprint-arrows">↔</span><span>Tx-B</span></div><div><span className="event-tag">Deadlock, 3 matches</span><strong>DEADLOCK-TX2, two-transaction cycle</strong><small>Same graph structure, different transaction IDs and event times</small></div><button type="button" className="button button-quiet" onClick={() => onAction('Showing three illustrative incidents with this graph shape.')}>View matches <ArrowRight size={14} /></button></div><div className="fingerprint-card"><div className="fingerprint-visual fingerprint-three"><span>Tx-A</span><span>Tx-B</span><span>Tx-C</span></div><div><span className="event-tag">Deadlock, 1 match</span><strong>DEADLOCK-TX3, three-transaction cycle</strong><small>Structural hash groups this cycle shape</small></div><button type="button" className="button button-quiet" onClick={() => onAction('Showing one illustrative incident with this graph shape.')}>View matches <ArrowRight size={14} /></button></div></section>;
  if (tab === 'Replay') return <section className="surface-panel replay-panel"><div className="panel-heading"><div><h3>Forensic replay, INC-018</h3><p>Deterministic playback of the investigation evidence</p></div><span className="event-tag tag-lavender">Read only</span></div><div className="replay-banner"><div className="replay-play"><Play size={17} fill="currentColor" /></div><div><strong>Replay does not re-run SQL</strong><p>It reconstructs the recorded timeline from linked evidence.</p></div><button type="button" className="button button-primary" onClick={() => onAction('Replay started for local sample data.')}>Play timeline <Play size={14} fill="currentColor" /></button></div><div className="replay-track">{['OS process', 'Transaction', 'Lock wait', 'Deadlock', 'Rollback'].map((label, index) => <div className="replay-step" key={label}><span className={index < 3 ? 'played' : ''}>{index + 1}</span><small>{label}</small></div>)}</div><EventList events={events.slice(0, 4)} /></section>;
  return <><div className="stat-inline"><div><span>Recorded incidents</span><strong>{incidents.length}</strong></div><div><span>Unresolved</span><strong>{incidents.filter((incident) => incident.resolved !== true).length}</strong></div><div className="inline-status"><span>{incidentError ? 'API unavailable' : 'Live API records'}</span></div></div><section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Incident queue</h3><p>Persisted deadlock incidents</p></div><button type="button" className="button button-secondary" onClick={() => void detectLiveDeadlock()}>Scan live locks</button></div>{incidentError ? <div className="empty-state">{incidentError}</div> : incidents.length ? <div className="table-wrap"><table><thead><tr><th>Incident</th><th>Type</th><th>Description</th><th>Detected</th><th>Trace</th><th>Status</th></tr></thead><tbody>{incidents.map((incident) => <tr key={incident.incident_id}><td><b>#{incident.incident_id}</b></td><td>{incident.incident_type}</td><td>{incident.description ?? '—'}</td><td>{incident.detected_at ? new Date(incident.detected_at).toLocaleString() : '—'}</td><td>{incident.trace_id ?? 'No trace'}</td><td>{incident.resolved ? 'Resolved' : 'Open'}</td></tr>)}</tbody></table></div> : <div className="empty-state">No incidents have been recorded.</div>}</section></>;
}

function LiveIncidentDetail({ tab, onAction }: { tab: string; onAction: (message: string) => void }) {
  type Incident = {incident_id: number; incident_type: string; description?: string | null; detected_at?: string | null; trace_id?: number | null};
  type TimelineItem = {sequence: number; source: string; timestamp?: string | null; event_type: string; description: string};
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [incidentId, setIncidentId] = useState('');
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [resources, setResources] = useState<Array<{resource_type: string; resource_id: string; impact_level: string; evidence: {rule_applied: string; relationship: string}}>>([]);
  const [replay, setReplay] = useState<{outcome: string; summary: string; steps: TimelineItem[]} | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { void incidentsApi.list<Incident>().then((items) => { setIncidents(items); setIncidentId(String(items[0]?.incident_id ?? '')); }).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Unable to load incidents.')); }, []);
  useEffect(() => {
    const id = Number(incidentId);
    if (!id) return;
    setError(''); setTimeline([]); setResources([]); setReplay(null);
    if (tab === 'Investigation') void incidentsApi.investigation<{timeline: TimelineItem[]}>(id).then((result) => setTimeline(result.timeline)).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Investigation unavailable.'));
    if (tab === 'Blast radius') void incidentsApi.blastRadius<{affected_resources: typeof resources}>(id).then((result) => setResources(result.affected_resources)).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Blast radius unavailable.'));
  }, [incidentId, tab]);
  const selected = incidents.find((item) => item.incident_id === Number(incidentId));
  const runReplay = async () => {
    try { const result = await incidentsApi.replay<{outcome: string; summary: string; steps: TimelineItem[]}>(Number(incidentId)); setReplay(result); onAction('Replay record saved from the incident evidence. Captured SQL was not executed.'); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Replay is unavailable for this incident.'); }
  };
  return <section className="surface-panel"><div className="panel-heading"><div><h3>{tab}</h3><p>Evidence loaded from the incident API</p></div><label className="field-label">Incident<select value={incidentId} onChange={(event) => setIncidentId(event.target.value)}><option value="">Choose incident</option>{incidents.map((item) => <option key={item.incident_id} value={item.incident_id}>#{item.incident_id} · {item.incident_type}</option>)}</select></label></div>{error && <div className="empty-state">{error}</div>}{selected && <p>{selected.description ?? selected.incident_type} · {selected.detected_at ? new Date(selected.detected_at).toLocaleString() : 'Time unavailable'} · Trace {selected.trace_id ?? 'not linked'}</p>}{tab === 'Replay' && <><p>Replay rebuilds recorded evidence; it does not execute captured SQL.</p><button type="button" className="button button-primary" disabled={!incidentId} onClick={() => void runReplay()}>Create evidence replay</button>{replay && <div className="note-banner"><strong>{replay.outcome}</strong><span>{replay.summary}</span></div>}</>}{tab === 'Blast radius' && (resources.length ? resources.map((resource) => <div className="rule-row" key={`${resource.resource_type}-${resource.resource_id}`}><span>{resource.impact_level}</span><div><strong>{resource.resource_type} {resource.resource_id}</strong><small>{resource.evidence.relationship} · {resource.evidence.rule_applied}</small></div></div>) : !error && <div className="empty-state">No affected resources are linked to this incident.</div>)}{tab === 'Investigation' && (timeline.length ? <div className="investigation-timeline">{timeline.map((item) => <div className="timeline-row" key={item.sequence}><time>{item.timestamp ? new Date(item.timestamp).toLocaleString() : '—'}</time><span className="timeline-marker" /><div><strong>{item.source} · {item.event_type}</strong><small>{item.description}</small></div></div>)}</div> : !error && <div className="empty-state">No investigation timeline evidence is linked.</div>)}</section>;
}

function Performance({ tab, onAction }: { tab: string; onAction: (message: string) => void }) {
  const [scenario, setScenario] = useState('LOCK_CONTENTION');
  const [benchmarkResult, setBenchmarkResult] = useState<Record<string, unknown> | null>(null);
  const runBenchmark = async () => {
    try { const result = await analysisApi.runBenchmark<Record<string, unknown>>({scenario, operations: 50, concurrency: 4, description: 'OS-DBX frontend benchmark'}); setBenchmarkResult(result); onAction('Backend benchmark completed.'); }
    catch (cause) { onAction(cause instanceof Error ? cause.message : 'Benchmark failed.'); }
  };
  if (tab === 'System health') return <LiveSystemHealth />;
  if (tab === 'Performance records') return <LivePerformanceRecords />;
  if (tab === 'Benchmarks') return <><section className="surface-panel benchmark-form"><div className="panel-heading"><div><h3>Run a controlled workload</h3><p>This action runs the selected backend benchmark against its configured database.</p></div><span className="demo-pill">Backend run</span></div><div className="benchmark-options">{['DBMS_ONLY', 'LOCK_CONTENTION', 'DEADLOCK'].map((item) => <button type="button" key={item} className={`benchmark-option ${scenario === item ? 'chosen' : ''}`} onClick={() => setScenario(item)}><span className="radio-dot" /><strong>{item.replace(/_/g, ' ')}</strong><small>{item === 'DBMS_ONLY' ? 'Query throughput without OS contention' : item === 'LOCK_CONTENTION' ? 'Concurrent transactions competing for rows' : 'Create a wait-for cycle to inspect'}</small></button>)}</div><div className="benchmark-controls"><button type="button" className="button button-primary" onClick={() => void runBenchmark()}><Play size={14} fill="currentColor" /> Run benchmark</button></div></section>{benchmarkResult && <section className="surface-panel"><div className="panel-heading"><div><h3>Backend benchmark result</h3><p>Measured by the API</p></div></div><pre className="result-json">{JSON.stringify(benchmarkResult, null, 2)}</pre></section>}</>;

  return <><div className="health-banner"><span className="health-symbol"><Activity size={19} /></span><div><strong>System health, sample snapshot</strong><small>10:42 UTC, Demo environment</small></div><span className="event-tag tag-lavender">Illustrative</span></div><div className="performance-grid"><section className="surface-panel chart-panel"><div className="panel-heading"><div><h3>System resource use</h3><p>Last 15 minutes, sample series</p></div><span className="chart-unit">Percent</span></div><MiniChart /></section><section className="surface-panel chart-panel"><div className="panel-heading"><div><h3>Query latency</h3><p>Average duration, sample series</p></div><span className="chart-unit">Milliseconds</span></div><MiniChart alternate /></section></div><div className="stat-inline"><div><span>OS capture overhead</span><strong>1.8% cpu</strong></div><div><span>Collector memory</span><strong>42 MB</strong></div><div><span>Correlation latency</span><strong>6.4 ms</strong></div><div><span>Dropped events</span><strong>0 <small>sample</small></strong></div><div className="inline-status"><span>Values are illustrative</span></div></div><button type="button" className="button button-secondary" onClick={() => onAction('Health refreshed from local sample data.')}>Refresh sample</button></>;
}

function LiveSystemHealth() {
  const [snapshot, setSnapshot] = useState<{timestamp?: string; system?: {cpu_percent?: number; memory_percent?: number; process_count?: number; disk_io_mbs?: number; dropped_events?: number}; dbms?: {status?: string; query_throughput_per_sec?: number; avg_query_latency_ms?: number; active_connections?: number}; overhead?: {agent_cpu_percent?: number; agent_memory_mb?: number}} | null>(null);
  const [error, setError] = useState('');
  const refresh = () => analysisApi.systemHealth<typeof snapshot>()
    .then((result) => { setSnapshot(result); setError(''); })
    .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Unable to load health data.'));
  useEffect(() => { void refresh(); const timer = window.setInterval(() => void refresh(), 15000); return () => window.clearInterval(timer); }, []);
  return <><div className="health-banner"><span className="health-symbol"><Activity size={19} /></span><div><strong>System health, live API snapshot</strong><small>{snapshot?.timestamp ? new Date(snapshot.timestamp).toLocaleString() : 'Waiting for backend'}</small></div><span className="event-tag tag-lavender">{snapshot?.dbms?.status ?? (error ? 'Unavailable' : 'Loading')}</span></div>{error && <div className="empty-state">{error}</div>}<div className="stat-inline"><div><span>CPU usage</span><strong>{snapshot?.system?.cpu_percent ?? '—'}%</strong></div><div><span>Memory use</span><strong>{snapshot?.system?.memory_percent ?? '—'}%</strong></div><div><span>Processes</span><strong>{snapshot?.system?.process_count ?? '—'}</strong></div><div><span>Disk throughput</span><strong>{snapshot?.system?.disk_io_mbs ?? '—'} MB/s</strong></div></div><div className="stat-inline"><div><span>DBMS queries/sec</span><strong>{snapshot?.dbms?.query_throughput_per_sec ?? '—'}</strong></div><div><span>Average query latency</span><strong>{snapshot?.dbms?.avg_query_latency_ms ?? '—'} ms</strong></div><div><span>Active connections</span><strong>{snapshot?.dbms?.active_connections ?? '—'}</strong></div><div><span>Dropped events</span><strong>{snapshot?.system?.dropped_events ?? '—'}</strong></div><div><span>Collector memory</span><strong>{snapshot?.overhead?.agent_memory_mb ?? '—'} MB</strong></div></div><button type="button" className="button button-secondary" onClick={() => void refresh()}>Refresh live health</button></>;
}

function LivePerformanceRecords() {
  const [records, setRecords] = useState<Array<{record_id: number; metric_name: string; metric_value: number; data_source: string; recorded_at: string; trace_id?: number | null}>>([]);
  const [error, setError] = useState('');
  const refresh = () => analysisApi.performanceRecords<(typeof records)[number]>()
    .then((items) => { setRecords(items); setError(''); })
    .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Unable to load performance records.'));
  useEffect(() => { void refresh(); }, []);
  return <section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Performance records</h3><p>Persisted measurements from the authenticated API</p></div><button type="button" className="button button-secondary" onClick={() => void refresh()}>Refresh</button></div>{error ? <div className="empty-state">{error}</div> : records.length ? <div className="table-wrap"><table><thead><tr><th>Metric</th><th>Value</th><th>Source</th><th>Recorded</th><th>Trace</th></tr></thead><tbody>{records.map((record) => <tr key={record.record_id}><td>{record.metric_name}</td><td>{record.metric_value}</td><td>{record.data_source}</td><td>{new Date(record.recorded_at).toLocaleString()}</td><td>{record.trace_id ?? '—'}</td></tr>)}</tbody></table></div> : <div className="empty-state">No performance records are available.</div>}</section>;
}

function MiniChart({ alternate = false }: { alternate?: boolean }) {
  const values = alternate ? [30, 38, 34, 47, 43, 60, 52, 58, 50, 68, 62, 73, 56, 65, 57, 78, 64, 68, 61, 74] : [45, 42, 50, 47, 55, 49, 52, 61, 56, 50, 60, 55, 65, 59, 53, 57, 49, 55, 48, 60];
  return <div className={`mini-chart ${alternate ? 'chart-alt' : ''}`} role="img" aria-label={alternate ? 'Illustrative query latency chart' : 'Illustrative CPU and memory chart'}><div className="chart-grid"><span>80</span><span>60</span><span>40</span><span>20</span><span>0</span></div><div className="chart-lines"><div className="gridline" /><div className="gridline" /><div className="gridline" /><div className="gridline" /><svg viewBox="0 0 600 170" preserveAspectRatio="none" aria-hidden="true"><path d={`M 0 ${170 - values[0] * 1.7} ${values.map((value, index) => `L ${index * 31.5} ${170 - value * 1.7}`).join(' ')}`} className="chart-path" /><path d={`M 0 ${170 - (alternate ? 36 : 35) * 1.7} ${values.map((value, index) => `L ${index * 31.5} ${170 - Math.max(20, value - (alternate ? 18 : 12)) * 1.7}`).join(' ')}`} className="chart-path chart-path-secondary" /></svg><span className="chart-onset">10:38</span></div><div className="chart-legend"><span><i className="legend-os" />{alternate ? 'P95 latency' : 'cpu use'}</span><span><i className="legend-db" />{alternate ? 'Average' : 'Memory use'}</span></div></div>;
}

function Simulations({ tab, selectedAlgorithm, onAlgorithm, onAction }: { tab: string; selectedAlgorithm: string; onAlgorithm: (value: string) => void; onAction: (message: string) => void }) {
  const options = tab === 'OS simulations' ? ['CPU Scheduling', 'Memory & page replacement', 'Deadlock theory'] : ['Serializability', 'WAL recovery', 'Strict 2PL'];
  const [lab, setLab] = useState(options[0]);
  const [apiResult, setApiResult] = useState<unknown>(null);
  const [apiError, setApiError] = useState('');
  const [input, setInput] = useState('');
  const [quantum, setQuantum] = useState('2');
  const activeAlgorithms = labAlgorithms(tab, lab);
  const activeAlgorithm = activeAlgorithms.includes(selectedAlgorithm) ? selectedAlgorithm : activeAlgorithms[0];
  const inputDefault = (selectedLab: string) => selectedLab.toLowerCase().includes('scheduling')
    ? 'P1: arrival 0, burst 6\nP2: arrival 1, burst 3\nP3: arrival 2, burst 5'
    : selectedLab.toLowerCase().includes('memory') ? '7, 0, 1, 2, 0, 3, 0, 4'
      : selectedLab.toLowerCase().includes('serial') ? 'R1(A), W1(A), R2(A), W2(A)'
        : selectedLab.toLowerCase().includes('wal') ? 'BEGIN T1, UPDATE T1 A 0 1, COMMIT T1'
          : 'Example is provided by the backend';
  useEffect(() => { setInput(inputDefault(lab)); setApiResult(null); setApiError(''); }, [lab]);
  const runApiSimulation = async () => {
    try {
      let result: unknown;
      if (lab.toLowerCase().includes('scheduling')) {
        const algorithm = activeAlgorithm === 'Round Robin' ? 'RR' : activeAlgorithm.toUpperCase();
        const processes = input.split(/\n|;/).map((line) => line.match(/P?(\d+)\s*:\s*arrival\s*(\d+)\s*,\s*burst\s*(\d+)(?:\s*,\s*priority\s*(-?\d+))?/i)).filter((match): match is RegExpMatchArray => Boolean(match)).map((match) => ({pid: Number(match[1]), arrival_time: Number(match[2]), burst_time: Number(match[3]), priority: Number(match[4] ?? 0)}));
        if (!processes.length) throw new Error('Enter one process per line, for example: P1: arrival 0, burst 6.');
        result = await simulationsApi.schedule({algorithm, quantum: Number(quantum), processes});
      } else if (lab.toLowerCase().includes('memory')) {
        const values = input.split(/[\s,]+/).filter(Boolean).map(Number);
        if (!values.length || values.some((value) => !Number.isInteger(value) || value < 0)) throw new Error('Enter a comma-separated list of non-negative page numbers.');
        result = await simulationsApi.memory({algorithm: activeAlgorithm.toUpperCase(), num_frames: 3, reference_string: values});
      } else if (lab.toLowerCase().includes('deadlock')) {
        result = activeAlgorithm.toLowerCase().includes('graph')
          ? await simulationsApi.resourceGraphDeadlock({processes: [1, 2], resources: [1, 2], allocation: {1: [1], 2: [2]}, request: {1: [2], 2: [1]}})
          : await simulationsApi.bankerDeadlock({allocation: [[1, 0], [0, 1]], max_need: [[2, 1], [1, 2]], available: [1, 1]});
      } else if (lab.toLowerCase().includes('serial')) {
        const operations = [...input.matchAll(/([RW])\s*(\d+)\s*\(([^)]+)\)/gi)].map((match) => ({transaction_id: Number(match[2]), operation: match[1].toUpperCase(), data_item: match[3].trim()}));
        if (!operations.length) throw new Error('Enter operations like R1(A), W1(A), R2(A).');
        result = await workflowsApi.analyzeSchedule({operations});
      } else if (lab.toLowerCase().includes('wal')) {
        const logs = input.split(',').map((part) => part.trim()).filter(Boolean).map((part, index) => {
          const begin = part.match(/^BEGIN\s+T?(\d+)$/i); const update = part.match(/^UPDATE\s+T?(\d+)\s+([\w]+)\s+([^\s]+)\s+([^\s]+)$/i); const commit = part.match(/^COMMIT\s+T?(\d+)$/i);
          if (begin) return {sequence: index + 1, transaction_id: Number(begin[1]), log_type: 'BEGIN'};
          if (update) return {sequence: index + 1, transaction_id: Number(update[1]), log_type: 'UPDATE', data_item: update[2], old_value: update[3], new_value: update[4]};
          if (commit) return {sequence: index + 1, transaction_id: Number(commit[1]), log_type: 'COMMIT'};
          throw new Error(`Could not parse log entry: ${part}`);
        });
        if (!logs.length) throw new Error('Add WAL entries such as BEGIN T1, UPDATE T1 A 0 1, COMMIT T1.');
        result = await workflowsApi.recover({initial_state: {}, logs});
      } else {
        throw new Error('Strict 2PL does not have a matching backend simulation endpoint yet.');
      }
      setApiResult(result); setApiError(''); onAction('Simulation completed by the backend API.');
    } catch (cause) { setApiError(cause instanceof Error ? cause.message : 'Simulation API call failed.'); }
  };
  return <><div className="lab-picker">{options.map((option) => <button type="button" key={option} className={`lab-option ${lab === option ? 'selected' : ''}`} onClick={() => { setLab(option); onAlgorithm(labAlgorithms(tab, option)[0]); }}>{option}<ChevronRight size={14} /></button>)}</div><div className="content-two-col simulation-grid"><section className="surface-panel simulation-input"><div className="panel-heading"><div><h3>{lab}</h3><p>{lab.includes('Strict 2PL') ? 'This backend endpoint is not implemented yet.' : 'Edit the input, then run the matching backend simulation.'}</p></div><span className="event-tag tag-lavender">Simulation</span></div>{!lab.includes('Strict 2PL') && <><label className="field-label">Algorithm<select value={activeAlgorithm} onChange={(event) => onAlgorithm(event.target.value)}>{activeAlgorithms.map((algorithm) => <option key={algorithm}>{algorithm}</option>)}</select></label>{lab.toLowerCase().includes('scheduling') && <label className="field-label">Time quantum<input type="number" min="1" value={quantum} onChange={(event) => setQuantum(event.target.value)} /></label>}<label className="field-label">{lab.toLowerCase().includes('scheduling') ? 'Processes (one per line)' : lab.toLowerCase().includes('serial') ? 'Schedule' : lab.toLowerCase().includes('wal') ? 'WAL entries' : 'Reference string'}<textarea value={input} onChange={(event) => setInput(event.target.value)} rows={4} /></label><button type="button" className="button button-primary" onClick={() => void runApiSimulation()}>Run backend simulation <ArrowRight size={14} /></button></>}{apiError && <div className="empty-state">{apiError}</div>}</section><section className="surface-panel simulation-result"><div className="panel-heading"><div><h3>{apiResult ? 'Backend result' : 'Simulation result'}</h3><p>{apiResult ? 'Returned by the matching backend API' : 'Run a simulation to calculate its result'}</p></div><span className="result-check"><Check size={15} /></span></div>{apiResult ? <pre className="result-json">{JSON.stringify(apiResult, null, 2)}</pre> : <div className="simulation-steps"><RuleRow n="1" title="Selected model" detail={activeAlgorithm} /><RuleRow n="2" title="Result" detail={lab.includes('Strict 2PL') ? 'Not available: there is no matching backend API.' : 'No result has been calculated yet.'} /></div>}</section></div><div className="note-banner"><FlaskConical size={16} /><span>Simulation results are separate from live observations. CPU scheduling, memory, deadlock theory, serializability, and WAL recovery use their corresponding backend APIs. Strict 2PL is currently unavailable.</span></div></>;
}

function labAlgorithms(tab: string, lab: string): string[] {
  if (tab === 'OS simulations') {
    if (lab.toLowerCase().includes('memory')) return ['FIFO', 'LRU', 'Optimal'];
    if (lab.toLowerCase().includes('deadlock')) return ['Banker’s algorithm', 'Resource allocation graph'];
    return ['FCFS', 'SJF', 'SRTF', 'Round Robin', 'Priority'];
  }
  if (lab.toLowerCase().includes('recovery')) return ['WAL / REDO-UNDO', 'Checkpoint recovery'];
  if (lab.toLowerCase().includes('2pl')) return ['Strict 2PL', 'Basic 2PL'];
  return ['Precedence graph', 'Conflict serializability'];
}

function WhatIf({ tab, onAction }: { tab: string; onAction: (message: string) => void }) {
  if (tab === 'Saved scenarios') return <LiveSavedScenarios />;
  return <ConnectedWhatIf tab={tab} onAction={onAction} />;
}

function ConnectedWhatIf({ tab, onAction }: { tab: string; onAction: (message: string) => void }) {
  const isSchedule = tab === 'Schedule analysis';
  const isRecovery = tab === 'Recovery experiment';
  const [name, setName] = useState(isSchedule ? 'Inventory schedule review' : isRecovery ? 'Crash after checkpoint' : 'Checkout CPU workload');
  const [input, setInput] = useState(isSchedule ? 'R1(A), W1(A), R2(A), W2(A), C1, C2' : isRecovery ? 'BEGIN T1, UPDATE A, BEGIN T2, COMMIT T2, CRASH' : 'process_count=12, avg_burst_ms=82, core_count=4');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');
  const analyzeAndSave = async () => {
    try {
      let response: Record<string, unknown>;
      if (isSchedule) {
        const operations = [...input.matchAll(/([RW])\s*(\d+)\s*\(([^)]+)\)/gi)].map((match) => ({operation: match[1].toUpperCase(), transaction_id: Number(match[2]), data_item: match[3].trim()}));
        if (!operations.length) throw new Error('Enter operations like R1(A), W1(A), R2(A).');
        response = await analysisApi.saveScheduleScenario<Record<string, unknown>>({name, operations});
      } else if (isRecovery) {
        const logs = input.split(',').map((part) => part.trim()).filter(Boolean).map((part, index) => {
          const begin = part.match(/^BEGIN\s+T?(\d+)$/i);
          const update = part.match(/^UPDATE\s+([A-Za-z0-9_]+)$/i);
          const commit = part.match(/^COMMIT\s+T?(\d+)$/i);
          const crash = /^CRASH$/i.test(part);
          if (begin) return {sequence: index + 1, transaction_id: Number(begin[1]), log_type: 'BEGIN'};
          if (update) return {sequence: index + 1, transaction_id: 1, log_type: 'UPDATE', data_item: update[1], old_value: '10', new_value: '20'};
          if (commit) return {sequence: index + 1, transaction_id: Number(commit[1]), log_type: 'COMMIT'};
          if (crash) return null;
          throw new Error(`Could not parse recovery step: ${part}`);
        }).filter((entry): entry is NonNullable<typeof entry> => entry !== null);
        response = await analysisApi.saveRecoveryScenario<Record<string, unknown>>({name, initial_state: {A: '10'}, logs});
      } else {
        const params = Object.fromEntries(input.split(',').map((part) => part.split('=').map((value) => value.trim())).filter((entry) => entry.length === 2).map(([key, value]) => [key, Number(value)]));
        if (Object.values(params).some((value) => !Number.isFinite(value))) throw new Error('Use numeric key=value parameters separated by commas.');
        response = await analysisApi.saveOsScenario<Record<string, unknown>>({name, scenario_type: 'CPU_LOAD', parameters: params});
      }
      setResult(response); setError(''); onAction('Analysis completed and saved to the backend.');
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to analyze this scenario.'); }
  };
  return <div className="content-two-col"><section className="surface-panel"><div className="panel-heading"><div><h3>{isSchedule ? 'Proposed transaction schedule' : isRecovery ? 'Recovery log after crash' : 'OS workload parameters'}</h3><p>Analysis runs through the API and saves the resulting scenario.</p></div><span className="event-tag tag-lavender">What-if analysis</span></div><label className="field-label">Scenario name<input value={name} onChange={(event) => setName(event.target.value)} /></label><label className="field-label">{isSchedule ? 'Schedule operations' : isRecovery ? 'Recovery steps' : 'CPU workload parameters'}<textarea value={input} onChange={(event) => setInput(event.target.value)} /></label><button type="button" className="button button-primary" onClick={() => void analyzeAndSave()}>Analyze and save <ArrowRight size={14} /></button>{error && <div className="empty-state">{error}</div>}</section><section className="surface-panel simulation-result"><div className="panel-heading"><div><h3>Backend result</h3><p>Hypothetical analysis, not observed behavior</p></div></div>{result ? <pre className="result-json">{JSON.stringify(result, null, 2)}</pre> : <div className="empty-state">Run the analysis to see its result here.</div>}</section></div>;
}

function LiveSavedScenarios() {
  const [items, setItems] = useState<Array<{scenario_id: number; analysis_type: string; name: string; result: Record<string, unknown>; created_at: string}>>([]);
  const [error, setError] = useState('');
  const refresh = () => analysisApi.scenarios<(typeof items)[number]>()
    .then((result) => { setItems(result); setError(''); })
    .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Unable to load saved scenarios.'));
  useEffect(() => { void refresh(); }, []);
  return <section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Saved what-if scenarios</h3><p>Persisted analysis results from the API</p></div><button type="button" className="button button-secondary" onClick={() => void refresh()}>Refresh</button></div>{error ? <div className="empty-state">{error}</div> : items.length ? <div className="table-wrap"><table><thead><tr><th>Scenario</th><th>Type</th><th>Created</th><th>Result summary</th></tr></thead><tbody>{items.map((item) => <tr key={item.scenario_id}><td><b>{item.name}</b></td><td>{item.analysis_type}</td><td>{new Date(item.created_at).toLocaleString()}</td><td>{Object.entries(item.result).slice(0, 3).map(([key, value]) => `${key}: ${String(value)}`).join(' · ') || 'Completed'}</td></tr>)}</tbody></table></div> : <div className="empty-state">No scenarios have been saved yet.</div>}</section>;
}

function Administration({ tab, currentUser, onSignOut }: { tab: string; currentUser: AuthUser; onSignOut: () => void }) {
  if (tab === 'Accounts & sign-in') return <AccountSettings user={currentUser} onSignOut={onSignOut} />;
  return <LiveAuditLog user={currentUser} />;
}

function LiveAuditLog({ user }: { user: AuthUser }) {
  const [items, setItems] = useState<Array<{id: number; username?: string | null; action: string; details?: string | null; timestamp: string}>>([]);
  const [error, setError] = useState('');
  const refresh = () => analysisApi.auditLog<(typeof items)[number]>()
    .then((result) => { setItems(result); setError(''); })
    .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Unable to load the audit log.'));
  useEffect(() => { void refresh(); }, []);
  if (!user.is_admin) return <section className="surface-panel"><div className="panel-heading"><div><h3>Audit log</h3><p>Administrator access required</p></div></div><div className="empty-state">Your signed-in account does not have permission to view the audit log.</div></section>;
  return <section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Administrative audit log</h3><p>Persisted account activity from the API</p></div><button type="button" className="button button-secondary" onClick={() => void refresh()}>Refresh</button></div>{error ? <div className="empty-state">{error}</div> : items.length ? <div className="table-wrap"><table><thead><tr><th>Time</th><th>User</th><th>Action</th><th>Details</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td>{new Date(item.timestamp).toLocaleString()}</td><td>{item.username ?? '—'}</td><td>{item.action}</td><td>{item.details ?? '—'}</td></tr>)}</tbody></table></div> : <div className="empty-state">No audit records are available.</div>}</section>;
}

function AccountSettings({ user, onSignOut }: { user: AuthUser; onSignOut: () => void }) {
  return <section className="surface-panel account-settings">
    <div className="panel-heading"><div><h3>Signed-in account</h3><p>Authenticated OS-DBX session</p></div><span className="event-tag tag-lavender">{user.is_admin ? 'Administrator' : 'Member'}</span></div>
    <div className="account-profile"><div className="account-avatar">{user.username.slice(0, 2).toUpperCase()}</div><div><strong>{user.username}</strong><small>{user.email ?? 'No email registered'}</small></div></div>
    <div className="health-facts"><span>Username <b>{user.username}</b></span><span>Email <b>{user.email ?? 'Not provided'}</b></span><span>Email verification <b>{user.email_verified ? 'Verified' : 'Not verified'}</b></span><span>Two-step verification <b>{user.totp_enabled ? 'Authenticator enabled' : 'Not enabled'}</b></span><span>Role <b>{user.is_admin ? 'Administrator' : 'Member'}</b></span></div>
    <button type="button" className="button button-secondary" onClick={onSignOut}>Sign out</button>
  </section>;
}

export default App;
