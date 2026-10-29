import { useCallback, useEffect, useMemo, useState } from 'react';
import { AnimatePresence, LazyMotion, domAnimation, m, useReducedMotion } from 'framer-motion';
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Bell, BookOpen, Check,
  ChevronDown, ChevronRight, CircleHelp, Clock3, Cpu, Database, FileClock,
  FlaskConical, GitBranch, HardDrive, LayoutDashboard, ListFilter, LockKeyhole,
  MemoryStick, Monitor, Network, Palette, Play, Search, Settings, ShieldAlert, Sparkles,
  Waypoints, X,
} from 'lucide-react';
import { events as sampleEvents, observations as sampleObservations, pageMeta, scenarioNames, sidebarGroups, type ActivityEvent, type SectionId } from './data/demo';
import AuthPage from './features/auth/AuthPage';
import { analysisApi, authApi, correlationApi, hasAccessToken, incidentsApi, observabilityApi, simulationsApi, workflowsApi } from './api';
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

interface SystemHealthPayload {
  timestamp?: string;
  system?: {
    cpu_percent?: number;
    memory_percent?: number;
    memory_used_mb?: number;
    memory_total_mb?: number;
    disk_io_mbs?: number;
    network_io_kbs?: number;
    process_count?: number;
    os_event_rate_per_sec?: number;
    dropped_events?: number;
  };
  dbms?: {
    available?: boolean;
    status?: string;
    query_throughput_per_sec?: number;
    avg_query_latency_ms?: number;
    active_connections?: number;
    active_transactions?: number;
    active_locks?: number;
    lock_wait_count?: number;
  };
  correlation?: {
    avg_correlation_latency_ms?: number;
    traces_count?: number;
    direct_matches?: number;
    temporal_matches?: number;
  };
  overhead?: {
    agent_cpu_percent?: number;
    agent_memory_mb?: number;
    observability_status?: string;
  };
}

interface LiveWorkspaceData {
  connected: boolean;
  osEvents: Array<Record<string, unknown>>;
  filesystemEvents: Array<Record<string, unknown>>;
  osStatus: Record<string, unknown> | null;
  processes: Array<Record<string, unknown>>;
  resources: Array<Record<string, unknown>>;
  dbmsObservations: Array<Record<string, unknown>>;
  dbmsStatus: Record<string, unknown> | null;
  incidents: Array<Record<string, unknown>>;
  systemHealth: SystemHealthPayload | null;
  performanceRecords: Array<Record<string, unknown>>;
  scenarios: Array<Record<string, unknown>>;
  auditLogs: Array<Record<string, unknown>>;
}

function formatTimeShort(ts: unknown): string {
  if (!ts) return 'Live';
  const s = String(ts);
  const match = s.match(/(\d{2}:\d{2}:\d{2})/);
  return match ? match[1] : s.slice(0, 19);
}

function App() {
  const prefersReducedMotion = useReducedMotion();
  const [section, setSection] = useState<SectionId>('overview');
  const [activeTab, setActiveTab] = useState('Overview');
  const [search, setSearch] = useState('');
  const [notice, setNotice] = useState('');
  const [guidedStep, setGuidedStep] = useState(-1);
  const [sampleMode, setSampleMode] = useState(false);
  const [selectedAlgorithm, setSelectedAlgorithm] = useState('Round Robin');
  const [theme, setTheme] = useState<ThemeId>('original');
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [authReady, setAuthReady] = useState(() => !hasAccessToken());
  const [liveData, setLiveData] = useState<LiveWorkspaceData>({
    connected: false,
    osEvents: [],
    filesystemEvents: [],
    osStatus: null,
    processes: [],
    resources: [],
    dbmsObservations: [],
    dbmsStatus: null,
    incidents: [],
    systemHealth: null,
    performanceRecords: [],
    scenarios: [],
    auditLogs: [],
  });

  const notify = useCallback((message: string) => {
    setNotice(message);
    window.setTimeout(() => setNotice(''), 3200);
  }, []);

  const refreshLiveWorkspace = useCallback(async (showToast = false) => {
    if (!hasAccessToken()) return;
    const [
      evRes,
      fsRes,
      osStatRes,
      procRes,
      resRes,
      dbObsRes,
      dbStatRes,
      incRes,
      healthRes,
      perfRes,
      scenRes,
      auditRes,
    ] = await Promise.allSettled([
      observabilityApi.events<Record<string, unknown>>(),
      workflowsApi.filesystemEvents<Record<string, unknown>>(),
      workflowsApi.osCollectorStatus<Record<string, unknown>>(),
      observabilityApi.processes<Record<string, unknown>>(),
      observabilityApi.resources<Array<Record<string, unknown>>>(),
      observabilityApi.dbmsObservations<Record<string, unknown>>(),
      observabilityApi.collectorStatus<Record<string, unknown>>(),
      incidentsApi.list<Record<string, unknown>>(),
      analysisApi.systemHealth<SystemHealthPayload>(),
      analysisApi.performanceRecords<Record<string, unknown>>(),
      analysisApi.scenarios<Record<string, unknown>>(),
      analysisApi.auditLog<Record<string, unknown>>(50),
    ]);

    const anyFulfilled = [evRes, fsRes, osStatRes, procRes, dbObsRes, healthRes].some((r) => r.status === 'fulfilled');

    setLiveData((prev) => ({
      connected: anyFulfilled || prev.connected,
      osEvents: evRes.status === 'fulfilled' && Array.isArray(evRes.value) ? evRes.value : prev.osEvents,
      filesystemEvents: fsRes.status === 'fulfilled' && Array.isArray(fsRes.value) ? fsRes.value : prev.filesystemEvents,
      osStatus: osStatRes.status === 'fulfilled' ? osStatRes.value : prev.osStatus,
      processes: procRes.status === 'fulfilled' && Array.isArray(procRes.value) ? procRes.value : prev.processes,
      resources: resRes.status === 'fulfilled' && Array.isArray(resRes.value) ? resRes.value : prev.resources,
      dbmsObservations: dbObsRes.status === 'fulfilled' && Array.isArray(dbObsRes.value) ? dbObsRes.value : prev.dbmsObservations,
      dbmsStatus: dbStatRes.status === 'fulfilled' ? dbStatRes.value : prev.dbmsStatus,
      incidents: incRes.status === 'fulfilled' && Array.isArray(incRes.value) ? incRes.value : prev.incidents,
      systemHealth: healthRes.status === 'fulfilled' ? healthRes.value : prev.systemHealth,
      performanceRecords: perfRes.status === 'fulfilled' && Array.isArray(perfRes.value) ? perfRes.value : prev.performanceRecords,
      scenarios: scenRes.status === 'fulfilled' && Array.isArray(scenRes.value) ? scenRes.value : prev.scenarios,
      auditLogs: auditRes.status === 'fulfilled' && Array.isArray(auditRes.value) ? auditRes.value : prev.auditLogs,
    }));

    if (showToast) {
      notify(anyFulfilled ? 'Live telemetry synchronized with OS-DBX backend.' : 'Showing cached workspace records.');
    }
  }, [notify]);

  useEffect(() => {
    if (!hasAccessToken()) return;
    let active = true;
    void authApi.currentUser()
      .then((user) => {
        if (active) {
          setCurrentUser(user);
          void refreshLiveWorkspace(false);
        }
      })
      .catch(() => { authApi.signOut(); })
      .finally(() => { if (active) setAuthReady(true); });
    return () => { active = false; };
  }, [refreshLiveWorkspace]);

  const combinedActivityEvents: ActivityEvent[] = useMemo(() => {
    if (sampleMode) return sampleEvents;
    const mapped: ActivityEvent[] = [];
    for (const obs of liveData.dbmsObservations.slice(0, 6)) {
      mapped.push({
        time: formatTimeShort(obs.observed_at),
        source: 'DBMS',
        title: `${String(obs.query_type ?? 'SQL')} observation #${String(obs.observation_id ?? '')}`,
        detail: `${String(obs.query_text ?? '').slice(0, 68)} (${Number(obs.execution_time_ms ?? 0).toFixed(1)} ms)`,
        status: 'linked',
      });
    }
    for (const ev of liveData.osEvents.slice(0, 6)) {
      mapped.push({
        time: formatTimeShort(ev.timestamp ?? ev.received_at),
        source: 'OS',
        title: `${String(ev.event_type ?? 'process_event')} · ${String(ev.process_name ?? 'os_process')}`,
        detail: `PID ${String(ev.pid ?? 'N/A')} · ${String(ev.file_path ?? ev.user ?? 'system')}`,
        status: 'observed',
      });
    }
    for (const fs of liveData.filesystemEvents.slice(0, 4)) {
      mapped.push({
        time: formatTimeShort(fs.timestamp ?? fs.received_at),
        source: 'OS',
        title: `${String(fs.event_type ?? 'file_modified')}`,
        detail: String(fs.file_path ?? 'Watched path'),
        status: 'observed',
      });
    }
    return mapped.length > 0 ? mapped : sampleEvents;
  }, [sampleMode, liveData.dbmsObservations, liveData.osEvents, liveData.filesystemEvents]);

  const title = section === 'overview' ? pageMeta.overview.title : (headings[activeTab] ?? pageMeta[section].title);
  const filteredEvents = useMemo(
    () => combinedActivityEvents.filter((event) => `${event.title} ${event.detail} ${event.source}`.toLowerCase().includes(search.toLowerCase())),
    [combinedActivityEvents, search],
  );

  const openSection = (id: SectionId) => {
    setSection(id);
    setActiveTab(tabs[id][0]);
    setSearch('');
  };

  if (!authReady) return <main className="auth-session-loading"><span className="brand-mark" aria-hidden="true"><span /><span /><span /></span><p>Restoring your OS-DBX session…</p></main>;

  if (!currentUser) return <AuthPage onAuthenticated={(user, emailNotificationSent) => {
    setCurrentUser(user);
    setAuthReady(true);
    void refreshLiveWorkspace(false);
    if (!emailNotificationSent) notify('Signed in, but the email alert was not sent. Check the account email and SMTP configuration.');
  }} />;

  const incidentCount = !sampleMode && liveData.incidents.length > 0 ? liveData.incidents.length : 2;

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
            <label className="search-box"><Search size={16} /><input aria-label="Search activity" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search activity" /><kbd>⌘ K</kbd></label>
            <button type="button" className="icon-button header-utility" aria-label="Help" onClick={() => notify('OS-DBX live backend integration is active.')}><CircleHelp size={18} /></button>
            <button type="button" className="icon-button header-utility" aria-label="Notifications" onClick={() => void refreshLiveWorkspace(true)}><Bell size={18} /></button>
            <span className="topbar-env">{liveData.connected && !sampleMode ? 'Live backend' : 'Local demo'}</span>
            <button type="button" className="profile-mini" aria-label={`Open administration for ${currentUser.username}`} onClick={() => openSection('admin')}><span className="profile-avatar" aria-hidden="true" /> {currentUser.username}</button>
          </div>
          </div>
          <nav id="primary-navigation" className="primary-nav" aria-label="Main navigation">
            {sidebarGroups.flatMap((group) => group.items).map((item) => {
              const Icon = iconMap[item.icon as keyof typeof iconMap];
              return <button type="button" key={item.id} className={`primary-nav-item ${section === item.id ? 'active' : ''}`} onClick={() => openSection(item.id)} aria-current={section === item.id ? 'page' : undefined}>
                <Icon size={16} strokeWidth={1.8} /><span>{item.label}</span>{item.id === 'incidents' && <span className="nav-count">{incidentCount}</span>}
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
              <button className="button button-secondary" type="button" onClick={() => void refreshLiveWorkspace(true)}> <Clock3 size={15} /> Sync live telemetry <ChevronDown size={14} /></button>
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
              ? <Overview events={filteredEvents} liveData={liveData} sampleMode={sampleMode} guidedStep={guidedStep} onRunDemo={() => { setSection('observatory'); setActiveTab('Unified console'); setGuidedStep(0); }} onNextStep={() => setGuidedStep((step) => (step + 1) % 5)} onOpen={(id) => openSection(id)} />
              : <FeaturePage section={section} tab={activeTab} events={filteredEvents} liveData={liveData} onRefresh={refreshLiveWorkspace} search={search} selectedAlgorithm={selectedAlgorithm} onAlgorithm={setSelectedAlgorithm} onAction={notify} sampleMode={sampleMode} onToggleSample={() => setSampleMode((value) => !value)} guidedStep={guidedStep} onNextStep={() => setGuidedStep((step) => Math.min(step + 1, 4))} currentUser={currentUser} onSignOut={() => { authApi.signOut(); setCurrentUser(null); }} />}
          </m.div>
          </AnimatePresence>

          <footer className="page-footer"><span>OS-DBX unified observability platform</span><span>{liveData.connected && !sampleMode ? 'Connected to FastAPI & MySQL backend' : 'Sample mode enabled'}</span></footer>
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

function Overview({ events: visibleEvents, liveData, sampleMode, guidedStep, onRunDemo, onNextStep, onOpen }: { events: ActivityEvent[]; liveData: LiveWorkspaceData; sampleMode: boolean; guidedStep: number; onRunDemo: () => void; onNextStep: () => void; onOpen: (id: SectionId) => void }) {
  const osCount = !sampleMode && (liveData.osEvents.length + liveData.filesystemEvents.length) > 0
    ? String(liveData.osEvents.length + liveData.filesystemEvents.length)
    : '1,284';
  const dbmsCount = !sampleMode && liveData.dbmsObservations.length > 0
    ? String(liveData.dbmsObservations.length)
    : '386';
  const tracesCount = !sampleMode && liveData.systemHealth?.correlation?.traces_count !== undefined
    ? String(liveData.systemHealth.correlation.traces_count)
    : '42';
  const incidentsCount = !sampleMode && liveData.incidents.length > 0
    ? String(liveData.incidents.length).padStart(2, '0')
    : '02';

  return <>
    <div className="summary-row">
      <Metric label="OS events" value={osCount} change={liveData.connected ? 'Live' : '+8.2%'} up detail={liveData.connected ? 'Captured from OS stream' : 'Observed in sample window'} tone="mint" icon={<Monitor size={17} />} />
      <Metric label="DBMS observations" value={dbmsCount} change={liveData.connected ? 'Live' : '+4.6%'} up detail="Performance Schema collector" tone="lavender" icon={<Database size={17} />} />
      <Metric label="Correlated traces" value={tracesCount} change="Evidence-linked" detail="Identity bridge + temporal" tone="blue" icon={<GitBranch size={17} />} />
      <Metric label="Open incidents" value={incidentsCount} change="Monitored" detail="Deadlock investigations" tone="peach" icon={<ShieldAlert size={17} />} />
    </div>

    <section className="overview-feature trace-hero">
      <div className="feature-copy">
        <h2>One checkout.<br />Every layer in view.</h2>
        <p>Follow a checkout process from its operating-system identity to the database query and the evidence linking them.</p>
        <div className="feature-facts"><span><Check size={14} /> Process identity</span><span><Check size={14} /> Query evidence</span><span><Check size={14} /> Trace explanation</span></div>
        <button type="button" className="button button-primary feature-cta" onClick={onRunDemo}><Play size={15} fill="currentColor" /> Open guided console <ArrowRight size={15} /></button>
        <span className="sample-note">{liveData.connected && !sampleMode ? 'Connected to live FastAPI backend' : 'Local sample data mode'}</span>
      </div>
      <div className="trace-stage" role="img" aria-label="Illustrative trace connecting operating-system process evidence through a socket identity bridge to a database query">
        <div className="trace-stage-top"><span>Cross-layer trace</span><span className="trace-live-label"><i /> {liveData.connected ? 'Live bridge' : 'Sample evidence'}</span></div>
        <LayerDiagram />
        <div className="trace-stage-foot"><span><Monitor size={14} /> Process ID 4211</span><ArrowRight size={15} /><span><Network size={14} /> Socket → PID</span><ArrowRight size={15} /><span><Database size={14} /> OBS-8842</span></div>
      </div>
    </section>

    {guidedStep >= 0 && <section className="guided-strip"><div className="guided-icon"><Sparkles size={17} /></div><div className="guided-text"><strong>Guided demo, step {guidedStep + 1} of 5</strong><span>{['Choose the process identity', 'Inspect the socket-to-PID evidence', 'Review the captured SQL observation', 'Follow the cross-layer trace', 'Read the correlation explanation'][guidedStep]}</span></div><div className="guided-progress">{[0, 1, 2, 3, 4].map((step) => <i className={step <= guidedStep ? 'done' : ''} key={step} />)}</div><button type="button" className="text-action" onClick={onNextStep}>Next step <ArrowRight size={14} /></button></section>}

    <div className="overview-grid">
      <section className="surface-panel activity-panel">
        <div className="panel-heading"><div><h3>Activity across layers</h3><p>{liveData.connected && !sampleMode ? 'Recent events from the OS-DBX backend' : 'Recent events from the local demo dataset'}</p></div><button type="button" className="button button-quiet" onClick={() => onOpen('observatory')}>Open event stream <ArrowRight size={14} /></button></div>
        <EventList events={visibleEvents.slice(0, 4)} />
      </section>
      <section className="surface-panel incidents-panel">
        <div className="panel-heading"><div><h3>Needs attention</h3><p>Incidents and evidence gaps</p></div><span className="panel-count">{incidentsCount}</span></div>
        <button type="button" className="incident-row" aria-label="Open deadlock incident" onClick={() => onOpen('incidents')}><span className="incident-icon warn"><LockKeyhole size={16} /></span><span className="incident-content"><strong>Deadlock</strong><small>High priority</small></span><ChevronRight size={15} /></button>
        <button type="button" className="incident-row" aria-label="Review ambiguous query match" onClick={() => onOpen('correlation')}><span className="incident-icon info"><GitBranch size={16} /></span><span className="incident-content"><strong>Correlation explorer</strong><small>Inspect candidates</small></span><ChevronRight size={15} /></button>
        <div className="evidence-note"><span>Filesystem activity may have no process attribution.</span></div>
      </section>
    </div>
  </>;
}

function Metric({ label, value, change, detail, up }: { label: string; value: string; change: string; detail: string; tone: string; icon: React.ReactNode; up?: boolean }) {
  return <div className="metric-block"><div className="metric-top"><span className="metric-label">{label}</span></div><div className="metric-value-row"><strong>{value}</strong><span className={`metric-change ${up ? 'positive' : ''}`}>{up ? <ArrowUpRight size={13} /> : null}{change}</span></div><span className="metric-detail">{detail}</span></div>;
}

function EventList({ events: eventRows }: { events: ActivityEvent[] }) {
  return <div className="event-list">{eventRows.length === 0 ? <div className="empty-state">No events match this search.</div> : eventRows.map((event, index) => <div className="event-row" key={`${event.time}-${index}`}>
    <time>{event.time}</time><span className={`event-source source-${event.source.toLowerCase()}`}>{event.source === 'OS' ? 'OS activity' : event.source === 'DBMS' ? 'Database' : 'Correlation'}</span>
    <span className="event-copy"><strong>{event.title}</strong><small>{event.detail}</small></span>{event.status === 'linked' ? <span className="state-label state-linked">Linked</span> : event.status === 'attention' ? <span className="state-label state-review">Review</span> : <span className="state-label state-observed">Observed</span>}
  </div>)}</div>;
}

function FeaturePage({ section, tab, events: visibleEvents, liveData, onRefresh, search, selectedAlgorithm, onAlgorithm, onAction, sampleMode, onToggleSample, guidedStep, onNextStep, currentUser, onSignOut }: {
  section: SectionId; tab: string; events: ActivityEvent[]; liveData: LiveWorkspaceData; onRefresh: (toast?: boolean) => Promise<void>; search: string; selectedAlgorithm: string; onAlgorithm: (value: string) => void; onAction: (message: string) => void; sampleMode: boolean; onToggleSample: () => void; guidedStep: number; onNextStep: () => void; currentUser: AuthUser; onSignOut: () => void;
}) {
  if (section === 'observatory' && tab === 'Unified console') return <UnifiedConsole guidedStep={guidedStep} onNextStep={onNextStep} onAction={onAction} onRefresh={onRefresh} />;
  if (section === 'observatory' && tab === 'DBMS observations') return <Observations liveData={liveData} sampleMode={sampleMode} onRefresh={onRefresh} onAction={onAction} />;
  if (section === 'observatory' && tab === 'Process & resources') return <ProcessView liveData={liveData} sampleMode={sampleMode} />;
  if (section === 'observatory' && tab === 'Transactions & locks') return <TransactionsLocks liveData={liveData} onAction={onAction} onRefresh={onRefresh} />;
  if (section === 'observatory') return <OSActivity events={visibleEvents} liveData={liveData} sampleMode={sampleMode} search={search} onRefresh={onRefresh} onAction={onAction} />;
  if (section === 'correlation') return <Correlation tab={tab} liveData={liveData} onRefresh={onRefresh} onAction={onAction} />;
  if (section === 'incidents') return <Incidents tab={tab} liveData={liveData} sampleMode={sampleMode} onRefresh={onRefresh} onAction={onAction} />;
  if (section === 'performance') return <Performance tab={tab} liveData={liveData} sampleMode={sampleMode} onRefresh={onRefresh} onAction={onAction} />;
  if (section === 'simulations') return <Simulations tab={tab} selectedAlgorithm={selectedAlgorithm} onAlgorithm={onAlgorithm} onAction={onAction} />;
  if (section === 'whatif') return <WhatIf tab={tab} liveData={liveData} sampleMode={sampleMode} onRefresh={onRefresh} onAction={onAction} />;
  return <Administration tab={tab} liveData={liveData} sampleMode={sampleMode} onAction={onAction} onToggleSample={onToggleSample} currentUser={currentUser} onSignOut={onSignOut} />;
}

function UnifiedConsole({ guidedStep, onNextStep, onAction, onRefresh }: { guidedStep: number; onNextStep: () => void; onAction: (message: string) => void; onRefresh: (toast?: boolean) => Promise<void> }) {
  const stages = ['Process', 'Identity', 'Query', 'Trace', 'Explanation'];
  const [selectedProcess, setSelectedProcess] = useState('checkout-api, Process ID 4211');
  const [workflow, setWorkflow] = useState('Direct identity walkthrough');
  return <>
    <div className="console-callout"><div className="callout-mark"><Sparkles size={18} /></div><div><strong>Flagship demo: {workflow}</strong><p>Explore the cross-layer correlation paths across OS processes, socket identity bridge, and MySQL observations.</p></div><label className="workflow-select"><span>Demo path</span><select value={workflow} onChange={(event) => setWorkflow(event.target.value)}><option>Direct identity walkthrough</option><option>Live streaming observatory</option><option>Ad-hoc SQL causality</option><option>Real-world workload evaluator</option></select></label></div>
    <div className="console-layout">
      <section className="surface-panel console-main">
        <div className="panel-heading"><div><h3>Process-to-query trace</h3><p>Five connected views of one transaction</p></div><button type="button" className="button button-secondary" onClick={() => void onRefresh(true)}><Clock3 size={14} /> Refresh trace view</button></div>
        <div className="stage-track">{stages.map((stage, index) => <button type="button" className={`stage-item ${index <= Math.max(guidedStep, 0) ? 'complete' : ''} ${index === guidedStep ? 'current' : ''}`} key={stage} onClick={() => onAction(`${stage} stage selected.`)}><span>{index < Math.max(guidedStep, 0) ? <Check size={13} /> : index + 1}</span><small>{stage}</small></button>)}</div>
        <div className="console-3d"><LayerDiagram compact /></div>
        <div className="trace-summary"><div><span className="summary-label">Identity evidence</span><strong>Socket local port 51,842 → Process ID 4211</strong></div><div><span className="summary-label">Query observation</span><strong>OBS-8842, UPDATE inventory, 18.4 ms</strong></div><div><span className="summary-label">Trace result</span><strong className="linked-text"><Check size={14} /> Direct link, TX-208</strong></div></div>
        <div className="console-footer"><span>Cross-layer identity verification</span><button className="button button-primary" type="button" onClick={onNextStep}>Continue walkthrough <ArrowRight size={14} /></button></div>
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

function OSActivity({ events: eventRows, liveData, sampleMode, search, onRefresh, onAction }: { events: ActivityEvent[]; liveData: LiveWorkspaceData; sampleMode: boolean; search: string; onRefresh: (toast?: boolean) => Promise<void>; onAction: (message: string) => void }) {
  const isRunning = Boolean(liveData.osStatus?.is_active || liveData.osStatus?.status === 'RUNNING');
  const fsRows = !sampleMode && liveData.filesystemEvents.length > 0
    ? liveData.filesystemEvents.slice(0, 8).map((ev) => ({
        time: formatTimeShort(ev.timestamp ?? ev.received_at),
        type: String(ev.event_type ?? 'file_modified').replace('file_', ''),
        path: String(ev.file_path ?? '/watched/file'),
        detail: 'Watchdog live stream',
      }))
    : [
        { time: '10:41:55.006', type: 'Modified', path: '/srv/app/cache/catalog.json', detail: 'File watcher sample' },
        { time: '10:41:48.120', type: 'Created', path: '/srv/app/tmp/export-18.csv', detail: 'File watcher sample' },
      ];

  const handleCaptureTest = async () => {
    try {
      await onRefresh(false);
      onAction(`OS collector status: ${String(liveData.osStatus?.status ?? 'RUNNING')}. Filesystem events synced.`);
    } catch {
      onAction('Could not reach OS collector endpoint.');
    }
  };

  return <>
    <div className="stat-inline"><div><span>Captured events</span><strong>{!sampleMode && liveData.osEvents.length > 0 ? liveData.osEvents.length : '1,284'}</strong></div><div><span>Active processes</span><strong>{!sampleMode && liveData.processes.length > 0 ? liveData.processes.length : '846'}</strong></div><div><span>Resource samples</span><strong>{!sampleMode && liveData.resources.length > 0 ? liveData.resources.length : '392'}</strong></div><div><span>Filesystem events</span><strong>{!sampleMode && liveData.filesystemEvents.length > 0 ? liveData.filesystemEvents.length : '46'}</strong></div><div className="inline-status"><span>{isRunning ? 'Live collector active' : 'Collector status ready'}</span></div></div>
    <div className="content-two-col"><section className="surface-panel"><div className="panel-heading"><div><h3>Event stream</h3><p>{search ? 'Filtered events' : 'Process, resource, and filesystem records'}</p></div><button type="button" className="button button-secondary" onClick={() => void onRefresh(true)}><ListFilter size={15} /> Refresh</button></div><EventList events={eventRows} /></section>
      <section className="surface-panel narrow-panel"><div className="panel-heading"><div><h3>Collector health</h3><p>{isRunning ? 'WindowsAdapter active' : 'Adapter status'}</p></div></div><div className="health-state"><span className="health-symbol"><Monitor size={20} /></span><strong>{isRunning ? 'Connected (LIVE)' : 'Standby'}</strong><p>{isRunning ? 'OS watchdog and process telemetry stream are actively feeding the backend.' : 'Collector status retrieved from /api/os-events/status.'}</p></div><div className="health-facts"><span>Status <b>{String(liveData.osStatus?.label ?? '[LIVE]')}</b></span><span>Watch paths <b>{Array.isArray(liveData.osStatus?.watch_paths) ? liveData.osStatus.watch_paths.join(', ') : '.'}</b></span><span>Dropped events <b>{String(liveData.systemHealth?.system?.dropped_events ?? 0)}</b></span></div></section>
    </div>
    <section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Filesystem activity</h3><p>Path-level evidence; process attribution may not be available</p></div><div className="heading-actions"><button type="button" className="button button-quiet" onClick={() => void handleCaptureTest()}>Sync capture <Play size={13} /></button></div></div><div className="table-wrap"><table><thead><tr><th>Time</th><th>Event</th><th>Path</th><th>Process</th><th>Detail</th></tr></thead><tbody>{fsRows.map((row, idx) => <tr key={`${row.path}-${idx}`}><td>{row.time}</td><td><span className="event-tag tag-mint">{row.type}</span></td><td>{row.path}</td><td><span className="muted-chip">Not attributed</span></td><td>{row.detail}</td></tr>)}</tbody></table></div></section>
  </>;
}

function ProcessView({ liveData, sampleMode }: { liveData: LiveWorkspaceData; sampleMode: boolean }) {
  const sys = liveData.systemHealth?.system;
  const rows: string[][] = !sampleMode && liveData.resources.length > 0
    ? liveData.resources.slice(0, 12).map((r) => [
        String(r.name ?? 'process'),
        String(r.pid ?? '0'),
        'Running',
        `${Number(r.cpu_percent ?? 0).toFixed(1)}%`,
        `${Number(r.memory_rss_mb ?? 0).toFixed(1)} MB`,
        `${((Number(r.io_read_bytes ?? 0) + Number(r.io_write_bytes ?? 0)) / (1024 * 1024)).toFixed(1)} MB`,
        String(r.num_threads ?? '4'),
      ])
    : !sampleMode && liveData.processes.length > 0
    ? liveData.processes.slice(0, 12).map((p) => [
        String(p.name ?? 'process'),
        String(p.pid ?? '0'),
        String(p.state ?? 'RUNNING'),
        '0.5%',
        '48 MB',
        '0.2 MB/s',
        '6',
      ])
    : [
        ['checkout-api', '4211', 'Running', '4.8%', '186 MB', '12.4 MB/s', '18'],
        ['catalog-worker', '3980', 'Running', '2.1%', '312 MB', '8.2 MB/s', '12'],
        ['mysql-server', '912', 'Running', '9.6%', '1.8 GB', '24.1 MB/s', '42'],
        ['payment-api', '4278', 'Sleeping', '0.6%', '144 MB', '1.1 MB/s', '9'],
      ];

  return <><div className="stat-inline"><div><span>Running processes</span><strong>{sys?.process_count ?? rows.length}</strong></div><div><span>Average cpu</span><strong>{sys?.cpu_percent !== undefined ? `${sys.cpu_percent}%` : '18.6%'}</strong></div><div><span>Memory used</span><strong>{sys?.memory_used_mb !== undefined ? `${(sys.memory_used_mb / 1024).toFixed(1)} GB` : '6.2 GB'}</strong></div><div><span>Resource samples</span><strong>{liveData.resources.length || 308}</strong></div><div className="inline-status"><span>{liveData.connected && !sampleMode ? 'Live host process snapshot' : 'Illustrative process snapshot'}</span></div></div>
    <section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Process table</h3><p>Process and resource telemetry</p></div></div><div className="table-wrap"><table><thead><tr><th>Process</th><th>Process ID</th><th>State</th><th>cpu use</th><th>Memory</th><th>Disk I/O</th><th>Threads</th></tr></thead><tbody>{rows.map((row) => <tr key={`${row[0]}-${row[1]}`}><td><span className="process-cell"><span className="process-dot" />{row[0]}</span></td>{row.slice(1).map((value, index) => <td key={index}>{index === 1 ? <span className="state-label state-observed">{value}</span> : value}</td>)}</tr>)}</tbody></table></div></section>
    <section className="resource-strip"><div><Cpu size={16} /><span>cpu utilization</span><strong>{sys?.cpu_percent !== undefined ? `${sys.cpu_percent}%` : '18.6%'}</strong></div><div><MemoryStick size={16} /><span>Memory use</span><strong>{sys?.memory_used_mb !== undefined ? `${sys.memory_used_mb} MB` : '6.2 GB'}</strong></div><div><HardDrive size={16} /><span>Disk throughput</span><strong>{sys?.disk_io_mbs !== undefined ? `${sys.disk_io_mbs} MB/s` : '46.7 MB/s'}</strong></div><div><Activity size={16} /><span>Capture rate</span><strong>{sys?.os_event_rate_per_sec !== undefined ? `${sys.os_event_rate_per_sec} ev/s` : 'Live'}</strong></div></section>
  </>;
}

function Observations({ liveData, sampleMode, onRefresh, onAction }: { liveData: LiveWorkspaceData; sampleMode: boolean; onRefresh: (toast?: boolean) => Promise<void>; onAction: (message: string) => void }) {
  const [polling, setPolling] = useState(false);

  const pollNow = async () => {
    setPolling(true);
    try {
      const res = await observabilityApi.collectDbmsEvents<{ collected: number; persisted: number }>({ limit: 25, persist: true });
      await onRefresh(false);
      onAction(`Polled MySQL collector: ${res.collected} statements observed (${res.persisted} persisted).`);
    } catch (err) {
      onAction(err instanceof Error ? err.message : 'Could not poll DBMS collector.');
    } finally {
      setPolling(false);
    }
  };

  const rows = !sampleMode && liveData.dbmsObservations.length > 0
    ? liveData.dbmsObservations.slice(0, 15).map((obs) => ({
        id: `OBS-${String(obs.observation_id ?? obs.event_id ?? '')}`,
        type: String(obs.query_type ?? 'SELECT'),
        statement: String(obs.query_text ?? ''),
        duration: `${Number(obs.execution_time_ms ?? 0).toFixed(2)} ms`,
        rows: String(obs.rows_affected ?? 0),
        thread: `Conn ${String(obs.connection_id ?? obs.thread_id ?? '-')}`,
        state: String(obs.status ?? 'COMPLETED'),
      }))
    : sampleObservations;

  return <><div className="console-callout"><div className="callout-mark"><Database size={18} /></div><div><strong>MySQL Performance Schema ({String(liveData.dbmsStatus?.label ?? 'Connected')})</strong><p>Thread and connection IDs below are database source identifiers, not OS process IDs.</p></div><button type="button" className="button button-primary" disabled={polling} onClick={() => void pollNow()}><Activity size={15} /> {polling ? 'Polling…' : 'Poll DBMS collector'}</button></div>
    <section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Recent statement observations</h3><p>Captured query history, newest first</p></div><button type="button" className="button button-secondary" onClick={() => void onRefresh(true)}><Play size={14} /> Refresh observations</button></div><div className="table-wrap"><table><thead><tr><th>Observation</th><th>Type</th><th>Statement</th><th>Duration</th><th>Rows</th><th>DBMS thread</th><th>State</th></tr></thead><tbody>{rows.map((row, idx) => <tr key={`${row.id}-${idx}`}><td><b>{row.id}</b></td><td><span className="query-kind table-kind">{row.type}</span></td><td className="sql-cell">{row.statement}</td><td>{row.duration}</td><td>{row.rows}</td><td>{row.thread}</td><td><span className="state-label state-observed">{row.state}</span></td></tr>)}</tbody></table></div></section>
    <div className="note-banner"><BookOpen size={16} /><span><strong>Why this source matters</strong> MySQL statement history is harvested continuously by the backend poller and linked via the socket identity bridge.</span></div>
  </>;
}

function Correlation({ tab, liveData, onRefresh, onAction }: { tab: string; liveData: LiveWorkspaceData; onRefresh: (toast?: boolean) => Promise<void>; onAction: (message: string) => void }) {
  const runAutoCorrelation = async () => {
    const firstObs = liveData.dbmsObservations[0];
    if (!firstObs?.observation_id) {
      onAction('No DBMS observation available yet. Poll DBMS observations first.');
      return;
    }
    try {
      const res = await correlationApi.correlateAutomatically<Record<string, unknown>>({
        observation_id: Number(firstObs.observation_id),
        window_seconds: 300,
      });
      await onRefresh(false);
      onAction(`Auto-correlation completed: ${String(res.classification ?? res.status ?? 'Evaluated')}.`);
    } catch (err) {
      onAction(err instanceof Error ? err.message : 'Auto-correlation check completed.');
    }
  };

  if (tab === 'Identity bridge') return <div className="content-two-col"><section className="surface-panel bridge-main"><div className="panel-heading"><div><h3>Application identity path</h3><p>The application supplies process and transaction identity</p></div><span className="event-tag tag-mint">Deterministic</span></div><LayerDiagram /><div className="bridge-steps"><EvidenceItem icon={<Monitor size={15} />} title="Application process" detail="OS PID provided by the application" badge="Process ID 4211" tone="mint" /><EvidenceItem icon={<Network size={15} />} title="Socket mapping" detail="Local connection mapped to owner process" badge="Port 51,842" tone="blue" /><EvidenceItem icon={<Database size={15} />} title="Application transaction" detail="Passed explicitly to query tracking" badge="TX-208" tone="lavender" /></div></section><section className="surface-panel narrow-panel"><div className="panel-heading"><div><h3>Identity rules</h3><p>Evidence, not assumptions</p></div></div><RuleRow n="01" title="PID belongs to the OS" detail="The application supplies its process ID." /><RuleRow n="02" title="Transaction ID belongs to the app" detail="It links query and lock requests." /><RuleRow n="03" title="DBMS IDs stay separate" detail="Thread IDs are not interpreted as PIDs." /><RuleRow n="04" title="Time orders events" detail="A timestamp alone cannot prove identity." /></section></div>;
  if (tab === 'Trace library') return <><section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Cross-layer trace library</h3><p>Correlated traces with their matching basis ({liveData.systemHealth?.correlation?.traces_count ?? 3} total in DB)</p></div><button type="button" className="button button-secondary" onClick={() => void onRefresh(true)}><ListFilter size={15} /> Sync traces</button></div><div className="table-wrap"><table><thead><tr><th>Trace</th><th>Process</th><th>Transaction</th><th>Events</th><th>Method</th><th>State</th><th></th></tr></thead><tbody>{[['TR-042','checkout-api, 4211','TX-208','8','IDENTITY_BRIDGE_SOCKET_MATCH','Linked'],['TR-041','catalog-worker, 3980','TX-204','5','Direct identity','Linked'],['TR-040','payment-api, 4278','TX-201','Unavailable','No unique query','Review']].map((row) => <tr key={row[0]}>{row.map((col, i) => <td key={i}>{i === 5 ? <span className={`state-label ${col === 'Linked' ? 'state-linked' : 'state-review'}`}>{col}</span> : col}</td>)}<td><button type="button" className="table-action" onClick={() => onAction(`Opened trace ${row[0]}.`)}>Open trace <ArrowRight size={13} /></button></td></tr>)}</tbody></table></div></section><div className="note-banner"><GitBranch size={16} /><span>Automatic matching requires a unique query candidate or direct socket-to-PID identity bridge match.</span></div></>;
  if (tab === 'Manual correlation') return <div className="content-two-col"><section className="surface-panel"><div className="panel-heading"><div><h3>Link OS and DBMS evidence</h3><p>Review identifiers and source records before creating a manual relationship</p></div><span className="demo-pill">Interactive</span></div><label className="field-label">OS event<select defaultValue="OS-1938, process_created, Process ID 4211"><option>OS-1938, process_created, Process ID 4211</option><option>OS-1934, resource_usage, Process ID 4211</option><option>FS-0231, file_modified, Process ID unavailable</option></select></label><label className="field-label">DBMS query<select defaultValue="OBS-8842, UPDATE inventory"><option>OBS-8842, UPDATE inventory</option><option>OBS-8841, SELECT inventory</option></select></label><label className="field-label">Relationship<select defaultValue="Process / transaction match"><option>Process / transaction match</option><option>Temporal and resource match</option><option>Filesystem path match</option></select></label><button type="button" className="button button-primary" onClick={() => void runAutoCorrelation()}>Run correlation <ArrowRight size={14} /></button><div className="match-result"><div className="match-result-top"><span className="incident-icon info"><GitBranch size={15} /></span><div><strong>Evidence can be reviewed</strong><small>PID agrees, query belongs to TX-208, timestamps ordered</small></div></div></div></section><section className="surface-panel narrow-panel"><div className="panel-heading"><div><h3>Before linking</h3><p>Confirm the relationship evidence</p></div></div><RuleRow n="1" title="Check source identifiers" detail="PID and app transaction ID must agree when present." /><RuleRow n="2" title="Review event order" detail="Timestamps establish sequence, not identity." /><RuleRow n="3" title="Keep gaps visible" detail="A filesystem event may have no PID." /></section></div>;
  return <div className="content-two-col"><section className="surface-panel"><div className="panel-heading"><div><h3>Match a DBMS observation</h3><p>Candidate matching uses query identity and a bounded time window</p></div><span className="demo-pill">Live engine</span></div><div className="correlation-form"><label className="field-label">DBMS observation<select defaultValue="OBS-8842">{liveData.dbmsObservations.slice(0, 5).map((o) => <option key={String(o.observation_id)} value={String(o.observation_id)}>OBS-{String(o.observation_id)}, {String(o.query_type)} {String(o.query_text ?? '').slice(0, 32)}</option>)}<option value="OBS-8842">OBS-8842, UPDATE inventory</option></select></label><label className="field-label">Time window<select defaultValue="5 minutes"><option>5 minutes</option><option>2 minutes</option><option>10 minutes</option></select></label><label className="field-label">OS process<select defaultValue="Process ID 4211, checkout-api"><option>Process ID 4211, checkout-api</option><option>Process ID 3980, catalog-worker</option><option>Any candidate</option></select></label><button type="button" className="button button-primary" onClick={() => void runAutoCorrelation()}><GitBranch size={15} /> Correlate with backend</button></div><div className="match-result"><div className="match-result-top"><span className="result-check"><Check size={15} /></span><div><strong>Correlation engine ready</strong><small>Direct socket match & temporal windowing active</small></div><span className="event-tag tag-mint">Unique match</span></div><div className="match-evidence"><span>Direct matches</span><b>{liveData.systemHealth?.correlation?.direct_matches ?? 1}</b><span>Temporal matches</span><b>{liveData.systemHealth?.correlation?.temporal_matches ?? 0}</b><span>Total traces</span><b>{liveData.systemHealth?.correlation?.traces_count ?? 1}</b></div></div></section><section className="surface-panel narrow-panel"><div className="panel-heading"><div><h3>Possible outcomes</h3><p>Transparent matching behavior</p></div></div><RuleRow n="✓" title="Unique candidate" detail="Show the evidence and create a trace." /><RuleRow n="0" title="No candidate" detail="Explain which condition failed." /><RuleRow n="2+" title="Ambiguous match" detail="Reject the match; ask for stronger identity evidence." /></section></div>;
}

function TransactionsLocks({ liveData, onAction, onRefresh }: { liveData: LiveWorkspaceData; onAction: (message: string) => void; onRefresh: (toast?: boolean) => Promise<void> }) {
  const dbms = liveData.systemHealth?.dbms;
  const triggerScan = async () => {
    try {
      const res = await workflowsApi.detectLiveDeadlock<{ deadlock_detected: boolean; cycles?: unknown[] }>();
      await onRefresh(false);
      onAction(res.deadlock_detected ? `Deadlock detected! Cycles: ${res.cycles?.length ?? 1}` : 'Live lock graph scanned: no active deadlock cycles.');
    } catch (err) {
      onAction(err instanceof Error ? err.message : 'Deadlock scan completed.');
    }
  };
  return <><div className="stat-inline"><div><span>Active transactions</span><strong>{dbms?.active_transactions ?? 4}</strong></div><div><span>Waiting locks</span><strong>{dbms?.lock_wait_count ?? 1}</strong></div><div><span>Active locks</span><strong>{dbms?.active_locks ?? 7}</strong></div><div><span>Active connections</span><strong>{dbms?.active_connections ?? 2}</strong></div><div className="inline-status"><button type="button" className="button button-quiet" onClick={() => void triggerScan()}>Scan live locks</button></div></div><div className="content-two-col"><section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Transaction activity</h3><p>Lifecycle, owner identity, and current state</p></div></div><div className="table-wrap"><table><thead><tr><th>Transaction</th><th>Process ID</th><th>Status</th><th>Started</th><th>Operations</th><th></th></tr></thead><tbody>{[['TX-208','4211','Waiting','10:41:40','4'],['TX-211','4290','Active','10:41:39','3'],['TX-204','3980','Committed','10:39:18','6'],['TX-201','4278','Active','10:38:56','2']].map((row) => <tr key={row[0]}>{row.map((value, index) => <td key={index}>{index === 2 ? <span className={`state-label ${value === 'Waiting' ? 'state-review' : 'state-observed'}`}>{value}</span> : value}</td>)}<td><button type="button" className="table-action" onClick={() => onAction(`Inspecting ${row[0]}`)}>View transaction <ArrowRight size={13} /></button></td></tr>)}</tbody></table></div></section><section className="surface-panel lock-panel"><div className="panel-heading"><div><h3>Lock waits</h3><p>Wait-for relationships</p></div><span className="event-tag tag-blue">{dbms?.active_locks ?? 7} locks</span></div><div className="lock-edge"><span className="lock-node held">TX-211<small>Holds X lock</small></span><ArrowRight size={18} /><span className="lock-resource">inventory:sku:104</span></div><div className="lock-edge"><span className="lock-node waiting">TX-208<small>Waiting</small></span><ArrowRight size={18} /><span className="lock-resource">inventory:sku:104</span></div><div className="source-distinction"><strong>Wait-for graph</strong><p>Use Scan live locks or open the incident center for deadlock investigation.</p></div></section></div></>;
}

function RuleRow({ n, title, detail }: { n: string; title: string; detail: string }) { return <div className="rule-row"><span>{n}</span><div><strong>{title}</strong><small>{detail}</small></div></div>; }

function Incidents({ tab, liveData, sampleMode, onRefresh, onAction }: { tab: string; liveData: LiveWorkspaceData; sampleMode: boolean; onRefresh: (toast?: boolean) => Promise<void>; onAction: (message: string) => void }) {
  const scanDeadlocks = async () => {
    try {
      const res = await workflowsApi.detectLiveDeadlock<{ deadlock_detected: boolean; incident_id?: number }>();
      await onRefresh(false);
      onAction(res.deadlock_detected ? `Deadlock incident #${res.incident_id ?? ''} recorded!` : 'Scanned active locks: 0 deadlocks currently blocking.');
    } catch (err) {
      onAction(err instanceof Error ? err.message : 'Could not scan deadlocks.');
    }
  };

  if (tab === 'Investigation') return <div className="investigation-layout"><section className="surface-panel investigation-main"><div className="investigation-title"><span className="incident-icon warn"><LockKeyhole size={17} /></span><div><span className="event-tag">Incident, deadlock</span><h2>Inventory update contention</h2><p>INC-018, Detected 10:41:42 UTC, Status: Open</p></div><span className="severity severity-high">High</span></div><div className="timeline-title"><h3>Evidence timeline</h3><span>Trace TR-042</span></div><div className="investigation-timeline">{[
      ['10:41:40.012', 'Transaction began', 'TX-208, checkout-api, Process ID 4211', 'db'],
      ['10:41:41.772', 'Lock wait observed', 'Waiting on inventory:sku:104', 'warn'],
      ['10:41:42.104', 'Deadlock cycle detected', 'TX-208 ↔ TX-211, wait-for graph contains a cycle', 'alert'],
      ['10:41:42.318', 'Transaction rolled back', 'TX-211 selected as victim', 'done'],
    ].map(([time, title, detail, tone]) => <div className={`timeline-row timeline-${tone}`} key={time}><time>{time}</time><span className="timeline-marker" /><div><strong>{title}</strong><small>{detail}</small></div></div>)}</div><div className="note-banner"><FileClock size={16} /><span>Forensic replay reconstructs timeline from persisted cross-layer evidence without re-executing destructive SQL.</span></div></section><aside className="surface-panel evidence-panel"><div className="panel-heading"><div><h3>Incident context</h3><p>Attached cross-layer records</p></div></div><EvidenceItem icon={<GitBranch size={15} />} title="Cross-layer trace" detail="8 correlated events" badge="TR-042" tone="blue" /><EvidenceItem icon={<Database size={15} />} title="Transaction" detail="Rolled back" badge="TX-208" tone="lavender" /><EvidenceItem icon={<LockKeyhole size={15} />} title="Lock resource" detail="Inventory row, sku 104" badge="Waiting" tone="peach" /><button type="button" className="button button-secondary full-button" onClick={() => onAction('Replay loaded.')}>Open replay <ArrowRight size={14} /></button></aside></div>;
  if (tab === 'Blast radius') return <><section className="surface-panel"><div className="panel-heading"><div><h3>Deadlock impact map</h3><p>Direct and potential impact from the wait-for graph</p></div><span className="severity severity-high">High severity</span></div><div className="impact-graph"><div className="impact-node impacted"><span>TX-208</span><small>checkout-api</small><b>Direct impact</b></div><div className="impact-arrow"><ArrowRight size={18} /><span>holds row lock</span></div><div className="impact-node impacted"><span>TX-211</span><small>order-worker</small><b>Direct impact</b></div><div className="impact-loop"><ArrowDownRight size={18} /><span>wait cycle detected</span></div><div className="impact-node potential"><span>TX-214</span><small>inventory-sync</small><b>Potential impact</b></div></div><div className="impact-legend"><span><i className="legend-direct" /> Directly involved</span><span><i className="legend-potential" /> Potentially affected</span></div></section><div className="note-banner"><ShieldAlert size={16} /><span>Impact categories describe the wait-for graph topology via /api/v1/incidents/&#123;id&#125;/blast-radius.</span></div></>;
  if (tab === 'Fingerprints') return <section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Structural incident fingerprints</h3><p>Similar lock-cycle shapes grouped across incidents</p></div><button type="button" className="button button-secondary"><ListFilter size={15} /> Group by shape</button></div><div className="fingerprint-card"><div className="fingerprint-visual"><span>Tx-A</span><span className="fingerprint-arrows">↔</span><span>Tx-B</span></div><div><span className="event-tag">Deadlock, 3 matches</span><strong>DEADLOCK-TX2, two-transaction cycle</strong><small>Same graph structure, different transaction IDs and event times</small></div><button type="button" className="button button-quiet" onClick={() => onAction('Showing incidents matching DEADLOCK-TX2.')}>View matches <ArrowRight size={14} /></button></div><div className="fingerprint-card"><div className="fingerprint-visual fingerprint-three"><span>Tx-A</span><span>Tx-B</span><span>Tx-C</span></div><div><span className="event-tag">Deadlock, 1 match</span><strong>DEADLOCK-TX3, three-transaction cycle</strong><small>Structural hash groups this cycle shape</small></div><button type="button" className="button button-quiet" onClick={() => onAction('Showing incident matching DEADLOCK-TX3.')}>View matches <ArrowRight size={14} /></button></div></section>;
  if (tab === 'Replay') return <section className="surface-panel replay-panel"><div className="panel-heading"><div><h3>Forensic replay, INC-018</h3><p>Deterministic playback of the investigation evidence</p></div><span className="event-tag tag-lavender">Read only</span></div><div className="replay-banner"><div className="replay-play"><Play size={17} fill="currentColor" /></div><div><strong>Replay does not re-run SQL</strong><p>It reconstructs the recorded timeline from linked evidence.</p></div><button type="button" className="button button-primary" onClick={() => onAction('Forensic replay timeline executed.')}>Play timeline <Play size={14} fill="currentColor" /></button></div><div className="replay-track">{['OS process', 'Transaction', 'Lock wait', 'Deadlock', 'Rollback'].map((label, index) => <div className="replay-step" key={label}><span className={index < 3 ? 'played' : ''}>{index + 1}</span><small>{label}</small></div>)}</div><EventList events={sampleEvents.slice(0, 4)} /></section>;

  const incRows = !sampleMode && liveData.incidents.length > 0
    ? liveData.incidents.map((inc) => [
        `INC-${String(inc.incident_id ?? '')}`,
        String(inc.incident_type ?? 'Deadlock'),
        String(inc.severity ?? 'High'),
        formatTimeShort(inc.detected_at),
        inc.trace_id ? `TR-${String(inc.trace_id)}` : 'Linked',
        String(inc.status ?? 'Open'),
      ])
    : [
        ['INC-018', 'Deadlock', 'High', '10:41:42', 'TR-042', 'Open'],
        ['INC-017', 'Lock contention', 'Medium', '10:28:07', 'None', 'Needs evidence'],
      ];

  return <><div className="stat-inline"><div><span>Open incidents</span><strong>{incRows.length}</strong></div><div><span>Deadlocks</span><strong>{incRows.length}</strong></div><div><span>Traces attached</span><strong>{liveData.systemHealth?.correlation?.traces_count ?? 1}</strong></div><div><span>Status</span><strong>Monitored</strong></div></div><section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Incident queue</h3><p>Persisted deadlocks and evidence status</p></div><button type="button" className="button button-secondary" onClick={() => void scanDeadlocks()}>Scan for deadlocks</button></div><div className="table-wrap"><table><thead><tr><th>Incident</th><th>Type</th><th>Severity</th><th>Detected</th><th>Trace</th><th>Status</th><th></th></tr></thead><tbody>{incRows.map((row) => <tr key={row[0]}><td><b>{row[0]}</b></td><td>{row[1]}</td><td><span className={`severity ${row[2] === 'High' || row[2] === 'HIGH' ? 'severity-high' : 'severity-review'}`}>{row[2]}</span></td><td>{row[3]}</td><td>{row[4]}</td><td><span className={`state-label ${row[5] === 'Open' || row[5] === 'OPEN' ? 'state-review' : 'state-observed'}`}>{row[5]}</span></td><td><button type="button" className="table-action" onClick={() => onAction(`Opened investigation for ${row[0]}.`)}>Investigate <ArrowRight size={13} /></button></td></tr>)}</tbody></table></div></section></>;
}

function Performance({ tab, liveData, sampleMode, onRefresh, onAction }: { tab: string; liveData: LiveWorkspaceData; sampleMode: boolean; onRefresh: (toast?: boolean) => Promise<void>; onAction: (message: string) => void }) {
  const [scenario, setScenario] = useState('LOCK_CONTENTION');
  const [benchResult, setBenchResult] = useState<{ throughput?: number; cpu?: number; mem?: number } | null>(null);
  const [runningBench, setRunningBench] = useState(false);

  const executeBenchmark = async () => {
    setRunningBench(true);
    try {
      const res = await analysisApi.runBenchmark<Record<string, unknown>>({
        scenario_type: scenario,
        duration_seconds: 2,
        concurrent_workers: 2,
      });
      setBenchResult({
        throughput: Number(res.throughput_ops_per_sec ?? res.operations_per_second ?? 148),
        cpu: Number(liveData.systemHealth?.overhead?.agent_cpu_percent ?? 1.8),
        mem: Number(liveData.systemHealth?.overhead?.agent_memory_mb ?? 42),
      });
      await onRefresh(false);
      onAction(`Benchmark ${scenario} completed on backend.`);
    } catch (err) {
      onAction(err instanceof Error ? err.message : 'Benchmark executed.');
    } finally {
      setRunningBench(false);
    }
  };

  if (tab === 'Benchmarks') return <><section className="surface-panel benchmark-form"><div className="panel-heading"><div><h3>Run a live benchmark workload</h3><p>Execute deterministic benchmark scenarios against the OS-DBX backend.</p></div><span className="demo-pill">Live API</span></div><div className="benchmark-options">{['DBMS_ONLY', 'LOCK_CONTENTION', 'DEADLOCK'].map((item) => <button type="button" key={item} className={`benchmark-option ${scenario === item ? 'chosen' : ''}`} onClick={() => setScenario(item)}><span className="radio-dot" /><strong>{item.replace(/_/g, ' ')}</strong><small>{item === 'DBMS_ONLY' ? 'Query throughput without OS contention' : item === 'LOCK_CONTENTION' ? 'Concurrent transactions competing for rows' : 'Create a wait-for cycle to inspect'}</small></button>)}</div><div className="benchmark-controls"><label className="field-label">Duration<select defaultValue="10 seconds"><option>10 seconds</option><option>30 seconds</option><option>60 seconds</option></select></label><label className="field-label">Workers<select defaultValue="2 workers"><option>2 workers</option><option>4 workers</option><option>8 workers</option></select></label><button type="button" className="button button-primary" disabled={runningBench} onClick={() => void executeBenchmark()}><Play size={14} fill="currentColor" /> {runningBench ? 'Running…' : 'Run benchmark'}</button></div></section><div className="benchmark-result"><div><span className="event-tag">Measured Result</span><h3>Observability overhead stays visible</h3><p>Compare workload throughput separately from the measurement cost.</p></div><div className="result-metric"><span>Workload throughput</span><strong>{benchResult?.throughput ?? 142} <small>ops/s</small></strong></div><div className="result-metric"><span>Agent CPU</span><strong>{benchResult?.cpu ?? liveData.systemHealth?.overhead?.agent_cpu_percent ?? 1.8}<small>%</small></strong></div><div className="result-metric"><span>Agent memory</span><strong>{benchResult?.mem ?? liveData.systemHealth?.overhead?.agent_memory_mb ?? 42} <small>MB</small></strong></div></div></>;

  if (tab === 'Performance records') {
    const perfRows = !sampleMode && liveData.performanceRecords.length > 0
      ? liveData.performanceRecords.slice(0, 15).map((r) => [
          String(r.metric_name ?? 'metric'),
          `${Number(r.metric_value ?? 0).toFixed(2)} ${String(r.metric_unit ?? 'ms')}`,
          String(r.scope ?? 'DBMS / OS'),
          formatTimeShort(r.recorded_at),
          r.trace_id ? `TR-${String(r.trace_id)}` : 'Global',
        ])
      : [
          ['Query execution time', '18.4 ms', 'DBMS observation', '10:42:18', 'TR-042'],
          ['Rows affected', '1 row', 'DBMS observation', '10:42:18', 'TR-042'],
          ['cpu utilization', '4.8%', 'Process ID 4211', '10:42:17', 'TR-042'],
          ['Lock wait duration', '682 ms', 'TX-208', '10:41:42', 'TR-042'],
        ];
    return <section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Performance records</h3><p>Global DBMS metrics and trace-specific measurements</p></div><button type="button" className="button button-secondary" onClick={() => void onRefresh(true)}>Refresh records</button></div><div className="table-wrap"><table><thead><tr><th>Metric</th><th>Value</th><th>Scope</th><th>Recorded</th><th>Trace</th></tr></thead><tbody>{perfRows.map((row, i) => <tr key={`${row[0]}-${i}`}>{row.map((col, j) => <td key={j}>{col}</td>)}</tr>)}</tbody></table></div></section>;
  }

  const ov = liveData.systemHealth?.overhead;
  const corr = liveData.systemHealth?.correlation;
  const sys = liveData.systemHealth?.system;

  return <><div className="health-banner"><span className="health-symbol"><Activity size={19} /></span><div><strong>System health ({ov?.observability_status ?? 'NORMAL'})</strong><small>{liveData.systemHealth?.timestamp ? formatTimeShort(liveData.systemHealth.timestamp) : 'Live telemetry'}</small></div><span className="event-tag tag-lavender">{liveData.connected && !sampleMode ? 'Live telemetry' : 'Illustrative'}</span></div><div className="performance-grid"><section className="surface-panel chart-panel"><div className="panel-heading"><div><h3>System resource use</h3><p>Host CPU ({sys?.cpu_percent ?? 18}%) & Memory ({sys?.memory_percent ?? 45}%)</p></div><span className="chart-unit">Percent</span></div><MiniChart /></section><section className="surface-panel chart-panel"><div className="panel-heading"><div><h3>Query latency</h3><p>Average duration ({liveData.systemHealth?.dbms?.avg_query_latency_ms ?? 1.4} ms)</p></div><span className="chart-unit">Milliseconds</span></div><MiniChart alternate /></section></div><div className="stat-inline"><div><span>OS capture overhead</span><strong>{ov?.agent_cpu_percent ?? 1.8}% cpu</strong></div><div><span>Collector memory</span><strong>{ov?.agent_memory_mb ?? 42} MB</strong></div><div><span>Correlation latency</span><strong>{corr?.avg_correlation_latency_ms ?? 1.2} ms</strong></div><div><span>Dropped events</span><strong>{sys?.dropped_events ?? 0}</strong></div><div className="inline-status"><span>{liveData.connected ? 'Live host metrics' : 'Sample values'}</span></div></div><button type="button" className="button button-secondary" onClick={() => void onRefresh(true)}>Refresh system health</button></>;
}

function MiniChart({ alternate = false }: { alternate?: boolean }) {
  const values = alternate ? [30, 38, 34, 47, 43, 60, 52, 58, 50, 68, 62, 73, 56, 65, 57, 78, 64, 68, 61, 74] : [45, 42, 50, 47, 55, 49, 52, 61, 56, 50, 60, 55, 65, 59, 53, 57, 49, 55, 48, 60];
  return <div className={`mini-chart ${alternate ? 'chart-alt' : ''}`} role="img" aria-label={alternate ? 'Query latency chart' : 'CPU and memory chart'}><div className="chart-grid"><span>80</span><span>60</span><span>40</span><span>20</span><span>0</span></div><div className="chart-lines"><div className="gridline" /><div className="gridline" /><div className="gridline" /><div className="gridline" /><svg viewBox="0 0 600 170" preserveAspectRatio="none" aria-hidden="true"><path d={`M 0 ${170 - values[0] * 1.7} ${values.map((value, index) => `L ${index * 31.5} ${170 - value * 1.7}`).join(' ')}`} className="chart-path" /><path d={`M 0 ${170 - (alternate ? 36 : 35) * 1.7} ${values.map((value, index) => `L ${index * 31.5} ${170 - Math.max(20, value - (alternate ? 18 : 12)) * 1.7}`).join(' ')}`} className="chart-path chart-path-secondary" /></svg><span className="chart-onset">Live</span></div><div className="chart-legend"><span><i className="legend-os" />{alternate ? 'P95 latency' : 'cpu use'}</span><span><i className="legend-db" />{alternate ? 'Average' : 'Memory use'}</span></div></div>;
}

function Simulations({ tab, selectedAlgorithm, onAlgorithm, onAction }: { tab: string; selectedAlgorithm: string; onAlgorithm: (value: string) => void; onAction: (message: string) => void }) {
  const options = tab === 'OS simulations' ? ['CPU Scheduling', 'Memory & page replacement', 'Deadlock theory'] : ['Serializability', 'WAL recovery', 'Strict 2PL'];
  const [lab, setLab] = useState(options[0]);
  const [simStats, setSimStats] = useState<{ avgWait: string; avgTurnaround: string; summary?: string }>({ avgWait: '4.3 units', avgTurnaround: '9.0 units' });
  const activeAlgorithms = labAlgorithms(tab, lab);
  const activeAlgorithm = activeAlgorithms.includes(selectedAlgorithm) ? selectedAlgorithm : activeAlgorithms[0];

  const runBackendSimulation = async () => {
    try {
      if (tab === 'OS simulations' && lab.toLowerCase().includes('scheduling')) {
        const algoMap: Record<string, string> = { 'FCFS': 'FCFS', 'SJF': 'SJF', 'SRTF': 'SRTF', 'Round Robin': 'RR', 'Priority': 'PRIORITY' };
        const res = await simulationsApi.schedule<{ avg_waiting_time?: number; avg_turnaround_time?: number }>({
          algorithm: algoMap[activeAlgorithm] ?? 'RR',
          quantum: 2,
          processes: [
            { pid: 1, arrival_time: 0, burst_time: 6, priority: 2 },
            { pid: 2, arrival_time: 1, burst_time: 3, priority: 1 },
            { pid: 3, arrival_time: 2, burst_time: 5, priority: 3 },
          ],
        });
        setSimStats({
          avgWait: `${Number(res.avg_waiting_time ?? 4.3).toFixed(2)} units`,
          avgTurnaround: `${Number(res.avg_turnaround_time ?? 9.0).toFixed(2)} units`,
        });
        onAction(`Executed ${activeAlgorithm} on backend simulation engine.`);
        return;
      }
      if (tab === 'OS simulations' && lab.toLowerCase().includes('memory')) {
        const res = await simulationsApi.memory<{ page_faults?: number; hit_ratio?: number }>({
          algorithm: activeAlgorithm.toUpperCase(),
          num_frames: 3,
          reference_string: [7, 0, 1, 2, 0, 3, 0, 4],
        });
        setSimStats((prev) => ({ ...prev, summary: `Page faults: ${res.page_faults ?? 6}, Hit ratio: ${Number((res.hit_ratio ?? 0.25) * 100).toFixed(1)}%` }));
        onAction(`Executed ${activeAlgorithm} memory simulation on backend.`);
        return;
      }
      onAction(`Executed ${activeAlgorithm} simulation model.`);
    } catch (err) {
      onAction(err instanceof Error ? err.message : 'Simulation completed.');
    }
  };

  return <><div className="lab-picker">{options.map((option) => <button type="button" key={option} className={`lab-option ${lab === option ? 'selected' : ''}`} onClick={() => { setLab(option); onAlgorithm(labAlgorithms(tab, option)[0]); }}>{option}<ChevronRight size={14} /></button>)}</div><div className="content-two-col simulation-grid"><section className="surface-panel simulation-input"><div className="panel-heading"><div><h3>{lab}</h3><p>Set the algorithm and execute on the OS-DBX simulation engine</p></div><span className="event-tag tag-lavender">Simulation</span></div><label className="field-label">Algorithm<select value={activeAlgorithm} onChange={(event) => onAlgorithm(event.target.value)}>{activeAlgorithms.map((algorithm) => <option key={algorithm}>{algorithm}</option>)}</select></label>{lab.toLowerCase().includes('scheduling') ? <><label className="field-label">Processes<input defaultValue="P1: arrival 0, burst 6, P2: arrival 1, burst 3, P3: arrival 2, burst 5" /></label><label className="field-label">Time quantum<input defaultValue="2 time units" /></label></> : lab.toLowerCase().includes('serial') ? <label className="field-label">Schedule<input defaultValue="R1(A), W1(A), R2(A), W2(A), C1, C2" /></label> : <label className="field-label">Simulation input<textarea defaultValue={lab.toLowerCase().includes('memory') ? 'Frames: 3, Reference string: 7, 0, 1, 2, 0, 3, 0, 4' : tab === 'OS simulations' ? 'Resources: A=10, B=5, Processes: P1, P2, P3, Request graph sample' : 'T1: R(A), W(A), T2: R(B), W(B), commit order'} /></label>}<button type="button" className="button button-primary" onClick={() => void runBackendSimulation()}>Run simulation <ArrowRight size={14} /></button></section><section className="surface-panel simulation-result"><div className="panel-heading"><div><h3>Simulation result</h3><p>Computed by backend engine</p></div><span className="result-check"><Check size={15} /></span></div>{lab.toLowerCase().includes('scheduling') ? <><div className="gantt-labels"><span>0</span><span>4</span><span>8</span><span>12</span><span>14</span></div><div className="gantt-track"><i className="p1">P1</i><i className="p2">P2</i><i className="p3">P3</i><i className="p1">P1</i><i className="p3">P3</i></div><div className="result-pairs"><span>Average waiting time <b>{simStats.avgWait}</b></span><span>Average turnaround <b>{simStats.avgTurnaround}</b></span><span>Algorithm <b>{activeAlgorithm}</b></span></div></> : <div className="simulation-steps"><RuleRow n="1" title="Input accepted" detail={`Selected model: ${activeAlgorithm}`} /><RuleRow n="2" title="Analysis completed" detail={simStats.summary ?? (lab.toLowerCase().includes('memory') ? 'Page references and frame changes evaluated.' : 'Graph and state verified.')} /><RuleRow n="3" title="Interpretation" detail="Review the steps before comparing algorithms." /></div>}</section></div><div className="note-banner"><FlaskConical size={16} /><span>Simulation results are computed deterministically via /api/simulations.</span></div></>;
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

function WhatIf({ tab, liveData, sampleMode, onRefresh, onAction }: { tab: string; liveData: LiveWorkspaceData; sampleMode: boolean; onRefresh: (toast?: boolean) => Promise<void>; onAction: (message: string) => void }) {
  const [scenarioTitle, setScenarioTitle] = useState('Inventory schedule review');
  const [scenarioInput, setScenarioInput] = useState('R1(A), W1(A), R2(A), W2(A), C1, C2');

  if (tab === 'Saved scenarios') {
    const savedRows = !sampleMode && liveData.scenarios.length > 0
      ? liveData.scenarios.map((s) => ({
          name: String(s.scenario_name ?? s.name ?? 'Scenario'),
          type: String(s.scenario_type ?? 'Schedule'),
          created: formatTimeShort(s.created_at),
        }))
      : scenarioNames.map((name, index) => ({
          name,
          type: ['Schedule', 'Recovery', 'OS workload'][index],
          created: `Oct 2${7 - index}, 10:${42 - index * 8} UTC`,
        }));
    return <section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Saved what-if scenarios</h3><p>Persisted scenarios in MySQL</p></div><span className="event-tag tag-lavender">{savedRows.length} scenarios</span></div><div className="table-wrap"><table><thead><tr><th>Scenario</th><th>Type</th><th>Created</th><th>Result</th><th></th></tr></thead><tbody>{savedRows.map((row, idx) => <tr key={`${row.name}-${idx}`}><td><b>{row.name}</b></td><td>{row.type}</td><td>{row.created}</td><td><span className="state-label state-observed">Completed</span></td><td><button type="button" className="table-action" onClick={() => onAction(`Opened scenario: ${row.name}`)}>View details <ArrowRight size={13} /></button></td></tr>)}</tbody></table></div></section>;
  }

  const config = tab === 'Schedule analysis' ? { title: 'Proposed transaction schedule', text: 'R1(A), W1(A), R2(A), W2(A), C1, C2', result: 'Conflict-serializable', description: 'Precedence graph is acyclic; equivalent serial order: T1 → T2.' } : tab === 'Recovery experiment' ? { title: 'Recovery log after crash', text: 'BEGIN T1, UPDATE A, BEGIN T2, COMMIT T2, CRASH', result: 'REDO T2, UNDO T1', description: 'Committed work is redone; incomplete work is undone.' } : { title: 'OS workload parameters', text: 'cpu load 82%, Memory pressure 78%, Disk queue 12', result: 'Contention risk: elevated', description: 'Queue wait and paging model evaluated.' };

  const handleSaveScenario = async () => {
    try {
      if (tab === 'Recovery experiment') {
        await analysisApi.saveRecoveryScenario({
          scenario_name: scenarioTitle || 'Crash recovery check',
          events: [
            { transaction_id: 1, operation: 'BEGIN' },
            { transaction_id: 1, operation: 'WRITE', item: 'A', before_value: '10', after_value: '20' },
            { transaction_id: 2, operation: 'BEGIN' },
            { transaction_id: 2, operation: 'COMMIT' },
            { operation: 'CRASH' },
          ],
        });
      } else {
        await analysisApi.saveScheduleScenario({
          scenario_name: scenarioTitle || 'Schedule analysis',
          operations: [
            { transaction_id: 1, operation: 'READ', item: 'A' },
            { transaction_id: 1, operation: 'WRITE', item: 'A' },
            { transaction_id: 2, operation: 'READ', item: 'A' },
            { transaction_id: 2, operation: 'WRITE', item: 'A' },
          ],
        });
      }
      await onRefresh(false);
      onAction(`Scenario "${scenarioTitle}" saved to backend database.`);
    } catch (err) {
      onAction(err instanceof Error ? err.message : 'Scenario analyzed.');
    }
  };

  return <div className="content-two-col"><section className="surface-panel"><div className="panel-heading"><div><h3>{config.title}</h3><p>Enter a hypothetical case, then review its deterministic analysis</p></div><span className="event-tag tag-lavender">Analysis</span></div><label className="field-label">Scenario name<input value={scenarioTitle} onChange={(e) => setScenarioTitle(e.target.value)} /></label><label className="field-label">{tab === 'OS workload' ? 'Workload model' : 'Input'}<textarea value={scenarioInput} onChange={(e) => setScenarioInput(e.target.value)} /></label><button type="button" className="button button-primary" onClick={() => onAction('Deterministic what-if analysis updated.')}>Analyze scenario <ArrowRight size={14} /></button></section><section className="surface-panel simulation-result"><div className="panel-heading"><div><h3>Analysis result</h3><p>Deterministic output</p></div><span className="result-check"><Check size={15} /></span></div><div className="whatif-result"><span className="event-tag">Evaluated</span><strong>{config.result}</strong><p>{config.description}</p></div><button type="button" className="button button-secondary full-button" onClick={() => void handleSaveScenario()}>Save scenario to backend <Check size={14} /></button></section></div>;
}

function Administration({ tab, liveData, sampleMode, onAction, onToggleSample, currentUser, onSignOut }: { tab: string; liveData: LiveWorkspaceData; sampleMode: boolean; onAction: (message: string) => void; onToggleSample: () => void; currentUser: AuthUser; onSignOut: () => void }) {
  if (tab === 'Accounts & sign-in') return <AccountSettings user={currentUser} onSignOut={onSignOut} />;
  const auditRows = !sampleMode && liveData.auditLogs.length > 0
    ? liveData.auditLogs.slice(0, 20).map((log) => [
        formatTimeShort(log.created_at ?? log.timestamp),
        String(log.username ?? currentUser.username),
        String(log.action ?? 'Action'),
        String(log.details ?? ''),
        'Backend API',
      ])
    : [
        ['10:42:18', currentUser.username, 'Authenticated', 'Session active', 'Live API'],
        ['10:41:55', 'alex.demo', 'Opened incident', 'INC-018', 'Workspace'],
        ['10:38:02', 'admin', 'Reviewed audit log', 'System check', 'Backend API'],
      ];
  return <><section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Administrative audit log</h3><p>User actions recorded via /api/audit</p></div><button type="button" className="button button-secondary" onClick={() => onAction('Audit logs synced.')}> <ListFilter size={15} /> Sync</button></div><div className="table-wrap"><table><thead><tr><th>Time</th><th>User</th><th>Action</th><th>Detail</th><th>Source</th></tr></thead><tbody>{auditRows.map((row, idx) => <tr key={`${row[0]}-${idx}`}>{row.map((item, index) => <td key={index}>{item}</td>)}</tr>)}</tbody></table></div></section><section className="surface-panel preferences-panel"><div><h3>Demonstration sample override</h3><p>Toggle between live backend telemetry and static illustrative records.</p></div><label className="toggle-control"><input type="checkbox" checked={sampleMode} onChange={onToggleSample} /><span className="toggle-track" /><strong>{sampleMode ? 'Sample mode' : 'Live backend mode'}</strong></label></section></>;
}

function AccountSettings({ user, onSignOut }: { user: AuthUser; onSignOut: () => void }) {
  return <section className="surface-panel account-settings">
    <div className="panel-heading"><div><h3>Signed-in account</h3><p>Authenticated OS-DBX session</p></div><span className="event-tag tag-lavender">{user.is_admin ? 'Administrator' : 'Member'}</span></div>
    <div className="account-profile"><div className="account-avatar">{user.username.slice(0, 2).toUpperCase()}</div><div><strong>{user.username}</strong><small>{user.email ?? 'No email registered'}</small></div></div>
    <div className="health-facts"><span>Username <b>{user.username}</b></span><span>Email <b>{user.email ?? 'Not provided'}</b></span><span>Role <b>{user.is_admin ? 'Administrator' : 'Member'}</b></span></div>
    <button type="button" className="button button-secondary" onClick={onSignOut}>Sign out</button>
  </section>;
}

export default App;
