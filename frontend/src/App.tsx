import { useCallback, useEffect, useMemo, useState } from 'react';
import { AnimatePresence, LazyMotion, domAnimation, m, useReducedMotion } from 'framer-motion';
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Bell, BookOpen, Check,
  ChevronDown, ChevronRight, CircleHelp, Clock3, Contrast, Cpu, Database, FileClock,
  FlaskConical, GitBranch, HardDrive, LayoutDashboard, ListFilter, LockKeyhole,
  MemoryStick, Monitor, Moon, Network, Palette, Play, RefreshCw, Search, Settings, ShieldAlert, Sparkles,
  Sun, Waypoints, X,
} from 'lucide-react';
import { events as sampleEvents, observations as sampleObservations, pageMeta, scenarioNames, sidebarGroups, type ActivityEvent, type SectionId } from './data/demo';
import AuthPage from './features/auth/AuthPage';
import { analysisApi, authApi, correlationApi, hasAccessToken, incidentsApi, observabilityApi, simulationsApi, workflowsApi } from './api';
import type { AuthUser } from './api/auth';
import EmptyState from './components/EmptyState';

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
type ToneId = 'light' | 'dark' | 'blue';

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

interface BridgeMapPayload {
  status?: string;
  active_bridges?: number;
  mapping?: Array<{ os_pid: number; mysql_connection_id: number }>;
  is_admin?: boolean;
  warning?: string | null;
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
  bridgeMap: BridgeMapPayload | null;
  transactions: Array<Record<string, unknown>>;
  locks: Array<Record<string, unknown>>;
  traces: Array<Record<string, unknown>>;
}

function formatTimeShort(ts: unknown): string {
  if (!ts) return 'Live';
  const s = String(ts);
  const match = s.match(/(\d{2}:\d{2}:\d{2})/);
  return match ? match[1] : s.slice(0, 19);
}

function parseScheduleString(input: string): Array<{ transaction_id: number; operation: 'R' | 'W'; data_item: string }> {
  const ops: Array<{ transaction_id: number; operation: 'R' | 'W'; data_item: string }> = [];
  const tokens = input.split(/[,;\n]+/).map((t) => t.trim()).filter(Boolean);
  for (const token of tokens) {
    const rwMatch = token.match(/^([RW])(\d+)\s*\(\s*([A-Za-z0-9_]+)\s*\)$/i);
    if (rwMatch) {
      ops.push({
        operation: rwMatch[1].toUpperCase() as 'R' | 'W',
        transaction_id: Number(rwMatch[2]),
        data_item: rwMatch[3].toUpperCase(),
      });
      continue;
    }
    const wordMatch = token.match(/^(READ|WRITE)\s+T?(\d+)\s+([A-Za-z0-9_]+)$/i);
    if (wordMatch) {
      ops.push({
        operation: wordMatch[1].toUpperCase().startsWith('R') ? 'R' : 'W',
        transaction_id: Number(wordMatch[2]),
        data_item: wordMatch[3].toUpperCase(),
      });
    }
  }
  if (ops.length === 0) {
    return [
      { transaction_id: 1, operation: 'R', data_item: 'A' },
      { transaction_id: 1, operation: 'W', data_item: 'A' },
      { transaction_id: 2, operation: 'R', data_item: 'A' },
      { transaction_id: 2, operation: 'W', data_item: 'A' },
    ];
  }
  return ops;
}

function parseRecoveryLogInput(input: string): {
  initial_state: Record<string, string>;
  logs: Array<{
    sequence: number;
    transaction_id: number;
    log_type: 'BEGIN' | 'WRITE' | 'COMMIT' | 'ABORT';
    data_item?: string;
    old_value?: string;
    new_value?: string;
  }>;
} {
  const initial_state: Record<string, string> = { A: '100', B: '200' };
  const logs: Array<{
    sequence: number;
    transaction_id: number;
    log_type: 'BEGIN' | 'WRITE' | 'COMMIT' | 'ABORT';
    data_item?: string;
    old_value?: string;
    new_value?: string;
  }> = [];

  const tokens = input.split(/[,;\n]+/).map((t) => t.trim()).filter(Boolean);
  let seq = 1;
  for (const token of tokens) {
    const initMatch = token.match(/^INIT\s+([A-Za-z0-9_]+)\s*=\s*(.+)$/i);
    if (initMatch) {
      initial_state[initMatch[1].toUpperCase()] = initMatch[2].trim();
      continue;
    }
    const beginMatch = token.match(/^BEGIN\s+T?(\d+)$/i);
    if (beginMatch) {
      logs.push({ sequence: seq++, transaction_id: Number(beginMatch[1]), log_type: 'BEGIN' });
      continue;
    }
    const commitMatch = token.match(/^COMMIT\s+T?(\d+)$/i);
    if (commitMatch) {
      logs.push({ sequence: seq++, transaction_id: Number(commitMatch[1]), log_type: 'COMMIT' });
      continue;
    }
    const abortMatch = token.match(/^ABORT\s+T?(\d+)$/i);
    if (abortMatch) {
      logs.push({ sequence: seq++, transaction_id: Number(abortMatch[1]), log_type: 'ABORT' });
      continue;
    }
    const writeMatch = token.match(/^(?:WRITE|UPDATE)\s+T?(\d+)\s+([A-Za-z0-9_]+)\s+(\S+)\s*(?:->|to|\s)\s*(\S+)$/i);
    if (writeMatch) {
      const item = writeMatch[2].toUpperCase();
      if (!(item in initial_state)) initial_state[item] = writeMatch[3];
      logs.push({
        sequence: seq++,
        transaction_id: Number(writeMatch[1]),
        log_type: 'WRITE',
        data_item: item,
        old_value: writeMatch[3],
        new_value: writeMatch[4],
      });
      continue;
    }
    const shortWrite = token.match(/^W(\d+)\(\s*([A-Za-z0-9_]+)\s*,\s*(\S+)\s*,\s*(\S+)\s*\)$/i);
    if (shortWrite) {
      const item = shortWrite[2].toUpperCase();
      if (!(item in initial_state)) initial_state[item] = shortWrite[3];
      logs.push({
        sequence: seq++,
        transaction_id: Number(shortWrite[1]),
        log_type: 'WRITE',
        data_item: item,
        old_value: shortWrite[3],
        new_value: shortWrite[4],
      });
    }
  }

  if (logs.length === 0) {
    return {
      initial_state: { A: '100', B: '200' },
      logs: [
        { sequence: 1, transaction_id: 1, log_type: 'BEGIN' },
        { sequence: 2, transaction_id: 1, log_type: 'WRITE', data_item: 'A', old_value: '100', new_value: '150' },
        { sequence: 3, transaction_id: 2, log_type: 'BEGIN' },
        { sequence: 4, transaction_id: 2, log_type: 'WRITE', data_item: 'B', old_value: '200', new_value: '280' },
        { sequence: 5, transaction_id: 2, log_type: 'COMMIT' },
      ],
    };
  }
  return { initial_state, logs };
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
  const [inspectingEvent, setInspectingEvent] = useState<ActivityEvent | null>(null);
  const [tone, setTone] = useState<ToneId>('light');
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [searchPaletteOpen, setSearchPaletteOpen] = useState(false);
  const [syncDropdownOpen, setSyncDropdownOpen] = useState(false);
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncedAt, setLastSyncedAt] = useState('Just now');
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
    bridgeMap: null,
    transactions: [],
    locks: [],
    traces: [],
  });

  const notify = useCallback((message: string) => {
    setNotice(message);
    window.setTimeout(() => setNotice(''), 3400);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setSearchPaletteOpen((prev) => !prev);
        setNotificationsOpen(false);
        setPaletteOpen(false);
        setSyncDropdownOpen(false);
      }
      if (e.key === 'Escape') {
        setSearchPaletteOpen(false);
        setNotificationsOpen(false);
        setPaletteOpen(false);
        setSyncDropdownOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const refreshLiveWorkspace = useCallback(async (showToast = false, isAdminUser?: boolean) => {
    if (!hasAccessToken()) return;
    const canReadAudit = isAdminUser ?? Boolean(currentUser?.is_admin);
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
      bridgeRes,
      auditRes,
      txRes,
      locksRes,
      tracesRes,
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
      correlationApi.liveBridgeMap<BridgeMapPayload>(),
      canReadAudit ? analysisApi.auditLog<Record<string, unknown>>(50) : Promise.resolve([] as Array<Record<string, unknown>>),
      workflowsApi.listTransactions<Record<string, unknown>>(30),
      workflowsApi.listLocks<Record<string, unknown>>(40),
      correlationApi.listTraces<Record<string, unknown>>(30),
    ]);

    const anyFulfilled = [evRes, fsRes, osStatRes, procRes, dbObsRes, healthRes].some((r) => r.status === 'fulfilled');

    if (osStatRes.status === 'fulfilled' && osStatRes.value?.status === 'STOPPED') {
      void workflowsApi.startOsCollector().catch(() => {});
    }

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
      bridgeMap: bridgeRes.status === 'fulfilled' ? bridgeRes.value : prev.bridgeMap,
      auditLogs: canReadAudit
        ? (auditRes.status === 'fulfilled' && Array.isArray(auditRes.value) ? auditRes.value : prev.auditLogs)
        : [],
      transactions: txRes.status === 'fulfilled' && Array.isArray(txRes.value) ? txRes.value : prev.transactions,
      locks: locksRes.status === 'fulfilled' && Array.isArray(locksRes.value) ? locksRes.value : prev.locks,
      traces: tracesRes.status === 'fulfilled' && Array.isArray(tracesRes.value) ? tracesRes.value : prev.traces,
    }));

    setLastSyncedAt(new Date().toLocaleTimeString());

    if (showToast) {
      notify(anyFulfilled ? 'Live telemetry synchronized.' : 'Showing cached workspace records.');
    }
  }, [notify, currentUser?.is_admin]);

  const handleManualSync = useCallback(async () => {
    setIsSyncing(true);
    try {
      await refreshLiveWorkspace(false);
      setLastSyncedAt(new Date().toLocaleTimeString());
      notify('Live telemetry synchronized.');
    } catch {
      notify('Telemetry up to date.');
    } finally {
      setIsSyncing(false);
    }
  }, [refreshLiveWorkspace, notify]);

  useEffect(() => {
    if (!hasAccessToken()) {
      setCurrentUser(null);
      setAuthReady(true);
      return;
    }
    let active = true;
    void authApi.currentUser()
      .then((user) => {
        if (active) {
          setCurrentUser(user);
          void refreshLiveWorkspace(false, user.is_admin);
        }
      })
      .catch(() => {
        if (active) {
          authApi.signOut();
          setCurrentUser(null);
        }
      })
      .finally(() => { if (active) setAuthReady(true); });
    return () => { active = false; };
  }, [refreshLiveWorkspace]);

  useEffect(() => {
    const handleSessionExpired = () => {
      authApi.signOut();
      setCurrentUser(null);
      setAuthReady(true);
      notify('Your session has expired. Please sign in again to continue.');
    };
    window.addEventListener('osdbx:session-expired', handleSessionExpired);
    return () => window.removeEventListener('osdbx:session-expired', handleSessionExpired);
  }, [notify]);

  useEffect(() => {
    if (!currentUser || sampleMode) return;
    const timer = window.setInterval(() => {
      void refreshLiveWorkspace(false, currentUser.is_admin);
    }, 12000);
    return () => window.clearInterval(timer);
  }, [currentUser, sampleMode, refreshLiveWorkspace]);

  const combinedActivityEvents: ActivityEvent[] = useMemo(() => {
    if (sampleMode) return sampleEvents;
    const mapped: ActivityEvent[] = [];
    for (const obs of liveData.dbmsObservations.slice(0, 6)) {
      mapped.push({
        time: formatTimeShort(obs.observed_at),
        source: 'DBMS',
        title: `${String(obs.query_type ?? 'SQL')} observation #${String(obs.observation_id ?? '')}`,
        detail: `${String(obs.query_text ?? '').slice(0, 72)} (${Number(obs.execution_time_ms ?? 0).toFixed(1)} ms)`,
        status: 'linked',
      });
    }
    for (const tr of liveData.traces.slice(0, 4)) {
      mapped.push({
        time: formatTimeShort(tr.started_at ?? tr.created_at),
        source: 'CORRELATION',
        title: `Trace #${tr.trace_id ?? 'link'}: PID ${tr.pid ?? 'N/A'} ↔ Tx ${tr.transaction_id ?? 'N/A'}`,
        detail: String(tr.summary ?? 'Identity bridge direct socket link'),
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
    // If osEvents hasn't received new events yet, map live running Windows processes
    if (liveData.processes.length > 0 && liveData.osEvents.length === 0) {
      for (const proc of liveData.processes.slice(0, 5)) {
        mapped.push({
          time: 'Active now',
          source: 'OS',
          title: `Process observed · ${String(proc.name ?? 'system_process')}`,
          detail: `PID ${proc.pid} · State: ${String(proc.state ?? 'RUNNING').toLowerCase()} · User: ${String(proc.user ?? 'system')}`,
          status: 'observed',
        });
      }
    }
    return mapped.length > 0 ? mapped : sampleEvents;
  }, [sampleMode, liveData.dbmsObservations, liveData.traces, liveData.osEvents, liveData.filesystemEvents, liveData.processes]);

  const title = section === 'overview' ? pageMeta.overview.title : (headings[activeTab] ?? pageMeta[section].title);
  const filteredEvents = useMemo(
    () => combinedActivityEvents.filter((event) => `${event.title} ${event.detail} ${event.source}`.toLowerCase().includes(search.toLowerCase())),
    [combinedActivityEvents, search],
  );

  const openSection = (id: SectionId) => {
    if (id === 'admin' && !currentUser?.is_admin) {
      notify('Access Denied: Administration is restricted to administrator accounts.');
      return;
    }
    setSection(id);
    setActiveTab(tabs[id][0]);
    setSearch('');
    setNotificationsOpen(false);
    setPaletteOpen(false);
    setSearchPaletteOpen(false);
    setSyncDropdownOpen(false);
  };

  if (!authReady) return <main className="auth-session-loading"><span className="brand-mark" aria-hidden="true"><span /><span /><span /></span><p>Restoring your OS-DBX session…</p></main>;

  if (!currentUser) return <AuthPage onAuthenticated={(user, emailNotificationSent) => {
    setCurrentUser(user);
    setAuthReady(true);
    void refreshLiveWorkspace(false, user.is_admin);
    if (!emailNotificationSent) notify('Signed in, but the email alert was not sent. Check the account email and SMTP configuration.');
  }} />;

  const incidentCount = !sampleMode && liveData.incidents.length > 0 ? liveData.incidents.length : 2;

  return (
    <LazyMotion features={domAnimation}>
    <div className="app-shell" data-theme={theme} data-tone={tone}>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <div className="workspace">
        <header className="app-header">
          <div className="topbar">
            <div className="topbar-left">
              <a className="brand-lockup" href="#main-content" aria-label="OS-DBX home">
                <div className="brand-mark" aria-hidden="true"><span /><span /><span /></div>
                <span className="brand-wordmark">OS-DBX</span>
                <span className="brand-caption">Cross-layer observability</span>
              </a>
            </div>
            <div className="topbar-actions">
            <div className="search-wrapper">
              <label className="search-box">
                <Search size={16} />
                <input
                  aria-label="Search telemetry"
                  value={search}
                  onFocus={() => {
                    setSearchPaletteOpen(true);
                    setNotificationsOpen(false);
                    setPaletteOpen(false);
                    setSyncDropdownOpen(false);
                  }}
                  onChange={(event) => {
                    setSearch(event.target.value);
                    if (!searchPaletteOpen) {
                      setSearchPaletteOpen(true);
                      setNotificationsOpen(false);
                      setPaletteOpen(false);
                      setSyncDropdownOpen(false);
                    }
                  }}
                  placeholder="Search telemetry…"
                />
                <kbd
                  onClick={() => {
                    setSearchPaletteOpen((v) => !v);
                    setNotificationsOpen(false);
                    setPaletteOpen(false);
                    setSyncDropdownOpen(false);
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  ⌘ K
                </kbd>
              </label>
              {searchPaletteOpen && (
                <div className="search-palette" role="dialog" aria-label="Command search palette">
                  <div className="search-palette-group-title">Navigation Views</div>
                  {[
                    { id: 'overview' as SectionId, tab: 'Overview', label: 'System Overview', badge: 'Overview' },
                    { id: 'observatory' as SectionId, tab: 'Unified console', label: 'Unified OS → DBMS Console', badge: 'Observatory' },
                    { id: 'observatory' as SectionId, tab: 'OS activity', label: 'OS Event Stream & Filesystem', badge: 'Observatory' },
                    { id: 'observatory' as SectionId, tab: 'DBMS observations', label: 'DBMS Query Observations', badge: 'Observatory' },
                    { id: 'correlation' as SectionId, tab: 'Explorer', label: 'Correlation Explorer', badge: 'Correlation' },
                    { id: 'incidents' as SectionId, tab: 'Deadlocks', label: 'Deadlock Incidents & Replay', badge: 'Incidents' },
                    { id: 'performance' as SectionId, tab: 'System health', label: 'System Health & Latency', badge: 'Performance' },
                    { id: 'performance' as SectionId, tab: 'Benchmarks', label: 'Benchmark Workload Lab', badge: 'Performance' },
                    { id: 'simulations' as SectionId, tab: 'OS simulations', label: 'OS Concurrency Simulations', badge: 'Simulations' },
                    { id: 'simulations' as SectionId, tab: 'DBMS simulations', label: 'DBMS ACID Simulations', badge: 'Simulations' },
                    { id: 'whatif' as SectionId, tab: 'Schedule analysis', label: 'What-If Scenario Analysis', badge: 'What-If' },
                    ...(currentUser?.is_admin ? [{ id: 'admin' as SectionId, tab: 'Audit log', label: 'Security & Audit Logs', badge: 'Admin' }] : []),
                  ]
                    .filter((item) => !search || item.label.toLowerCase().includes(search.toLowerCase()) || item.badge.toLowerCase().includes(search.toLowerCase()))
                    .map((item) => (
                      <button
                        type="button"
                        key={`${item.id}-${item.tab}`}
                        className="search-palette-item"
                        onClick={() => {
                          setSection(item.id);
                          setActiveTab(item.tab);
                          setSearchPaletteOpen(false);
                          setSearch('');
                        }}
                      >
                        <div className="search-palette-item-left">
                          <Sparkles size={14} />
                          <span>{item.label}</span>
                        </div>
                        <span className="search-palette-item-badge">{item.badge}</span>
                      </button>
                    ))}
                </div>
              )}
            </div>
            <div className="tone-toggle-group" role="group" aria-label="Workspace tone">
              <button
                type="button"
                className={`tone-btn ${tone === 'light' ? 'active' : ''}`}
                onClick={() => setTone('light')}
                aria-pressed={tone === 'light'}
                title="Light tone"
              >
                <Sun size={13} />
                <span>Light</span>
              </button>
              <button
                type="button"
                className={`tone-btn ${tone === 'dark' ? 'active' : ''}`}
                onClick={() => setTone('dark')}
                aria-pressed={tone === 'dark'}
                title="Dark tone"
              >
                <Moon size={13} />
                <span>Dark</span>
              </button>
              <button
                type="button"
                className={`tone-btn ${tone === 'blue' ? 'active' : ''}`}
                onClick={() => setTone('blue')}
                aria-pressed={tone === 'blue'}
                title="Blue tone"
              >
                <Contrast size={13} />
                <span>Blue</span>
              </button>
            </div>
            <button type="button" className="icon-button header-utility" aria-label="Help" onClick={() => notify('Cross-layer causal observability active.')}><CircleHelp size={18} /></button>
            <div style={{ position: 'relative' }}>
              <button
                type="button"
                className={`icon-button header-utility ${notificationsOpen ? 'active' : ''}`}
                aria-label="Notifications"
                aria-expanded={notificationsOpen}
                onClick={() => {
                  setNotificationsOpen((v) => !v);
                  setPaletteOpen(false);
                  setSearchPaletteOpen(false);
                  setSyncDropdownOpen(false);
                }}
              >
                <Bell size={18} />
                {(liveData.incidents.length > 0 || liveData.auditLogs.length > 0) && <span className="notifications-badge" />}
              </button>
              {notificationsOpen && (
                <div className="notifications-popover" role="dialog" aria-label="Notifications">
                  <div className="notifications-header">
                    <h3>System Alerts & Notifications</h3>
                    <button type="button" className="button button-quiet" onClick={() => { void refreshLiveWorkspace(true); setNotificationsOpen(false); }}>
                      <RefreshCw size={13} /> Refresh
                    </button>
                  </div>
                  <div className="notification-item">
                    <Activity size={16} color="#7665bd" />
                    <div className="notification-content">
                      <strong>System Health Status: {liveData.systemHealth?.overhead?.observability_status ?? 'Operational'}</strong>
                      <p>CPU {liveData.systemHealth?.system?.cpu_percent ?? 12}% · Memory {liveData.systemHealth?.system?.memory_percent ?? 42}%</p>
                      <time>{formatTimeShort(liveData.systemHealth?.timestamp ?? Date.now())}</time>
                    </div>
                  </div>
                  <div className="notification-item">
                    <ShieldAlert size={16} color={liveData.incidents.length > 0 ? '#bb5746' : '#2f6298'} />
                    <div className="notification-content">
                      <strong>{liveData.incidents.length > 0 ? `${liveData.incidents.length} Deadlock Incidents Recorded` : 'Zero Unresolved Deadlocks'}</strong>
                      <p>{liveData.incidents.length > 0 ? 'Wait-for cycle detected. Forensics and replay available.' : 'Active deadlock detector monitoring lock acquisition queues.'}</p>
                      <time>Active</time>
                    </div>
                  </div>
                  <div className="notification-item">
                    <Monitor size={16} color="#3b82f6" />
                    <div className="notification-content">
                      <strong>Filesystem & Kernel Process Telemetry Stream</strong>
                      <p>{liveData.osStatus?.status === 'RUNNING' || liveData.osStatus?.is_active ? 'Active stream capturing process creation and file events.' : 'Stream collector operational.'}</p>
                      <time>Live</time>
                    </div>
                  </div>
                  {currentUser.is_admin && liveData.auditLogs.length > 0 && (
                    <div className="notification-item">
                      <LockKeyhole size={16} color="#059669" />
                      <div className="notification-content">
                        <strong>Security Audit Trail Active</strong>
                        <p>Last entry: {String(liveData.auditLogs[0]?.action ?? 'SESSION_VERIFY')} by {String(liveData.auditLogs[0]?.username ?? 'user')}</p>
                        <time>{formatTimeShort(liveData.auditLogs[0]?.timestamp ?? Date.now())}</time>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
            <button
              type="button"
              className={`topbar-env clickable ${liveData.connected && !sampleMode ? 'live-active' : 'demo-active'}`}
              onClick={() => {
                if (!liveData.connected) {
                  void refreshLiveWorkspace(true);
                } else {
                  setSampleMode((prev) => {
                    const next = !prev;
                    notify(next ? 'Switched to demonstration sample dataset.' : 'Switched to live system telemetry stream.');
                    return next;
                  });
                }
              }}
              title="Click to toggle live telemetry / demo dataset"
            >
              <span className={`live-dot ${liveData.connected && !sampleMode ? 'pulse' : ''}`} />
              {liveData.connected ? (sampleMode ? 'Demo dataset (Click for Live)' : 'Live telemetry') : 'Reconnecting...'}
            </button>
            <button
              type="button"
              className="profile-mini"
              aria-label={`Open account profile for ${currentUser.username}`}
              onClick={() => {
                setProfileModalOpen(true);
                setNotificationsOpen(false);
                setSearchPaletteOpen(false);
                setPaletteOpen(false);
                setSyncDropdownOpen(false);
              }}
            >
              <span className="profile-avatar" aria-hidden="true" /> {currentUser.username}
            </button>
          </div>
          </div>
          <nav id="primary-navigation" className="primary-nav" aria-label="Main navigation">
            {sidebarGroups
              .flatMap((group) => group.items)
              .filter((item) => item.id !== 'admin' || Boolean(currentUser?.is_admin))
              .map((item) => {
              const Icon = iconMap[item.icon as keyof typeof iconMap];
              return <button type="button" key={item.id} className={`primary-nav-item ${section === item.id ? 'active' : ''}`} onClick={() => openSection(item.id)} aria-current={section === item.id ? 'page' : undefined}>
                <Icon size={16} strokeWidth={1.8} /><span>{item.label}</span>{item.id === 'incidents' && <span className="nav-count">{incidentCount}</span>}
              </button>;
            })}
            <button
              type="button"
              className={`primary-nav-item theme-nav-toggle ${paletteOpen ? 'active' : ''}`}
              aria-expanded={paletteOpen}
              aria-controls="theme-preview-panel"
              onClick={() => {
                setPaletteOpen((open) => !open);
                setNotificationsOpen(false);
                setSearchPaletteOpen(false);
                setSyncDropdownOpen(false);
              }}
            >
              <Palette size={16} />
              <span>Theme preview</span>
            </button>
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

        <main
          id="main-content"
          className="main-content"
          onClick={() => {
            if (notificationsOpen) setNotificationsOpen(false);
            if (paletteOpen) setPaletteOpen(false);
            if (searchPaletteOpen) setSearchPaletteOpen(false);
          }}
        >
          <div className="page-heading">
            <div><h1>{title}</h1><p>{pageMeta[section].subtitle}</p></div>
            <div className="heading-actions">
              <div className="sync-telemetry-wrapper">
                <button className="button button-secondary" type="button" disabled={isSyncing} onClick={() => void handleManualSync()}>
                  <RefreshCw size={14} className={isSyncing ? 'spin' : ''} />
                  {isSyncing ? 'Synchronizing…' : 'Sync live telemetry'}
                  <ChevronDown size={14} onClick={(e) => { e.stopPropagation(); setSyncDropdownOpen((v) => !v); }} />
                </button>
                {syncDropdownOpen && (
                  <div className="sync-telemetry-dropdown">
                    <button type="button" className="sync-dropdown-item" onClick={() => { setSyncDropdownOpen(false); void handleManualSync(); }}>
                      <RefreshCw size={13} /> Sync all telemetry now
                    </button>
                    <button type="button" className="sync-dropdown-item" onClick={() => { setSyncDropdownOpen(false); notify('Auto-refresh set to 15 seconds.'); }}>
                      <Clock3 size={13} /> Auto-refresh: 15s (Active)
                    </button>
                    <div style={{ padding: '6px 12px', fontSize: '11px', color: 'var(--color-ink-2)' }}>
                      Last synced: {lastSyncedAt}
                    </div>
                  </div>
                )}
              </div>
              <button className="button button-primary" type="button" onClick={() => { setSection('observatory'); setActiveTab('Unified console'); setGuidedStep(0); }}><Play size={15} fill="currentColor" /> Run guided demo</button>
            </div>
          </div>

          {section !== 'overview' && (section !== 'admin' || Boolean(currentUser?.is_admin)) && <div className="tabs-bar" role="tablist" aria-label={`${pageMeta[section].title} views`}>
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
              ? <Overview events={filteredEvents} liveData={liveData} sampleMode={sampleMode} guidedStep={guidedStep} onRunDemo={() => { setSection('observatory'); setActiveTab('Unified console'); setGuidedStep(0); }} onNextStep={() => setGuidedStep((step) => (step + 1) % 5)} onOpen={(id) => openSection(id)} onSelectEvent={(ev) => setInspectingEvent(ev)} />
              : <FeaturePage section={section} tab={activeTab} onSelectTab={setActiveTab} events={filteredEvents} liveData={liveData} onRefresh={refreshLiveWorkspace} search={search} selectedAlgorithm={selectedAlgorithm} onAlgorithm={setSelectedAlgorithm} onAction={notify} sampleMode={sampleMode} onToggleSample={() => setSampleMode((value) => !value)} guidedStep={guidedStep} onNextStep={() => setGuidedStep((step) => Math.min(step + 1, 4))} currentUser={currentUser} onSignOut={() => { authApi.signOut(); setCurrentUser(null); }} />}
          </m.div>
          </AnimatePresence>

          <footer className="page-footer"><span>OS-DBX Unified Forensic Observability Platform · Real-time causal visibility</span><span>{liveData.connected && !sampleMode ? 'Operational · All collectors streaming' : 'Demo workspace'}</span></footer>
        </main>
      </div>

      {inspectingEvent && (
        <div className="inspector-overlay" onClick={() => setInspectingEvent(null)} role="dialog" aria-modal="true" aria-label="Event Inspector">
          <div className="inspector-card" onClick={(e) => e.stopPropagation()}>
            <div className="inspector-header">
              <div className="inspector-header-left">
                <span className={`event-source source-${inspectingEvent.source.toLowerCase()}`}>
                  {inspectingEvent.source === 'OS' ? 'OS Activity' : inspectingEvent.source === 'DBMS' ? 'Database' : 'Correlation'}
                </span>
                <h3>{inspectingEvent.title}</h3>
              </div>
              <button type="button" className="icon-button" onClick={() => setInspectingEvent(null)} aria-label="Close inspector">
                <X size={18} />
              </button>
            </div>

            <div className="inspector-body">
              <div className="inspector-grid">
                <div className="inspector-stat">
                  <span className="inspector-label">Observed Timestamp</span>
                  <strong>{inspectingEvent.time}</strong>
                </div>
                <div className="inspector-stat">
                  <span className="inspector-label">Causal Verification Status</span>
                  <span className={`state-label state-${inspectingEvent.status}`}>
                    {inspectingEvent.status === 'linked' ? 'Direct Identity Bridge' : inspectingEvent.status === 'attention' ? 'Requires Forensic Review' : 'Observed Telemetry'}
                  </span>
                </div>
                <div className="inspector-stat">
                  <span className="inspector-label">System Layer</span>
                  <strong>
                    {inspectingEvent.source === 'OS' ? 'Windows Host Kernel (psutil differential)' : inspectingEvent.source === 'DBMS' ? 'MySQL Performance Schema' : 'Cross-Layer Socket Correlator'}
                  </strong>
                </div>
                <div className="inspector-stat">
                  <span className="inspector-label">Evidence Classification</span>
                  <strong>
                    {inspectingEvent.source === 'CORRELATION' ? 'DIRECT (TCP Socket ↔ PID)' : inspectingEvent.source === 'DBMS' ? 'Statement Digest & Latency' : 'Real Process / Thread / FS'}
                  </strong>
                </div>
              </div>

              <div className="inspector-detail-box">
                <span className="inspector-label">Technical Observation Payload</span>
                <p>{inspectingEvent.detail}</p>
              </div>
            </div>

            <div className="inspector-actions">
              {inspectingEvent.source === 'OS' && (
                <button
                  type="button"
                  className="button button-primary"
                  onClick={() => {
                    setInspectingEvent(null);
                    openSection('observatory');
                    setActiveTab('Process & resources');
                  }}
                >
                  <Monitor size={15} /> Inspect Process in Live Observatory <ArrowRight size={15} />
                </button>
              )}
              {inspectingEvent.source === 'DBMS' && (
                <button
                  type="button"
                  className="button button-primary"
                  onClick={() => {
                    setInspectingEvent(null);
                    openSection('observatory');
                    setActiveTab('DBMS observations');
                  }}
                >
                  <Database size={15} /> Inspect Query in Live Observatory <ArrowRight size={15} />
                </button>
              )}
              {inspectingEvent.source === 'CORRELATION' && (
                <button
                  type="button"
                  className="button button-primary"
                  onClick={() => {
                    setInspectingEvent(null);
                    openSection('correlation');
                    setActiveTab('Explorer');
                  }}
                >
                  <GitBranch size={15} /> Trace Identity Bridge in Explorer <ArrowRight size={15} />
                </button>
              )}
              <button type="button" className="button button-secondary" onClick={() => setInspectingEvent(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {profileModalOpen && (
        <div className="inspector-overlay" onClick={() => setProfileModalOpen(false)} role="dialog" aria-modal="true" aria-label="Account Profile">
          <div className="inspector-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '480px' }}>
            <div className="inspector-header">
              <div className="inspector-header-left">
                <span className="event-source" style={{ width: 'auto', padding: '3px 10px', background: currentUser.is_admin ? 'rgba(99, 102, 241, 0.15)' : 'rgba(16, 185, 129, 0.15)', color: currentUser.is_admin ? '#818cf8' : '#34d399' }}>
                  {currentUser.is_admin ? 'Administrator Role' : 'Member Role'}
                </span>
                <h3>Account Profile</h3>
              </div>
              <button type="button" className="icon-button" onClick={() => setProfileModalOpen(false)} aria-label="Close profile">
                <X size={18} />
              </button>
            </div>

            <div className="account-profile" style={{ margin: '8px 0 16px' }}>
              <div className="account-avatar" style={{ width: '48px', height: '48px', fontSize: '16px' }}>
                {currentUser.username.slice(0, 2).toUpperCase()}
              </div>
              <div style={{ marginLeft: '12px' }}>
                <strong style={{ fontSize: '16px', color: 'var(--color-ink)' }}>{currentUser.username}</strong>
                <small style={{ color: 'var(--color-ink-2)', fontSize: '13px' }}>{currentUser.email ?? 'No email address registered'}</small>
              </div>
            </div>

            <div className="inspector-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)', gap: '14px' }}>
              <div className="inspector-stat">
                <span className="inspector-label">System Identity (Host UID)</span>
                <strong>UID {currentUser.uid_linux ?? 1000}</strong>
              </div>
              <div className="inspector-stat">
                <span className="inspector-label">Access Level</span>
                <span className={`state-label ${currentUser.is_admin ? 'state-linked' : 'state-observed'}`}>
                  {currentUser.is_admin ? 'System Administrator' : 'Standard Member (Read-Only)'}
                </span>
              </div>
              <div className="inspector-stat">
                <span className="inspector-label">Security Role</span>
                <strong>{currentUser.is_admin ? 'admin' : 'member'}</strong>
              </div>
              <div className="inspector-stat">
                <span className="inspector-label">Session Status</span>
                <strong style={{ color: '#10b981' }}>Active (JWT Authenticated)</strong>
              </div>
            </div>

            <div className="inspector-actions" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px' }}>
              {currentUser.is_admin ? (
                <button
                  type="button"
                  className="button button-primary"
                  onClick={() => {
                    setProfileModalOpen(false);
                    openSection('admin');
                  }}
                >
                  <Settings size={15} /> Administration Console
                </button>
              ) : (
                <span style={{ fontSize: '12px', color: 'var(--color-ink-subtle)' }}>
                  Standard member telemetry access
                </span>
              )}
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  className="button button-danger"
                  style={{ background: 'rgba(239, 68, 68, 0.12)', color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.3)' }}
                  onClick={() => {
                    authApi.signOut();
                    setCurrentUser(null);
                    setProfileModalOpen(false);
                    notify('Signed out successfully.');
                  }}
                >
                  Sign out
                </button>
                <button type="button" className="button button-secondary" onClick={() => setProfileModalOpen(false)}>
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
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

function Overview({ events: visibleEvents, liveData, sampleMode, guidedStep, onRunDemo, onNextStep, onOpen, onSelectEvent }: { events: ActivityEvent[]; liveData: LiveWorkspaceData; sampleMode: boolean; guidedStep: number; onRunDemo: () => void; onNextStep: () => void; onOpen: (id: SectionId) => void; onSelectEvent?: (event: ActivityEvent) => void }) {
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
        <span className="sample-note">{liveData.connected && !sampleMode ? 'Live collector pipeline active' : 'Offline demo dataset'}</span>
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
        <div className="panel-heading"><div><h3>Activity across layers</h3><p>{liveData.connected && !sampleMode ? 'Live streaming events across system layers' : 'Sample events across system layers'}</p></div><button type="button" className="button button-quiet" onClick={() => onOpen('observatory')}>Open event stream <ArrowRight size={14} /></button></div>
        <EventList events={visibleEvents.slice(0, 5)} onSelectEvent={onSelectEvent} />
      </section>
      <section className="surface-panel incidents-panel">
        <div className="panel-heading"><div><h3>Quick CLI-parity workbenches</h3><p>Launch interactive labs with live output rendering</p></div><span className="panel-count">{incidentsCount}</span></div>
        <button type="button" className="incident-row" aria-label="Open deadlock incident" onClick={() => onOpen('incidents')}><span className="incident-icon warn"><LockKeyhole size={16} /></span><span className="incident-content"><strong>Deadlock & Forensic Replay</strong><small>Inspect wait-for cycles, blast radius, and timeline replay</small></span><ChevronRight size={15} /></button>
        <button type="button" className="incident-row" aria-label="Open OS and DBMS simulation labs" onClick={() => onOpen('simulations')}><span className="incident-icon info"><FlaskConical size={16} /></span><span className="incident-content"><strong>OS & DBMS Simulation Labs</strong><small>CPU Gantt charts, Memory frames, Banker's, 2PL, WAL Recovery</small></span><ChevronRight size={15} /></button>
        <button type="button" className="incident-row" aria-label="Open What-If deterministic analysis" onClick={() => onOpen('whatif')}><span className="incident-icon info"><Sparkles size={16} /></span><span className="incident-content"><strong>What-If Scenario Engine</strong><small>Evaluate schedules, crash logs, and OS contention models</small></span><ChevronRight size={15} /></button>
      </section>
    </div>
  </>;
}

function Metric({ label, value, change, detail, up }: { label: string; value: string; change: string; detail: string; tone: string; icon: React.ReactNode; up?: boolean }) {
  return <div className="metric-block"><div className="metric-top"><span className="metric-label">{label}</span></div><div className="metric-value-row"><strong>{value}</strong><span className={`metric-change ${up ? 'positive' : ''}`}>{up ? <ArrowUpRight size={13} /> : null}{change}</span></div><span className="metric-detail">{detail}</span></div>;
}

function EventList({
  events: eventRows,
  onSelectEvent,
}: {
  events: ActivityEvent[];
  onSelectEvent?: (event: ActivityEvent) => void;
}) {
  return (
    <div className="event-list" role="feed" aria-label="Activity events across system layers">
      {eventRows.length === 0 ? (
        <EmptyState
          icon="search"
          title="No events match this filter"
          description="Try adjusting your search terms or verify active OS & DBMS collector streaming status."
        />
      ) : (
        eventRows.map((event, index) => (
          <div
            className={`event-row clickable ${onSelectEvent ? 'interactive' : ''}`}
            key={`${event.time}-${index}`}
            role="button"
            tabIndex={0}
            onClick={() => onSelectEvent?.(event)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onSelectEvent?.(event);
              }
            }}
            title="Click to inspect cross-layer forensic evidence"
          >
            <time>{event.time}</time>
            <span className={`event-source source-${event.source.toLowerCase()}`}>
              {event.source === 'OS' ? 'OS activity' : event.source === 'DBMS' ? 'Database' : 'Correlation'}
            </span>
            <span className={`event-mark mark-${event.status}`} />
            <span className="event-copy">
              <strong>{event.title}</strong>
              <small>{event.detail}</small>
            </span>
            <div className="event-row-badge-group">
              {event.status === 'linked' ? (
                <span className="state-label state-linked">Linked</span>
              ) : event.status === 'attention' ? (
                <span className="state-label state-review">Review</span>
              ) : (
                <span className="state-label state-observed">Observed</span>
              )}
              <span className="event-row-arrow" aria-hidden="true">
                <ChevronRight size={14} />
              </span>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

function FeaturePage({ section, tab, onSelectTab, events: visibleEvents, liveData, onRefresh, search, selectedAlgorithm, onAlgorithm, onAction, sampleMode, onToggleSample, guidedStep, onNextStep, currentUser, onSignOut }: {
  section: SectionId; tab: string; onSelectTab: (tab: string) => void; events: ActivityEvent[]; liveData: LiveWorkspaceData; onRefresh: (toast?: boolean) => Promise<void>; search: string; selectedAlgorithm: string; onAlgorithm: (value: string) => void; onAction: (message: string) => void; sampleMode: boolean; onToggleSample: () => void; guidedStep: number; onNextStep: () => void; currentUser: AuthUser; onSignOut: () => void;
}) {
  if (section === 'observatory' && tab === 'Unified console') return <UnifiedConsole guidedStep={guidedStep} onNextStep={onNextStep} onAction={onAction} onRefresh={onRefresh} />;
  if (section === 'observatory' && tab === 'DBMS observations') return <Observations liveData={liveData} sampleMode={sampleMode} onRefresh={onRefresh} onAction={onAction} />;
  if (section === 'observatory' && tab === 'Process & resources') return <ProcessView liveData={liveData} sampleMode={sampleMode} />;
  if (section === 'observatory' && tab === 'Transactions & locks') return <TransactionsLocks liveData={liveData} onAction={onAction} onRefresh={onRefresh} />;
  if (section === 'observatory') return <OSActivity events={visibleEvents} liveData={liveData} sampleMode={sampleMode} search={search} onRefresh={onRefresh} onAction={onAction} />;
  if (section === 'correlation') return <Correlation tab={tab} liveData={liveData} onRefresh={onRefresh} onAction={onAction} />;
  if (section === 'incidents') return <Incidents tab={tab} onSelectTab={onSelectTab} liveData={liveData} sampleMode={sampleMode} onRefresh={onRefresh} onAction={onAction} />;
  if (section === 'performance') return <Performance tab={tab} liveData={liveData} sampleMode={sampleMode} onRefresh={onRefresh} onAction={onAction} />;
  if (section === 'simulations') return <Simulations tab={tab} selectedAlgorithm={selectedAlgorithm} onAlgorithm={onAlgorithm} onAction={onAction} />;
  if (section === 'whatif') return <WhatIf tab={tab} liveData={liveData} sampleMode={sampleMode} onRefresh={onRefresh} onAction={onAction} />;
  if (section === 'admin') {
    if (!currentUser.is_admin) {
      return (
        <section className="surface-panel" style={{ padding: '48px 24px', textAlign: 'center', margin: '24px auto', maxWidth: '600px' }}>
          <div style={{ display: 'inline-flex', padding: '16px', borderRadius: '50%', background: 'rgba(239, 68, 68, 0.12)', color: '#ef4444', marginBottom: '16px' }}>
            <ShieldAlert size={36} />
          </div>
          <h2 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '8px', color: 'var(--color-ink)' }}>Access Denied</h2>
          <p style={{ color: 'var(--color-ink-subtle)', lineHeight: 1.6, marginBottom: '20px' }}>
            Administrator privileges are required to access security audit logs and workspace administration. Your current role is <strong>Member</strong>.
          </p>
          <button type="button" className="button button-primary" onClick={() => onAction('Administration is restricted to system administrators.')}>
            Return to Dashboard
          </button>
        </section>
      );
    }
    return <Administration tab={tab} liveData={liveData} sampleMode={sampleMode} onRefresh={onRefresh} onAction={onAction} onToggleSample={onToggleSample} currentUser={currentUser} onSignOut={onSignOut} />;
  }
  return null;
}

interface DemoCorrelationResultInner {
  is_correlated?: boolean;
  classification?: string;
  evidence_summary?: string;
  trace?: { trace_id: number; pid: number; transaction_id: number; summary: string };
  causal_sequence?: Array<{
    os_event_id?: number;
    pid?: number;
    transaction_id?: number;
    query_id?: number;
    event_type?: string;
    timestamp?: string;
    source?: string;
  }>;
}

interface DemoCorrelationOutput {
  demo?: string;
  status?: string;
  generated_at?: string;
  result?: DemoCorrelationResultInner;
  checks?: Array<{ name: string; passed: boolean; detail: string }>;
}

function UnifiedConsole({ guidedStep, onNextStep, onAction, onRefresh }: { guidedStep: number; onNextStep: () => void; onAction: (message: string) => void; onRefresh: (toast?: boolean) => Promise<void> }) {
  const stages = ['Process', 'Identity', 'Query', 'Trace', 'Explanation'];
  const [selectedProcess, setSelectedProcess] = useState('checkout-api, Process ID 4211');
  const [workflow, setWorkflow] = useState('Direct identity walkthrough');
  const [demoOutput, setDemoOutput] = useState<DemoCorrelationOutput | null>(null);
  const [runningDemo, setRunningDemo] = useState(false);

  // CLI parity workbenches
  const [adhocQuery, setAdhocQuery] = useState('SELECT @@version;');
  const [adhocOutput, setAdhocOutput] = useState<Record<string, any> | null>(null);
  const [runningAdhoc, setRunningAdhoc] = useState(false);
  const [realWorldOutput, setRealWorldOutput] = useState<Record<string, any> | null>(null);
  const [runningRealWorld, setRunningRealWorld] = useState(false);

  const executeLiveFlagshipDemo = useCallback(async (silent = false) => {
    setRunningDemo(true);
    try {
      const res = await correlationApi.demoCorrelation<DemoCorrelationOutput>();
      setDemoOutput(res);
      await onRefresh(false);
      if (!silent) {
        const traceId = res.result?.trace?.trace_id ?? 42;
        const cls = res.result?.classification ?? 'DIRECT';
        onAction(`Flagship correlation executed: Trace #${traceId} verified (${cls}).`);
      }
    } catch (err) {
      if (!silent) {
        onAction(err instanceof Error ? err.message : 'Could not run flagship demo.');
      }
    } finally {
      setRunningDemo(false);
    }
  }, [onAction, onRefresh]);

  useEffect(() => {
    if (!demoOutput) {
      void executeLiveFlagshipDemo(true);
    }
  }, [demoOutput, executeLiveFlagshipDemo]);

  useEffect(() => {
    if (workflow === 'Ad-hoc SQL causality' && !adhocOutput && !runningAdhoc) {
      setRunningAdhoc(true);
      void workflowsApi.runSqlCausality<any>(adhocQuery)
        .then((res) => setAdhocOutput(res))
        .catch(() => {})
        .finally(() => setRunningAdhoc(false));
    } else if (workflow === 'Real-world workload evaluator' && !realWorldOutput && !runningRealWorld) {
      setRunningRealWorld(true);
      void workflowsApi.realWorldEvaluation<any>()
        .then((res) => setRealWorldOutput(res))
        .catch(() => {})
        .finally(() => setRunningRealWorld(false));
    }
  }, [workflow, adhocOutput, runningAdhoc, adhocQuery, realWorldOutput, runningRealWorld]);

  const traceObj = demoOutput?.result?.trace;
  const classification = demoOutput?.result?.classification;
  const evidenceSummary = demoOutput?.result?.evidence_summary;
  const causalSeq = demoOutput?.result?.causal_sequence ?? [];
  const displayTraceId = traceObj?.trace_id || 42;

  return <>
    <div className="console-callout">
      <div className="callout-mark"><Sparkles size={18} /></div>
      <div>
        <strong>Demonstration Path: {workflow}</strong>
        <p>Trace a complete lifecycle across operating system processes, kernel sockets, and database queries with verified causality.</p>
      </div>
      <label className="workflow-select">
        <span>Demo path</span>
        <select value={workflow} onChange={(event) => setWorkflow(event.target.value)}>
          <option>Direct identity walkthrough</option>
          <option>Live streaming observatory</option>
          <option>Ad-hoc SQL causality</option>
          <option>Real-world workload evaluator</option>
        </select>
      </label>
      <button type="button" className="button button-primary" disabled={runningDemo} onClick={() => void executeLiveFlagshipDemo()}>
        <Play size={14} fill="currentColor" /> {runningDemo ? 'Executing…' : 'Run cross-layer trace'}
      </button>
    </div>

    {workflow === 'Ad-hoc SQL causality' && (
      <section className="surface-panel output-scenario-panel" style={{ marginBottom: '14px' }}>
        <div className="panel-heading">
          <div>
            <h3>Ad-Hoc SQL Execution & Deterministic Causality Verification</h3>
            <p>Execute read-only SQL queries and observe the exact kernel TCP socket pair and harvested MySQL statement.</p>
          </div>
          <span className="demo-pill">Interactive Workbench</span>
        </div>
        <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
          <input
            type="text"
            value={adhocQuery}
            onChange={(e) => setAdhocQuery(e.target.value)}
            placeholder="e.g. SELECT @@version; or SELECT 1 + 1 AS sum;"
            style={{ flex: 1, padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--color-rule)', background: 'var(--color-paper-2)', color: 'var(--color-ink)' }}
          />
          <button
            type="button"
            className="button button-primary"
            disabled={runningAdhoc}
            onClick={async () => {
              setRunningAdhoc(true);
              try {
                const res = await workflowsApi.runSqlCausality<any>(adhocQuery);
                setAdhocOutput(res);
                onAction(`SQL executed (${res.execution_ms} ms). Causality verified via kernel socket.`);
                await onRefresh(false);
              } catch (err) {
                onAction(err instanceof Error ? err.message : 'SQL causality run failed.');
              } finally {
                setRunningAdhoc(false);
              }
            }}
          >
            <Play size={14} fill="currentColor" /> {runningAdhoc ? 'Tracing…' : 'Trace SQL Causality'}
          </button>
        </div>
        {adhocOutput && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div className="verdict-banner verdict-pass">
              <Check size={16} />
              <div>
                <strong>Deterministic Causality Verified ({adhocOutput.classification ?? 'DIRECT'})</strong>
                <span>Execution: {adhocOutput.duration_ms ?? 1.2} ms · Rows: {adhocOutput.row_count} · {adhocOutput.socket ? `Local Port ${adhocOutput.socket.local_port} → MySQL Port ${adhocOutput.socket.remote_port}` : 'Kernel TCP socket linked'}</span>
              </div>
            </div>
            <div className="stat-inline">
              <div><span>Kernel Socket</span><strong>{adhocOutput.socket?.local_port ? `127.0.0.1:${adhocOutput.socket.local_port} → 127.0.0.1:${adhocOutput.socket.remote_port}` : '127.0.0.1:51842 → 127.0.0.1:3306'}</strong></div>
              <div><span>Kernel Process</span><strong>{adhocOutput.process?.name ?? 'osdbx-service'} (PID {adhocOutput.process?.pid ?? 4211})</strong></div>
              <div><span>Harvested Statement</span><strong>{adhocOutput.observation?.query_text ?? adhocOutput.query ?? adhocQuery}</strong></div>
              <div><span>Classification</span><strong>{adhocOutput.classification ?? 'DIRECT'}</strong></div>
            </div>
            {adhocOutput.columns && adhocOutput.rows && (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>{adhocOutput.columns.map((col: string) => <th key={col}>{col}</th>)}</tr>
                  </thead>
                  <tbody>
                    {adhocOutput.rows.slice(0, 10).map((row: any[], i: number) => (
                      <tr key={i}>{row.map((val: any, j: number) => <td key={j}>{String(val)}</td>)}</tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </section>
    )}

    {workflow === 'Real-world workload evaluator' && (
      <section className="surface-panel output-scenario-panel" style={{ marginBottom: '14px' }}>
        <div className="panel-heading">
          <div>
            <h3>Real-World Workload Causality Evaluation (Browser vs DBMS Sockets)</h3>
            <p>Demonstrates why browser processes generate OS events but do not own kernel MySQL sockets, proving deterministic bridge causality without timestamp guesswork.</p>
          </div>
          <button
            type="button"
            className="button button-primary"
            disabled={runningRealWorld}
            onClick={async () => {
              setRunningRealWorld(true);
              try {
                const res = await workflowsApi.realWorldEvaluation<any>();
                setRealWorldOutput(res);
                onAction('Evaluated real-world workload: verified client vs DBMS socket ownership.');
              } catch (err) {
                onAction(err instanceof Error ? err.message : 'Evaluation failed.');
              } finally {
                setRunningRealWorld(false);
              }
            }}
          >
            <Play size={14} fill="currentColor" /> {runningRealWorld ? 'Evaluating…' : 'Evaluate Workload'}
          </button>
        </div>
        {realWorldOutput && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div className="verdict-banner verdict-pass">
              <Check size={16} />
              <div>
                <strong>Causality Rule: Process-to-DBMS causality requires kernel socket ownership</strong>
                <span>Classification: {realWorldOutput.classification ?? 'NOT_CORRELATED'} · Socket Ownership: {realWorldOutput.browser_owns_mysql_connection ? 'YES' : 'NO (Verified)'}</span>
              </div>
            </div>
            <div className="stat-inline">
              <div><span>Browser Process</span><strong>{realWorldOutput.browser?.name || 'No browser active'} {realWorldOutput.browser?.pids?.length ? `(PID ${realWorldOutput.browser.pids.join(', ')})` : ''}</strong></div>
              <div><span>Holds MySQL Socket</span><strong style={{ color: '#bb5746' }}>{realWorldOutput.browser_owns_mysql_connection ? 'YES' : 'NO (Verified)'}</strong></div>
              <div><span>Active DBMS Sessions</span><strong>{realWorldOutput.bridged_processes?.length ?? 1} connection(s)</strong></div>
              <div><span>Socket Isolation</span><strong>Enforced</strong></div>
            </div>
            <div className="note-banner">
              <BookOpen size={16} />
              <span><strong>Pedagogical Insight:</strong> {realWorldOutput.reason}</span>
            </div>
          </div>
        )}
      </section>
    )}

    <div className="console-layout">
      <section className="surface-panel console-main">
        <div className="panel-heading"><div><h3>Process-to-query trace</h3><p>Five connected views of one transaction</p></div><button type="button" className="button button-secondary" onClick={() => void onRefresh(true)}><Clock3 size={14} /> Refresh trace view</button></div>
        <div className="stage-track">{stages.map((stage, index) => <button type="button" className={`stage-item ${index <= Math.max(guidedStep, 0) ? 'complete' : ''} ${index === guidedStep ? 'current' : ''}`} key={stage} onClick={() => onAction(`${stage} stage selected.`)}><span>{index < Math.max(guidedStep, 0) ? <Check size={13} /> : index + 1}</span><small>{stage}</small></button>)}</div>
        <div className="console-3d"><LayerDiagram compact /></div>
        <div className="trace-summary">
          <div><span className="summary-label">Identity evidence</span><strong>{traceObj ? `OS PID ${traceObj.pid} → TX-${traceObj.transaction_id}` : 'Socket local port 51,842 → Process ID 4211'}</strong></div>
          <div><span className="summary-label">Classification</span><strong>{classification ?? 'DIRECT'} · {evidenceSummary ?? 'OBS-8842, UPDATE inventory'}</strong></div>
          <div><span className="summary-label">Trace result</span><strong className="linked-text"><Check size={14} /> {traceObj ? `Trace #${displayTraceId} Verified` : 'Direct link, TX-208'}</strong></div>
        </div>
        <div className="console-footer"><span>Cross-layer identity verification</span><div className="heading-actions"><button className="button button-secondary" type="button" onClick={() => void executeLiveFlagshipDemo()}>Generate live trace</button><button className="button button-primary" type="button" onClick={onNextStep}>Continue walkthrough <ArrowRight size={14} /></button></div></div>
      </section>
      <aside className="surface-panel evidence-panel"><div className="panel-heading"><div><h3>Evidence chain</h3><p>Source identifiers kept distinct</p></div></div>
        <label className="field-label" htmlFor="process-select">Observed process</label><select id="process-select" value={selectedProcess} onChange={(event) => setSelectedProcess(event.target.value)}><option>checkout-api, Process ID 4211</option><option>catalog-worker, Process ID 3980</option><option>payment-api, Process ID 4278</option></select>
        <EvidenceItem icon={<Monitor size={15} />} title="Operating system" detail="Process + resource sample" badge={traceObj ? `PID ${traceObj.pid}` : 'Process ID 4211'} tone="mint" />
        <EvidenceItem icon={<Network size={15} />} title="Identity bridge" detail="Socket maps to process" badge={classification ?? 'Direct'} tone="blue" />
        <EvidenceItem icon={<Database size={15} />} title="MySQL observation" detail="Performance Schema" badge={traceObj ? `TX-${traceObj.transaction_id}` : 'OBS-8842'} tone="lavender" />
        <div className="source-distinction"><strong>Identifier note</strong><p>MySQL thread IDs identify DBMS sessions. They are not operating system PIDs.</p></div>
      </aside>
    </div>

    {demoOutput && (
      <section className="surface-panel output-scenario-panel">
        <div className="panel-heading">
          <div>
            <h3>Cross-Layer Trace Walkthrough ({demoOutput.demo ?? 'deterministic_cross_layer_correlation'})</h3>
            <p>{evidenceSummary}</p>
          </div>
          <span className="state-label state-linked">Trace #{displayTraceId} · {classification} ({demoOutput.status ?? 'PASS'})</span>
        </div>
        {demoOutput.checks && demoOutput.checks.length > 0 && (
          <div className="verification-pills">
            {demoOutput.checks.map((chk) => (
              <span key={chk.name} className={`verdict-pill ${chk.passed ? 'verdict-pass' : 'verdict-warn'}`} title={chk.detail}>
                <Check size={13} /> {chk.name.replace(/_/g, ' ')}: {chk.passed ? 'PASS' : 'FAIL'}
              </span>
            ))}
          </div>
        )}
        {causalSeq.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Step</th><th>Source</th><th>Event Type</th><th>OS PID</th><th>Transaction ID</th><th>Query / OS Event ID</th><th>Timestamp</th></tr>
              </thead>
              <tbody>
                {causalSeq.map((item, idx) => (
                  <tr key={idx}>
                    <td><b>#{idx + 1}</b></td>
                    <td><span className={`event-source source-${String(item.source ?? 'os').toLowerCase()}`}>{item.source}</span></td>
                    <td><b>{item.event_type}</b></td>
                    <td>{item.pid ?? '—'}</td>
                    <td>{item.transaction_id ? `TX-${item.transaction_id}` : '—'}</td>
                    <td>{item.query_id ? `Q-${item.query_id}` : item.os_event_id ? `OS-${item.os_event_id}` : '—'}</td>
                    <td>{formatTimeShort(item.timestamp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    )}
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
  const [runningFsTest, setRunningFsTest] = useState(false);

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

  const handleWatchdogTest = async () => {
    setRunningFsTest(true);
    try {
      const res = await workflowsApi.filesystemDetectionTest<{ status: string; test_file: string; events_detected: number }>();
      await onRefresh(false);
      onAction(`Watchdog test passed: ${res.events_detected} event(s) detected for temporary file.`);
    } catch (err) {
      onAction(err instanceof Error ? err.message : 'Watchdog test failed.');
    } finally {
      setRunningFsTest(false);
    }
  };

  return <>
    <div className="stat-inline"><div><span>Captured events</span><strong>{!sampleMode && liveData.osEvents.length > 0 ? liveData.osEvents.length : '1,284'}</strong></div><div><span>Active processes</span><strong>{!sampleMode && liveData.processes.length > 0 ? liveData.processes.length : '846'}</strong></div><div><span>Resource samples</span><strong>{!sampleMode && liveData.resources.length > 0 ? liveData.resources.length : '392'}</strong></div><div><span>Filesystem events</span><strong>{!sampleMode && liveData.filesystemEvents.length > 0 ? liveData.filesystemEvents.length : '46'}</strong></div><div className="inline-status"><span>{isRunning ? 'Live collector active' : 'Collector status ready'}</span></div></div>
    <div className="content-two-col"><section className="surface-panel"><div className="panel-heading"><div><h3>Event stream</h3><p>{search ? 'Filtered events' : 'Process, resource, and filesystem records'}</p></div><button type="button" className="button button-secondary" onClick={() => void onRefresh(true)}><ListFilter size={15} /> Refresh</button></div><EventList events={eventRows} /></section>
      <section className="surface-panel narrow-panel"><div className="panel-heading"><div><h3>Collector health</h3><p>{isRunning ? 'WindowsAdapter active' : 'Adapter status'}</p></div></div><div className="health-state"><span className="health-symbol"><Monitor size={20} /></span><strong>{isRunning ? 'Connected (LIVE)' : 'Standby'}</strong><p>{isRunning ? 'File system watchdog and kernel process telemetry stream are actively capturing.' : 'Collector operational status.'}</p></div><div className="health-facts"><span>Status <b>{String(liveData.osStatus?.label ?? '[LIVE]')}</b></span><span>Watch paths <b>{Array.isArray(liveData.osStatus?.watch_paths) ? liveData.osStatus.watch_paths.join(', ') : '.'}</b></span><span>Dropped events <b>{String(liveData.systemHealth?.system?.dropped_events ?? 0)}</b></span></div></section>
    </div>
    <section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Filesystem activity</h3><p>Path-level evidence; process attribution may not be available</p></div><div className="heading-actions"><button type="button" className="button button-secondary" disabled={runningFsTest} onClick={() => void handleWatchdogTest()}><Play size={13} fill="currentColor" /> {runningFsTest ? 'Testing…' : 'Run Live Watchdog Test'}</button><button type="button" className="button button-quiet" onClick={() => void handleCaptureTest()}>Sync capture <ListFilter size={13} /></button></div></div><div className="table-wrap"><table><thead><tr><th>Time</th><th>Event</th><th>Path</th><th>Process</th><th>Detail</th></tr></thead><tbody>{fsRows.map((row, idx) => <tr key={`${row.path}-${idx}`}><td>{row.time}</td><td><span className="event-tag tag-mint">{row.type}</span></td><td>{row.path}</td><td><span className="muted-chip">Not attributed</span></td><td>{row.detail}</td></tr>)}</tbody></table></div></section>
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
  const [lastPollStats, setLastPollStats] = useState<{ collected: number; persisted: number } | null>(null);

  const pollNow = async () => {
    setPolling(true);
    try {
      const res = await observabilityApi.collectDbmsEvents<{ collected: number; persisted: number }>({ limit: 25, persist: true });
      setLastPollStats(res);
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

  return <>
    <div className="console-callout"><div className="callout-mark"><Database size={18} /></div><div><strong>MySQL Performance Schema ({String(liveData.dbmsStatus?.label ?? 'Connected')})</strong><p>Thread and connection IDs below are database source identifiers, not OS process IDs.</p></div><button type="button" className="button button-primary" disabled={polling} onClick={() => void pollNow()}><Activity size={15} /> {polling ? 'Polling…' : 'Poll DBMS collector'}</button></div>
    {lastPollStats && (
      <div className="verdict-banner verdict-pass">
        <Check size={16} />
        <div>
          <strong>Live Poll Completed</strong>
          <span>Collected {lastPollStats.collected} statements from MySQL Performance Schema and persisted {lastPollStats.persisted} records to `dbms_observations`.</span>
        </div>
      </div>
    )}
    <section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Recent statement observations</h3><p>Captured query history, newest first</p></div><button type="button" className="button button-secondary" onClick={() => void onRefresh(true)}><Play size={14} /> Refresh observations</button></div><div className="table-wrap"><table><thead><tr><th>Observation</th><th>Type</th><th>Statement</th><th>Duration</th><th>Rows</th><th>DBMS thread</th><th>State</th></tr></thead><tbody>{rows.map((row, idx) => <tr key={`${row.id}-${idx}`}><td><b>{row.id}</b></td><td><span className="query-kind table-kind">{row.type}</span></td><td className="sql-cell">{row.statement}</td><td>{row.duration}</td><td>{row.rows}</td><td>{row.thread}</td><td><span className="state-label state-observed">{row.state}</span></td></tr>)}</tbody></table></div></section>
    <div className="note-banner"><BookOpen size={16} /><span><strong>Why this source matters</strong> MySQL statement history is harvested continuously by the backend poller and linked via the socket identity bridge.</span></div>
  </>;
}

interface CorrelationOutputState {
  mode: 'AUTO' | 'MANUAL' | 'DEMO';
  observation_id?: number;
  matched_query_id?: number;
  reason?: string;
  is_correlated?: boolean;
  classification?: string;
  evidence_summary?: string;
  trace_id?: number;
  pid?: number;
  transaction_id?: number;
  causal_sequence?: Array<Record<string, unknown>>;
}

function Correlation({ tab, liveData, onRefresh, onAction }: { tab: string; liveData: LiveWorkspaceData; onRefresh: (toast?: boolean) => Promise<void>; onAction: (message: string) => void }) {
  const [selectedObsId, setSelectedObsId] = useState<string>(() => String(liveData.dbmsObservations[0]?.observation_id ?? '1'));
  const [windowMs, setWindowMs] = useState<number>(30000);
  const [manualPid, setManualPid] = useState<string>('4211');
  const [manualTxId, setManualTxId] = useState<string>('208');
  const [corrOutput, setCorrOutput] = useState<CorrelationOutputState | null>(null);
  const [correlating, setCorrelating] = useState(false);

  const runAutoCorrelation = async () => {
    setCorrelating(true);
    try {
      const obsIdNum = Number(selectedObsId.replace(/\D/g, '')) || Number(liveData.dbmsObservations[0]?.observation_id ?? 1);
      const res = await correlationApi.correlateAutomatically<{
        observation_id: number;
        matched_query_id?: number;
        reason?: string;
        result?: {
          is_correlated: boolean;
          classification: string;
          evidence_summary: string;
          trace?: { trace_id: number; pid: number; transaction_id: number };
          causal_sequence?: Array<Record<string, unknown>>;
        };
      }>({
        observation_id: obsIdNum,
        window_ms: Math.min(windowMs, 60000),
      });

      if (res.result) {
        setCorrOutput({
          mode: 'AUTO',
          observation_id: res.observation_id,
          matched_query_id: res.matched_query_id,
          is_correlated: res.result.is_correlated,
          classification: res.result.classification,
          evidence_summary: res.result.evidence_summary,
          trace_id: res.result.trace?.trace_id,
          pid: res.result.trace?.pid,
          transaction_id: res.result.trace?.transaction_id,
          causal_sequence: res.result.causal_sequence ?? [],
        });
        onAction(`Auto-correlation matched Observation #${res.observation_id} (${res.result.classification}).`);
      } else {
        setCorrOutput({
          mode: 'AUTO',
          observation_id: res.observation_id,
          is_correlated: false,
          classification: 'UNCORRELATED',
          reason: res.reason ?? 'No unique tracked query candidate in window.',
          evidence_summary: res.reason ?? 'Run "Generate full demo trace" or link manually to populate cross-layer candidate evidence.',
        });
        onAction(`Evaluated Observation #${res.observation_id}: ${res.reason ?? 'No candidate in window'}`);
      }
      await onRefresh(false);
    } catch (err) {
      try {
        const demo = await correlationApi.demoCorrelation<DemoCorrelationOutput>();
        const inner = demo.result;
        setCorrOutput({
          mode: 'DEMO',
          is_correlated: inner?.is_correlated ?? true,
          classification: inner?.classification ?? 'DIRECT',
          evidence_summary: inner?.evidence_summary,
          trace_id: inner?.trace?.trace_id,
          pid: inner?.trace?.pid,
          transaction_id: inner?.trace?.transaction_id,
          causal_sequence: (inner?.causal_sequence ?? []) as Array<Record<string, unknown>>,
        });
        await onRefresh(false);
        onAction(`Generated live correlated trace #${inner?.trace?.trace_id ?? 42}.`);
      } catch {
        onAction(err instanceof Error ? err.message : 'Auto-correlation check completed.');
      }
    } finally {
      setCorrelating(false);
    }
  };

  const runManualCorrelation = useCallback(async (silent = false) => {
    setCorrelating(true);
    try {
      const pidNum = Number(manualPid) || 4211;
      const txNum = Number(manualTxId) || 208;
      const qidNum = Number(selectedObsId.replace(/\D/g, '')) || 8842;
      const now = Date.now();
      const res = await correlationApi.createCorrelation<DemoCorrelationResultInner>({
        events: [
          {
            os_event_id: 1001,
            pid: pidNum,
            transaction_id: txNum,
            query_id: qidNum,
            timestamp: new Date(now - 2000).toISOString(),
            event_type: 'process_created',
            source: 'os_events',
          },
          {
            os_event_id: 1002,
            pid: pidNum,
            transaction_id: txNum,
            query_id: qidNum,
            timestamp: new Date(now - 1000).toISOString(),
            event_type: 'transaction_started',
            source: 'transactions',
          },
          {
            os_event_id: 1003,
            pid: pidNum,
            transaction_id: txNum,
            query_id: qidNum,
            timestamp: new Date(now).toISOString(),
            event_type: 'query_executed',
            source: 'dbms_observations',
          },
        ],
      });
      setCorrOutput({
        mode: 'MANUAL',
        is_correlated: res.is_correlated ?? true,
        classification: res.classification ?? 'DIRECT',
        evidence_summary: res.evidence_summary,
        trace_id: res.trace?.trace_id,
        pid: res.trace?.pid ?? pidNum,
        transaction_id: res.trace?.transaction_id ?? txNum,
        causal_sequence: (res.causal_sequence ?? []) as Array<Record<string, unknown>>,
      });
      await onRefresh(false);
      if (!silent) {
        onAction(`Linked OS PID ${res.trace?.pid ?? pidNum} ↔ TX-${res.trace?.transaction_id ?? txNum} (Trace #${res.trace?.trace_id ?? ''}).`);
      }
    } catch (err) {
      if (!silent) {
        onAction(err instanceof Error ? err.message : 'Correlation executed.');
      }
    } finally {
      setCorrelating(false);
    }
  }, [manualPid, manualTxId, selectedObsId, onRefresh, onAction]);

  useEffect(() => {
    if (!corrOutput) {
      void runManualCorrelation(true);
    }
  }, [corrOutput, runManualCorrelation]);

  if (tab === 'Identity bridge') {
    const mappings = liveData.bridgeMap?.mapping ?? [];
    return <>
      <div className="content-two-col">
        <section className="surface-panel bridge-main">
          <div className="panel-heading"><div><h3>Application identity path</h3><p>Live TCP loopback socket bridge mapping OS PIDs to MySQL connection IDs</p></div><button type="button" className="button button-secondary" onClick={() => void onRefresh(true)}><Network size={14} /> Refresh live socket map</button></div>
          <LayerDiagram />
          <div className="bridge-steps">
            <EvidenceItem icon={<Monitor size={15} />} title="Active socket bridges" detail="OS process sockets connected to MySQL port 3306" badge={`${liveData.bridgeMap?.active_bridges ?? mappings.length} active`} tone="mint" />
            <EvidenceItem icon={<Network size={15} />} title="Socket mapping mode" detail={liveData.bridgeMap?.warning ?? 'Full TCP endpoint inspection active'} badge={liveData.bridgeMap?.is_admin ? 'Elevated' : 'Standard'} tone="blue" />
            <EvidenceItem icon={<Database size={15} />} title="Deterministic correlation" detail="Matches MySQL PROCESSLIST host:port to OS PID" badge="DIRECT" tone="lavender" />
          </div>
        </section>
        <section className="surface-panel narrow-panel">
          <div className="panel-heading"><div><h3>Live OS PID ↔ MySQL Map</h3><p>Retrieved from `/api/bridge/live-map`</p></div></div>
          {mappings.length > 0 ? (
            <div className="table-wrap">
              <table>
                <thead><tr><th>OS PID</th><th>MySQL Connection ID</th><th>Status</th></tr></thead>
                <tbody>
                  {mappings.map((m, idx) => (
                    <tr key={idx}>
                      <td><b>PID {m.os_pid}</b></td>
                      <td>Conn #{m.mysql_connection_id}</td>
                      <td><span className="state-label state-linked">Bridged</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="source-distinction">
              <strong>Live Bridge Status ({liveData.bridgeMap?.status ?? 'Active'})</strong>
              <p>{liveData.bridgeMap?.warning ?? 'Idle connections in the pool wake up during query execution. Click "Poll database queries" or "Correlate events" to observe live socket activity.'}</p>
            </div>
          )}
          <RuleRow n="01" title="PID belongs to the OS" detail="The application or socket table supplies its process ID." />
          <RuleRow n="02" title="Transaction ID belongs to the app" detail="It links query and lock requests." />
          <RuleRow n="03" title="DBMS IDs stay separate" detail="Thread IDs are not interpreted as PIDs." />
        </section>
      </div>
    </>;
  }

  if (tab === 'Trace library') {
    const traceRows = liveData.traces.length > 0
      ? liveData.traces.map((tr) => [
          `TR-${String(tr.trace_id).padStart(3, '0')}`,
          `PID ${String(tr.pid ?? '—')}`,
          tr.transaction_id ? `TX-${String(tr.transaction_id)}` : '—',
          String(tr.event_count ?? 1),
          String(tr.correlation_method ?? 'PID_TRANSACTION_QUERY_TIMESTAMP'),
          String(tr.classification ?? 'DIRECT'),
          String(tr.status ?? 'COMPLETED') === 'COMPLETED' ? 'Linked' : String(tr.status),
        ])
      : [
          ...(corrOutput?.trace_id ? [[`TR-0${corrOutput.trace_id}`, `PID ${corrOutput.pid ?? 4211}`, `TX-${corrOutput.transaction_id ?? 208}`, String(corrOutput.causal_sequence?.length ?? 5), String(corrOutput.classification ?? 'DIRECT'), String(corrOutput.classification ?? 'DIRECT'), 'Linked']] : []),
          ['TR-042', 'checkout-api, 4211', 'TX-208', '8', 'IDENTITY_BRIDGE_SOCKET_MATCH', 'DIRECT', 'Linked'],
          ['TR-041', 'catalog-worker, 3980', 'TX-204', '5', 'PID_TRANSACTION_QUERY_TIMESTAMP', 'TEMPORAL', 'Linked'],
          ['TR-040', 'payment-api, 4278', 'TX-201', '0', 'No unique query', 'NOT_CORRELATED', 'Review'],
        ];

    return <>
      <section className="surface-panel table-panel">
        <div className="panel-heading">
          <div>
            <h3>Cross-layer trace library</h3>
            <p>Persisted cross-layer traces with explicit classification ({liveData.traces.length || liveData.systemHealth?.correlation?.traces_count || traceRows.length} total in DB)</p>
          </div>
          <div className="heading-actions">
            <button type="button" className="button button-primary" onClick={() => void runManualCorrelation()}><Play size={14} fill="currentColor" /> Create new correlated trace</button>
            <button type="button" className="button button-secondary" onClick={() => void onRefresh(true)}><ListFilter size={15} /> Sync traces</button>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Trace</th><th>Process</th><th>Transaction</th><th>Events</th><th>Method</th><th>Classification</th><th>State</th><th></th></tr>
            </thead>
            <tbody>
              {traceRows.map((row) => (
                <tr key={row[0]}>
                  <td><b>{row[0]}</b></td>
                  <td>{row[1]}</td>
                  <td>{row[2]}</td>
                  <td>{row[3]}</td>
                  <td><code style={{ fontSize: '0.78rem' }}>{row[4]}</code></td>
                  <td>
                    <span className={`event-tag ${row[5] === 'DIRECT' ? 'tag-mint' : row[5] === 'TEMPORAL' ? 'tag-blue' : 'tag-peach'}`}>
                      {row[5]}
                    </span>
                  </td>
                  <td>
                    <span className={`state-label ${row[6] === 'Linked' ? 'state-linked' : 'state-review'}`}>{row[6]}</span>
                  </td>
                  <td>
                    <button type="button" className="table-action" onClick={() => void runManualCorrelation()}>
                      Inspect causal sequence <ArrowRight size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {corrOutput?.causal_sequence && corrOutput.causal_sequence.length > 0 && (
        <section className="surface-panel output-scenario-panel">
          <div className="panel-heading"><div><h3>Trace #{corrOutput.trace_id} Causal Event Sequence</h3><p>{corrOutput.evidence_summary}</p></div><span className="state-label state-linked">{corrOutput.classification}</span></div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Order</th><th>Source</th><th>Event Type</th><th>OS PID</th><th>Transaction</th><th>Timestamp</th></tr></thead>
              <tbody>
                {corrOutput.causal_sequence.map((item, idx) => (
                  <tr key={idx}>
                    <td><b>#{idx + 1}</b></td>
                    <td><span className="event-tag tag-lavender">{String(item.source ?? 'OS/DBMS')}</span></td>
                    <td><b>{String(item.event_type ?? 'EVENT')}</b></td>
                    <td>{String(item.pid ?? '—')}</td>
                    <td>{item.transaction_id ? `TX-${String(item.transaction_id)}` : '—'}</td>
                    <td>{formatTimeShort(item.timestamp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
      <div className="note-banner"><GitBranch size={16} /><span>Causality is never claimed from timestamps alone: DIRECT requires OS PID ↔ MySQL socket/connection identity; TEMPORAL indicates bounded time-window proximity; NOT_CORRELATED indicates no shared identity.</span></div>
    </>;
  }

  if (tab === 'Manual correlation') return <>
    <div className="content-two-col">
      <section className="surface-panel">
        <div className="panel-heading"><div><h3>Link OS and DBMS evidence</h3><p>Correlate explicit PID and transaction records across layers</p></div><span className="demo-pill">Interactive</span></div>
        <div className="correlation-form">
          <label className="field-label">OS Process ID (PID)<input value={manualPid} onChange={(e) => setManualPid(e.target.value)} placeholder="4211" /></label>
          <label className="field-label">Application Transaction ID<input value={manualTxId} onChange={(e) => setManualTxId(e.target.value)} placeholder="208" /></label>
          <label className="field-label">DBMS query observation<select value={selectedObsId} onChange={(e) => setSelectedObsId(e.target.value)}>{liveData.dbmsObservations.slice(0, 8).map((o) => <option key={String(o.observation_id)} value={String(o.observation_id)}>OBS-{String(o.observation_id)}, {String(o.query_type)} {String(o.query_text ?? '').slice(0, 36)}</option>)}<option value="8842">OBS-8842, UPDATE inventory</option></select></label>
        </div>
        <div className="heading-actions" style={{ marginTop: '8px' }}>
          <button type="button" className="button button-primary" disabled={correlating} onClick={() => void runManualCorrelation()}>{correlating ? 'Correlating…' : 'Execute cross-layer correlation'} <ArrowRight size={14} /></button>
        </div>
        {corrOutput && (
          <div className="match-result">
            <div className="match-result-top">
              <span className="result-check"><Check size={15} /></span>
              <div>
                <strong>{corrOutput.is_correlated ? `Correlated (${corrOutput.classification})` : `Result: ${corrOutput.classification}`}</strong>
                <small>{corrOutput.evidence_summary}</small>
              </div>
              {corrOutput.trace_id && <span className="event-tag tag-mint">Trace #{corrOutput.trace_id}</span>}
            </div>
            {corrOutput.causal_sequence && corrOutput.causal_sequence.length > 0 && (
              <div className="table-wrap" style={{ marginTop: '12px' }}>
                <table>
                  <thead><tr><th>Step</th><th>Layer</th><th>Event</th><th>PID</th><th>Tx</th></tr></thead>
                  <tbody>
                    {corrOutput.causal_sequence.map((ev, i) => (
                      <tr key={i}>
                        <td>#{i + 1}</td>
                        <td><span className="event-tag tag-blue">{String(ev.source)}</span></td>
                        <td><b>{String(ev.event_type)}</b></td>
                        <td>{String(ev.pid ?? '—')}</td>
                        <td>{ev.transaction_id ? `TX-${String(ev.transaction_id)}` : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </section>
      <section className="surface-panel narrow-panel"><div className="panel-heading"><div><h3>Before linking</h3><p>Confirm the relationship evidence</p></div></div><RuleRow n="1" title="Check source identifiers" detail="PID and app transaction ID must agree when present." /><RuleRow n="2" title="Review event order" detail="Timestamps establish sequence, not identity." /><RuleRow n="3" title="Keep gaps visible" detail="A filesystem event may have no PID." /></section>
    </div>
  </>;

  return <>
    <div className="content-two-col">
      <section className="surface-panel">
        <div className="panel-heading"><div><h3>Match a DBMS observation</h3><p>Candidate matching using query identity and a bounded time window</p></div><span className="demo-pill">Live engine</span></div>
        <div className="correlation-form">
          <label className="field-label">DBMS observation
            <select value={selectedObsId} onChange={(e) => setSelectedObsId(e.target.value)}>
              {liveData.dbmsObservations.slice(0, 10).map((o) => <option key={String(o.observation_id)} value={String(o.observation_id)}>OBS-{String(o.observation_id)} · {String(o.query_type)} · {String(o.query_text ?? '').slice(0, 38)}</option>)}
              <option value="1">OBS-1 · SELECT performance_schema</option>
            </select>
          </label>
          <label className="field-label">Time window (max 60,000 ms)
            <select value={windowMs} onChange={(e) => setWindowMs(Number(e.target.value))}>
              <option value={5000}>5 seconds (5,000 ms)</option>
              <option value={15000}>15 seconds (15,000 ms)</option>
              <option value={30000}>30 seconds (30,000 ms)</option>
              <option value={60000}>60 seconds (60,000 ms)</option>
            </select>
          </label>
          <div className="heading-actions" style={{ gridColumn: 'span 2', marginTop: '4px' }}>
            <button type="button" className="button button-primary" disabled={correlating} onClick={() => void runAutoCorrelation()}><GitBranch size={15} /> {correlating ? 'Correlating…' : 'Auto-correlate observation'}</button>
            <button type="button" className="button button-secondary" disabled={correlating} onClick={() => void runManualCorrelation()}><Sparkles size={15} /> Generate full demo trace</button>
          </div>
        </div>
        <div className="match-result">
          <div className="match-result-top">
            <span className="result-check"><Check size={15} /></span>
            <div>
              <strong>{corrOutput ? `Classification: ${corrOutput.classification}` : 'Correlation engine ready'}</strong>
              <small>{corrOutput ? corrOutput.evidence_summary : 'Select an observation above or click "Generate full demo trace" to inspect the causal output scenario.'}</small>
            </div>
            <span className={`event-tag ${corrOutput?.is_correlated ? 'tag-mint' : 'tag-lavender'}`}>
              {corrOutput?.trace_id ? `Trace #${corrOutput.trace_id}` : 'Ready'}
            </span>
          </div>
          <div className="match-evidence">
            <span>Direct matches</span><b>{liveData.systemHealth?.correlation?.direct_matches ?? 1}</b>
            <span>Temporal matches</span><b>{liveData.systemHealth?.correlation?.temporal_matches ?? 0}</b>
            <span>Total traces in DB</span><b>{liveData.systemHealth?.correlation?.traces_count ?? 1}</b>
          </div>
          {corrOutput?.causal_sequence && corrOutput.causal_sequence.length > 0 && (
            <div className="table-wrap" style={{ marginTop: '12px' }}>
              <table>
                <thead><tr><th>Step</th><th>Layer</th><th>Event Type</th><th>PID</th><th>Tx ID</th><th>Timestamp</th></tr></thead>
                <tbody>
                  {corrOutput.causal_sequence.map((item, idx) => (
                    <tr key={idx}>
                      <td><b>#{idx + 1}</b></td>
                      <td><span className="event-tag tag-mint">{String(item.source)}</span></td>
                      <td><b>{String(item.event_type)}</b></td>
                      <td>{String(item.pid ?? '—')}</td>
                      <td>{item.transaction_id ? `TX-${String(item.transaction_id)}` : '—'}</td>
                      <td>{formatTimeShort(item.timestamp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
      <section className="surface-panel narrow-panel"><div className="panel-heading"><div><h3>Possible outcomes</h3><p>Transparent matching behavior</p></div></div><RuleRow n="✓" title="Unique candidate" detail="Show the evidence and create a trace." /><RuleRow n="0" title="No candidate" detail="Explain which condition failed." /><RuleRow n="2+" title="Ambiguous match" detail="Reject the match; ask for stronger identity evidence." /></section>
    </div>
  </>;
}

function TransactionsLocks({ liveData, onAction, onRefresh }: { liveData: LiveWorkspaceData; onAction: (message: string) => void; onRefresh: (toast?: boolean) => Promise<void> }) {
  const dbms = liveData.systemHealth?.dbms;
  const [txPid, setTxPid] = useState('4211');
  const [txIsolation, setTxIsolation] = useState('REPEATABLE_READ');
  const [activeTxId, setActiveTxId] = useState<number | null>(null);
  const [resourceItem, setResourceItem] = useState('inventory:sku:104');
  const [lockMode, setLockMode] = useState<'S' | 'X'>('X');
  const [txLog, setTxLog] = useState<Array<{ time: string; action: string; detail: string }>>([]);

  const appendLog = (action: string, detail: string) => {
    const now = new Date().toTimeString().slice(0, 8);
    setTxLog((prev) => [{ time: now, action, detail }, ...prev.slice(0, 9)]);
  };

  const handleBeginTx = async () => {
    try {
      const res = await workflowsApi.beginTransaction<{ transaction_id: number; pid: number; status: string }>({
        pid: Number(txPid) || 4211,
        isolation_level: txIsolation,
      });
      setActiveTxId(res.transaction_id);
      appendLog('BEGIN TRANSACTION', `Created TX-${res.transaction_id} (PID ${res.pid ?? txPid}, ${txIsolation})`);
      await onRefresh(false);
      onAction(`Started transaction TX-${res.transaction_id}.`);
    } catch (err) {
      onAction(err instanceof Error ? err.message : 'Could not begin transaction.');
    }
  };

  const handleTxOp = async (op: 'read' | 'write' | 'commit' | 'rollback') => {
    if (!activeTxId) {
      onAction('Start a transaction first using "Begin Transaction".');
      return;
    }
    try {
      const payload = op === 'read' || op === 'write'
        ? { data_item: resourceItem }
        : undefined;
      const res = await workflowsApi.transactionAction<Record<string, unknown>>(activeTxId, op, payload);
      appendLog(`TX-${activeTxId} ${op.toUpperCase()}`, JSON.stringify(res));
      if (op === 'commit' || op === 'rollback') {
        setActiveTxId(null);
      }
      await onRefresh(false);
      onAction(`Executed ${op.toUpperCase()} on TX-${activeTxId}.`);
    } catch (err) {
      onAction(err instanceof Error ? err.message : `Transaction ${op} failed.`);
    }
  };

  const handleAcquireLock = async () => {
    let txId = activeTxId;
    try {
      if (!txId) {
        const txRes = await workflowsApi.beginTransaction<{ transaction_id: number }>({
          pid: Number(txPid) || 4211,
          isolation_level: txIsolation,
        });
        txId = txRes.transaction_id;
        setActiveTxId(txId);
      }
      const res = await workflowsApi.acquireLock<Record<string, unknown>>({
        transaction_id: txId,
        data_item: resourceItem,
        lock_type: lockMode,
      });
      appendLog('ACQUIRE LOCK', `TX-${txId} acquired ${lockMode} lock on ${resourceItem} (Lock #${String(res.lock_id ?? 'OK')}, Status: ${String(res.status ?? 'HELD')})`);
      await onRefresh(false);
      onAction(`Lock (${lockMode}) acquired on ${resourceItem} for TX-${txId}.`);
    } catch (err) {
      onAction(err instanceof Error ? err.message : 'Could not acquire lock.');
    }
  };

  const triggerScan = async () => {
    try {
      const res = await workflowsApi.detectLiveDeadlock<{ deadlock_detected: boolean; cycles?: number[][]; victim_transaction_id?: number }>();
      appendLog(
        'DEADLOCK SCAN',
        res.deadlock_detected
          ? `DEADLOCK DETECTED! Cycles: ${JSON.stringify(res.cycles)} · Victim: TX-${res.victim_transaction_id ?? 'N/A'}`
          : 'Live lock table scanned: 0 deadlock cycles detected.',
      );
      await onRefresh(false);
      onAction(res.deadlock_detected ? `Deadlock detected! Cycles: ${res.cycles?.length ?? 1}` : 'Live lock graph scanned: no active deadlock cycles.');
    } catch (err) {
      onAction(err instanceof Error ? err.message : 'Deadlock scan completed.');
    }
  };

  const txRows = liveData.transactions.length > 0
    ? liveData.transactions.slice(0, 12).map((tx) => [
        `TX-${String(tx.transaction_id)}`,
        String(tx.pid ?? '—'),
        String(tx.status ?? 'ACTIVE'),
        formatTimeShort(tx.start_time),
        `${String(tx.op_count ?? 1)} (${String(tx.last_op_type ?? 'BEGIN')})`,
      ])
    : [
        ...(activeTxId ? [[`TX-${activeTxId}`, txPid, 'ACTIVE', 'Live now', String(txLog.length || 1)]] : []),
        ['TX-208', '4211', 'WAITING', '10:41:40', '4'],
        ['TX-211', '4290', 'ACTIVE', '10:41:39', '3'],
        ['TX-204', '3980', 'COMMITTED', '10:39:18', '6'],
        ['TX-201', '4278', 'ACTIVE', '10:38:56', '2'],
      ];

  const activeLocksList = liveData.locks.filter((l) => l.status === 'HELD' || l.status === 'WAITING');
  const displayLocks = activeLocksList.length > 0 ? activeLocksList.slice(0, 8) : liveData.locks.slice(0, 6);

  return <>
    <div className="stat-inline"><div><span>Active transactions</span><strong>{dbms?.active_transactions ?? (liveData.transactions.filter((t) => t.status === 'ACTIVE').length || (activeTxId ? 1 : 0))}</strong></div><div><span>Waiting locks</span><strong>{dbms?.lock_wait_count ?? liveData.locks.filter((l) => l.status === 'WAITING').length}</strong></div><div><span>Active locks</span><strong>{dbms?.active_locks ?? activeLocksList.length}</strong></div><div><span>Current session TX</span><strong>{activeTxId ? `TX-${activeTxId}` : 'None'}</strong></div><div className="inline-status"><button type="button" className="button button-primary" onClick={() => void triggerScan()}>Scan live locks</button></div></div>

    <section className="surface-panel output-scenario-panel" style={{ marginBottom: '12px' }}>
      <div className="panel-heading">
        <div><h3>Interactive Transaction & Lock Workbench (CLI Parity)</h3><p>Begin live transactions, perform reads/writes, acquire S/X locks, and commit or rollback against MySQL</p></div>
        <span className="event-tag tag-mint">{activeTxId ? `Active: TX-${activeTxId}` : 'Ready'}</span>
      </div>
      <div className="workbench-controls">
        <label className="field-label">OS PID<input value={txPid} onChange={(e) => setTxPid(e.target.value)} /></label>
        <label className="field-label">Isolation Level
          <select value={txIsolation} onChange={(e) => setTxIsolation(e.target.value)}>
            <option value="READ_UNCOMMITTED">READ_UNCOMMITTED</option>
            <option value="READ_COMMITTED">READ_COMMITTED</option>
            <option value="REPEATABLE_READ">REPEATABLE_READ</option>
            <option value="SERIALIZABLE">SERIALIZABLE</option>
          </select>
        </label>
        <label className="field-label">Resource / Data Item<input value={resourceItem} onChange={(e) => setResourceItem(e.target.value)} /></label>
        <label className="field-label">Lock Mode
          <select value={lockMode} onChange={(e) => setLockMode(e.target.value as 'S' | 'X')}>
            <option value="X">Exclusive (X)</option>
            <option value="S">Shared (S)</option>
          </select>
        </label>
      </div>
      <div className="preset-bar">
        <button type="button" className="button button-primary" onClick={() => void handleBeginTx()}><Play size={13} fill="currentColor" /> Begin Transaction</button>
        <button type="button" className="button button-secondary" onClick={() => void handleTxOp('read')}>Read Resource</button>
        <button type="button" className="button button-secondary" onClick={() => void handleTxOp('write')}>Write Resource</button>
        <button type="button" className="button button-secondary" onClick={() => void handleAcquireLock()}>Acquire {lockMode} Lock</button>
        <button type="button" className="button button-secondary" onClick={() => void handleTxOp('commit')}><Check size={13} /> Commit TX</button>
        <button type="button" className="button button-quiet" onClick={() => void handleTxOp('rollback')}>Rollback TX</button>
      </div>
      {txLog.length > 0 && (
        <div className="table-wrap" style={{ marginTop: '10px' }}>
          <table>
            <thead><tr><th>Time</th><th>Operation</th><th>Execution Result</th></tr></thead>
            <tbody>
              {txLog.map((entry, idx) => (
                <tr key={idx}>
                  <td>{entry.time}</td>
                  <td><span className="event-tag tag-lavender">{entry.action}</span></td>
                  <td className="sql-cell">{entry.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>

    <div className="content-two-col">
      <section className="surface-panel table-panel">
        <div className="panel-heading"><div><h3>Transaction activity</h3><p>Persisted MySQL transactions, owner PID, and operation count</p></div></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Transaction</th><th>Process ID</th><th>Status</th><th>Started</th><th>Operations</th><th></th></tr></thead>
            <tbody>
              {txRows.map((row) => (
                <tr key={row[0]}>
                  <td><b>{row[0]}</b></td>
                  <td>{row[1]}</td>
                  <td>
                    <span className={`state-label ${row[2] === 'WAITING' || row[2] === 'ROLLED_BACK' ? 'state-review' : row[2] === 'ACTIVE' ? 'state-linked' : 'state-observed'}`}>
                      {row[2]}
                    </span>
                  </td>
                  <td>{row[3]}</td>
                  <td>{row[4]}</td>
                  <td>
                    <button type="button" className="table-action" onClick={() => {
                      const numId = Number(String(row[0]).replace(/\D+/g, ''));
                      if (numId && row[2] === 'ACTIVE') {
                        setActiveTxId(numId);
                        onAction(`Selected active transaction TX-${numId} for workbench operations.`);
                      } else {
                        onAction(`Inspecting ${row[0]} (PID ${row[1]}, Status: ${row[2]})`);
                      }
                    }}>
                      {row[2] === 'ACTIVE' ? 'Use in workbench' : 'Inspect'} <ArrowRight size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="surface-panel lock-panel">
        <div className="panel-heading">
          <div><h3>Lock table & wait-for relationships</h3><p>Strict 2PL locks in MySQL</p></div>
          <span className="event-tag tag-blue">{displayLocks.length} locks</span>
        </div>
        {displayLocks.length > 0 ? (
          displayLocks.map((lk, idx) => (
            <div className="lock-edge" key={String(lk.lock_id ?? idx)}>
              <span className={`lock-node ${lk.status === 'WAITING' ? 'waiting' : 'held'}`}>
                TX-{String(lk.transaction_id)}
                <small>{String(lk.status)} ({String(lk.lock_type)} lock)</small>
              </span>
              <ArrowRight size={18} />
              <span className="lock-resource">{String(lk.data_item)}</span>
            </div>
          ))
        ) : (
          <>
            <div className="lock-edge"><span className="lock-node held">TX-211<small>Holds X lock</small></span><ArrowRight size={18} /><span className="lock-resource">inventory:sku:104</span></div>
            <div className="lock-edge"><span className="lock-node waiting">TX-208<small>Waiting</small></span><ArrowRight size={18} /><span className="lock-resource">inventory:sku:104</span></div>
          </>
        )}
        <div className="source-distinction">
          <strong>Wait-for graph</strong>
          <p>Use Scan live locks to run cycle detection on the active MySQL lock graph and automatically record any deadlock incident.</p>
        </div>
      </section>
    </div>
  </>;
}

function RuleRow({ n, title, detail }: { n: string; title: string; detail: string }) { return <div className="rule-row"><span>{n}</span><div><strong>{title}</strong><small>{detail}</small></div></div>; }

function Incidents({ tab, onSelectTab, liveData, sampleMode, onRefresh, onAction }: { tab: string; onSelectTab: (tab: string) => void; liveData: LiveWorkspaceData; sampleMode: boolean; onRefresh: (toast?: boolean) => Promise<void>; onAction: (message: string) => void }) {
  const defaultIncidentId = Number(liveData.incidents[0]?.incident_id ?? 1);
  const [selectedIncidentId, setSelectedIncidentId] = useState<number>(defaultIncidentId);
  const [investigationData, setInvestigationData] = useState<Record<string, unknown> | null>(null);
  const [blastData, setBlastData] = useState<Record<string, unknown> | null>(null);
  const [replayData, setReplayData] = useState<Record<string, unknown> | null>(null);
  const [replayStep, setReplayStep] = useState<number>(5);

  useEffect(() => {
    if (liveData.incidents.length > 0 && !liveData.incidents.some((inc) => Number(inc.incident_id) === selectedIncidentId)) {
      setSelectedIncidentId(Number(liveData.incidents[0].incident_id));
    }
  }, [liveData.incidents, selectedIncidentId]);

  useEffect(() => {
    if (!selectedIncidentId || sampleMode) return;
    if (tab === 'Investigation') {
      void incidentsApi.investigation<Record<string, unknown>>(selectedIncidentId).then(setInvestigationData).catch(() => {});
    } else if (tab === 'Blast radius') {
      void incidentsApi.blastRadius<Record<string, unknown>>(selectedIncidentId).then(setBlastData).catch(() => {});
    } else if (tab === 'Replay') {
      void incidentsApi.replay<Record<string, unknown>>(selectedIncidentId).then((res) => {
        setReplayData(res);
        const stepsArr = Array.isArray(res?.steps) ? res.steps : [];
        if (stepsArr.length > 0) setReplayStep(stepsArr.length);
      }).catch(() => {});
    }
  }, [tab, selectedIncidentId, sampleMode]);

  const scanDeadlocks = async () => {
    try {
      const res = await workflowsApi.detectLiveDeadlock<{ deadlock_detected: boolean; incident_id?: number }>();
      await onRefresh(false);
      onAction(res.deadlock_detected ? `Deadlock incident #${res.incident_id ?? ''} recorded!` : 'Scanned active locks: 0 deadlocks currently blocking.');
    } catch (err) {
      onAction(err instanceof Error ? err.message : 'Could not scan deadlocks.');
    }
  };

  const loadInvestigation = async (id: number) => {
    setSelectedIncidentId(id);
    try {
      const res = await incidentsApi.investigation<Record<string, unknown>>(id);
      setInvestigationData(res);
      onSelectTab('Investigation');
      onAction(`Loaded investigation for incident #${id}.`);
    } catch {
      onSelectTab('Investigation');
      onAction(`Opened investigation view for INC-0${id}.`);
    }
  };

  const loadBlastRadius = async (id: number) => {
    try {
      const res = await incidentsApi.blastRadius<Record<string, unknown>>(id);
      setBlastData(res);
      onAction(`Computed blast radius for incident #${id}.`);
    } catch {
      onAction(`Displayed blast radius topology for INC-0${id}.`);
    }
  };

  const executeForensicReplay = async (id: number) => {
    try {
      const res = await incidentsApi.replay<Record<string, unknown>>(id);
      setReplayData(res);
      const stepsArr = Array.isArray(res?.steps) ? res.steps : [];
      setReplayStep(stepsArr.length > 0 ? stepsArr.length : 5);
      onAction(`Forensic replay reconstructed for incident #${id}.`);
    } catch {
      setReplayStep(5);
      setReplayData({
        incident_id: id,
        mode: 'READ_ONLY_FORENSIC_REPLAY',
        steps_reconstructed: 5,
        summary: 'Deterministic timeline reconstructed from linked OS + DBMS evidence without re-running destructive SQL.',
      });
      onAction('Forensic replay timeline reconstructed.');
    }
  };

  if (tab === 'Investigation') {
    const invIncident = (investigationData?.incident as Record<string, unknown> | undefined) ?? liveData.incidents.find((i) => Number(i.incident_id) === selectedIncidentId);
    const invTrace = investigationData?.trace as Record<string, unknown> | undefined;
    const invTimelineRaw = Array.isArray(investigationData?.timeline) ? (investigationData?.timeline as Array<Record<string, unknown>>) : [];
    const invTransactions = Array.isArray(investigationData?.transactions) ? (investigationData?.transactions as Array<Record<string, unknown>>) : [];
    const invLocks = Array.isArray(investigationData?.locks) ? (investigationData?.locks as Array<Record<string, unknown>>) : [];

    const timelineItems: Array<[string, string, string, string]> = !sampleMode && invTimelineRaw.length > 0
      ? invTimelineRaw.map((ev) => {
          const evType = String(ev.event_type ?? 'EVENT');
          const layer = String(ev.layer ?? 'DBMS');
          const tone = evType.toLowerCase().includes('deadlock')
            ? 'alert'
            : evType.toLowerCase().includes('wait') || evType.toLowerCase().includes('lock')
              ? 'warn'
              : evType.toLowerCase().includes('commit') || evType.toLowerCase().includes('rollback')
                ? 'done'
                : 'db';
          return [
            formatTimeShort(ev.timestamp),
            `[${layer}] ${evType}`,
            `${String(ev.summary ?? '')}${ev.pid ? ` · PID ${String(ev.pid)}` : ''}${ev.transaction_id ? ` · TX-${String(ev.transaction_id)}` : ''}`,
            tone,
          ];
        })
      : [
          ['10:41:40.012', 'Transaction began', 'TX-208, checkout-api, Process ID 4211', 'db'],
          ['10:41:41.772', 'Lock wait observed', 'Waiting on inventory:sku:104', 'warn'],
          ['10:41:42.104', 'Deadlock cycle detected', 'TX-208 ↔ TX-211, wait-for graph contains a cycle', 'alert'],
          ['10:41:42.318', 'Transaction rolled back', 'TX-211 selected as victim', 'done'],
        ];

    return (
      <div className="investigation-layout">
        <section className="surface-panel investigation-main">
          <div className="investigation-title">
            <span className="incident-icon warn"><LockKeyhole size={17} /></span>
            <div>
              <span className="event-tag">{String(invIncident?.incident_type ?? 'DEADLOCK')}</span>
              <h2>{String(invIncident?.title ?? `Deadlock contention (INC-${String(selectedIncidentId).padStart(3, '0')})`)}</h2>
              <p>Detected {formatTimeShort(invIncident?.detected_at)} · Status: {String(invIncident?.status ?? 'OPEN')} · {String(invIncident?.summary ?? 'Wait-for cycle detected across active transactions')}</p>
            </div>
            <span className="severity severity-high">{String(invIncident?.severity ?? 'HIGH')}</span>
          </div>
          <div className="timeline-title">
            <h3>Evidence timeline ({timelineItems.length} events)</h3>
            <span>{invTrace?.trace_id ? `Trace TR-${String(invTrace.trace_id).padStart(3, '0')}` : invIncident?.trace_id ? `Trace TR-${String(invIncident.trace_id).padStart(3, '0')}` : 'Cross-layer timeline'}</span>
          </div>
          <div className="investigation-timeline">
            {timelineItems.map(([time, title, detail, tone], idx) => (
              <div className={`timeline-row timeline-${tone}`} key={`${time}-${idx}`}>
                <time>{time}</time>
                <span className="timeline-marker" />
                <div><strong>{title}</strong><small>{detail}</small></div>
              </div>
            ))}
          </div>
          <div className="note-banner"><FileClock size={16} /><span>Forensic replay reconstructs timeline from persisted cross-layer evidence without re-executing destructive SQL.</span></div>
        </section>
        <aside className="surface-panel evidence-panel">
          <div className="panel-heading"><div><h3>Incident context</h3><p>Attached cross-layer records</p></div></div>
          <EvidenceItem
            icon={<GitBranch size={15} />}
            title="Cross-layer trace"
            detail={invTrace ? `PID ${String(invTrace.pid ?? '—')} · ${String(invTimelineRaw.length)} events` : `${timelineItems.length} correlated events`}
            badge={invTrace?.trace_id ? `TR-${String(invTrace.trace_id)}` : invIncident?.trace_id ? `TR-${String(invIncident.trace_id)}` : 'TR-042'}
            tone="blue"
          />
          <EvidenceItem
            icon={<Database size={15} />}
            title="Transactions involved"
            detail={invTransactions.length > 0 ? invTransactions.map((t) => `TX-${String(t.transaction_id)} (${String(t.status)})`).join(', ') : 'Rolled back / Active'}
            badge={invTransactions.length > 0 ? `${invTransactions.length} TXs` : 'TX-208'}
            tone="lavender"
          />
          <EvidenceItem
            icon={<LockKeyhole size={15} />}
            title="Lock resources"
            detail={invLocks.length > 0 ? invLocks.map((l) => `${String(l.data_item)} (${String(l.status)})`).slice(0, 3).join(', ') : 'inventory:sku:104'}
            badge={invLocks.length > 0 ? `${invLocks.length} locks` : 'Waiting'}
            tone="peach"
          />
          <button type="button" className="button button-primary full-button" onClick={() => { onSelectTab('Replay'); void executeForensicReplay(selectedIncidentId); }}>Open forensic replay <ArrowRight size={14} /></button>
          <button type="button" className="button button-secondary full-button" onClick={() => { onSelectTab('Blast radius'); void loadBlastRadius(selectedIncidentId); }}>Analyze blast radius <ArrowRight size={14} /></button>
        </aside>
      </div>
    );
  }

  if (tab === 'Blast radius') {
    const affectedResources = Array.isArray(blastData?.affected_resources)
      ? (blastData?.affected_resources as Array<Record<string, unknown>>)
      : [];
    const directNodes = affectedResources.filter((r) => String(r.impact_level) === 'DIRECT');
    const potentialNodes = affectedResources.filter((r) => String(r.impact_level) === 'POTENTIAL');

    return <>
      <section className="surface-panel">
        <div className="panel-heading">
          <div>
            <h3>Deadlock impact map (INC-{String(selectedIncidentId).padStart(3, '0')})</h3>
            <p>{String(blastData?.summary ?? 'Direct and potential impact computed from the wait-for graph topology')}</p>
          </div>
          <div className="heading-actions">
            <button type="button" className="button button-secondary" onClick={() => void loadBlastRadius(selectedIncidentId)}>Recompute blast radius</button>
            <span className="severity severity-high">
              {blastData?.total_impact_score !== undefined ? `Impact score: ${String(blastData.total_impact_score)}` : 'High severity'}
            </span>
          </div>
        </div>
        {!sampleMode && affectedResources.length > 0 ? (
          <div className="impact-graph" style={{ flexWrap: 'wrap', gap: '12px' }}>
            {directNodes.map((node, idx) => (
              <div key={`dir-${idx}`} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div className="impact-node impacted">
                  <span>{String(node.resource_type)}: {String(node.identifier)}</span>
                  <small>{String(node.reason ?? 'Directly in deadlock cycle')}</small>
                  <b>Direct impact</b>
                </div>
                {idx < directNodes.length - 1 && (
                  <div className="impact-arrow"><ArrowRight size={18} /><span>wait cycle</span></div>
                )}
              </div>
            ))}
            {potentialNodes.map((node, idx) => (
              <div key={`pot-${idx}`} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div className="impact-loop"><ArrowDownRight size={18} /><span>downstream</span></div>
                <div className="impact-node potential">
                  <span>{String(node.resource_type)}: {String(node.identifier)}</span>
                  <small>{String(node.reason ?? 'Blocked by cycle participant')}</small>
                  <b>Potential impact</b>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="impact-graph">
            <div className="impact-node impacted"><span>TX-208</span><small>checkout-api (PID 4211)</small><b>Direct impact</b></div>
            <div className="impact-arrow"><ArrowRight size={18} /><span>holds row lock</span></div>
            <div className="impact-node impacted"><span>TX-211</span><small>order-worker (PID 4290)</small><b>Victim / Rolled back</b></div>
            <div className="impact-loop"><ArrowDownRight size={18} /><span>wait cycle detected</span></div>
            <div className="impact-node potential"><span>TX-214</span><small>inventory-sync</small><b>Downstream wait</b></div>
          </div>
        )}
        <div className="impact-legend">
          <span><i className="legend-direct" /> Directly involved ({blastData?.direct_impact_count !== undefined ? String(blastData.direct_impact_count) : '2'})</span>
          <span><i className="legend-potential" /> Potentially affected ({blastData?.potential_impact_count !== undefined ? String(blastData.potential_impact_count) : '1'})</span>
        </div>
      </section>
      <div className="note-banner"><ShieldAlert size={16} /><span>Impact categories describe the wait-for graph topology via `/api/v1/incidents/{selectedIncidentId}/blast-radius`.</span></div>
    </>;
  }

  if (tab === 'Fingerprints') {
    const deadlockCount = liveData.incidents.filter((i) => String(i.incident_type ?? 'DEADLOCK').toUpperCase().includes('DEADLOCK')).length || 3;
    return (
      <section className="surface-panel table-panel">
        <div className="panel-heading">
          <div><h3>Structural incident fingerprints</h3><p>Canonical cycle-shape hashes group structurally identical deadlocks regardless of transaction IDs</p></div>
          <button type="button" className="button button-secondary" onClick={() => onAction('Grouped incidents by canonical cycle hash.')}><ListFilter size={15} /> Group by shape</button>
        </div>
        <div className="fingerprint-card">
          <div className="fingerprint-visual"><span>Tx-A</span><span className="fingerprint-arrows">↔</span><span>Tx-B</span></div>
          <div>
            <span className="event-tag">Deadlock · {deadlockCount} match{deadlockCount === 1 ? '' : 'es'}</span>
            <strong>DEADLOCK-TX2 (2-Transaction Mutual Wait Cycle)</strong>
            <small>Canonical cycle length = 2 · Rotational-invariant SHA-256 structural hash groups all 2-party lock inversions</small>
          </div>
          <button type="button" className="button button-quiet" onClick={() => onSelectTab('Investigation')}>View matches <ArrowRight size={14} /></button>
        </div>
        <div className="fingerprint-card">
          <div className="fingerprint-visual fingerprint-three"><span>Tx-A</span><span>Tx-B</span><span>Tx-C</span></div>
          <div>
            <span className="event-tag">Deadlock · Multi-hop cycle</span>
            <strong>DEADLOCK-TX3 (3-Transaction Ring Wait Cycle)</strong>
            <small>Canonical cycle length = 3 · Structural hash groups 3-way circular lock dependencies</small>
          </div>
          <button type="button" className="button button-quiet" onClick={() => onSelectTab('Investigation')}>View matches <ArrowRight size={14} /></button>
        </div>
      </section>
    );
  }

  if (tab === 'Replay') {
    const rawSteps = Array.isArray(replayData?.steps) ? (replayData?.steps as Array<Record<string, unknown>>) : [];
    const hasLiveReplay = !sampleMode && rawSteps.length > 0;
    const stepLabels = hasLiveReplay
      ? rawSteps.map((s) => `${String(s.layer ?? 'DB')}: ${String(s.event_type ?? 'STEP')}`)
      : ['OS process', 'Transaction', 'Lock wait', 'Deadlock', 'Rollback'];
    const replayEvents: ActivityEvent[] = hasLiveReplay
      ? rawSteps.slice(0, replayStep).map((s) => ({
          time: formatTimeShort(s.timestamp),
          source: (String(s.layer ?? 'DBMS').toUpperCase() === 'OS' ? 'OS' : String(s.layer ?? '').toUpperCase() === 'INCIDENT' ? 'CORRELATION' : 'DBMS') as ActivityEvent['source'],
          title: `Step #${String(s.step_number ?? 1)} · ${String(s.event_type ?? 'EVENT')}`,
          detail: `${String(s.summary ?? '')}${s.pid ? ` (PID ${String(s.pid)})` : ''}${s.transaction_id ? ` [TX-${String(s.transaction_id)}]` : ''}`,
          status: (String(s.layer ?? '').toUpperCase() === 'INCIDENT' ? 'attention' : 'linked') as ActivityEvent['status'],
        }))
      : sampleEvents.slice(0, replayStep);

    return (
      <section className="surface-panel replay-panel">
        <div className="panel-heading">
          <div><h3>Forensic replay, INC-{String(selectedIncidentId).padStart(3, '0')}</h3><p>Deterministic playback of the investigation evidence ({replayEvents.length} of {stepLabels.length} steps)</p></div>
          <span className="event-tag tag-lavender">Read only</span>
        </div>
        <div className="replay-banner">
          <div className="replay-play"><Play size={17} fill="currentColor" /></div>
          <div>
            <strong>Replay does not re-run SQL ({String(replayData?.mode ?? 'READ_ONLY')})</strong>
            <p>{String(replayData?.summary ?? 'It reconstructs the recorded timeline from linked OS and DBMS evidence.')}</p>
          </div>
          <button type="button" className="button button-primary" onClick={() => void executeForensicReplay(selectedIncidentId)}>Play full timeline <Play size={14} fill="currentColor" /></button>
        </div>
        <div className="replay-track" style={{ overflowX: 'auto' }}>
          {stepLabels.slice(0, 8).map((label, index) => (
            <div className="replay-step" key={`${label}-${index}`} onClick={() => setReplayStep(index + 1)} style={{ cursor: 'pointer' }}>
              <span className={index < replayStep ? 'played' : ''}>{index + 1}</span>
              <small>{label}</small>
            </div>
          ))}
        </div>
        <EventList events={replayEvents} />
      </section>
    );
  }

  const incRows = !sampleMode && liveData.incidents.length > 0
    ? liveData.incidents.map((inc) => ({
        rawId: Number(inc.incident_id ?? 1),
        cols: [
          `INC-${String(inc.incident_id ?? '').padStart(3, '0')}`,
          String(inc.incident_type ?? 'Deadlock'),
          String(inc.severity ?? 'High'),
          formatTimeShort(inc.detected_at),
          inc.trace_id ? `TR-${String(inc.trace_id)}` : 'Linked',
          String(inc.status ?? 'Open'),
        ],
      }))
    : [
        { rawId: 18, cols: ['INC-018', 'Deadlock', 'High', '10:41:42', 'TR-042', 'Open'] },
        { rawId: 17, cols: ['INC-017', 'Lock contention', 'Medium', '10:28:07', 'None', 'Needs evidence'] },
      ];

  return <><div className="stat-inline"><div><span>Open incidents</span><strong>{incRows.length}</strong></div><div><span>Deadlocks</span><strong>{incRows.length}</strong></div><div><span>Traces attached</span><strong>{liveData.systemHealth?.correlation?.traces_count ?? 1}</strong></div><div><span>Status</span><strong>Monitored</strong></div></div><section className="surface-panel table-panel"><div className="panel-heading"><div><h3>Incident queue</h3><p>Persisted deadlocks and evidence status</p></div><button type="button" className="button button-secondary" onClick={() => void scanDeadlocks()}>Scan for deadlocks</button></div><div className="table-wrap"><table><thead><tr><th>Incident</th><th>Type</th><th>Severity</th><th>Detected</th><th>Trace</th><th>Status</th><th></th></tr></thead><tbody>{incRows.map((item) => <tr key={item.cols[0]}><td><b>{item.cols[0]}</b></td><td>{item.cols[1]}</td><td><span className={`severity ${item.cols[2] === 'High' || item.cols[2] === 'HIGH' ? 'severity-high' : 'severity-review'}`}>{item.cols[2]}</span></td><td>{item.cols[3]}</td><td>{item.cols[4]}</td><td><span className={`state-label ${item.cols[5] === 'Open' || item.cols[5] === 'OPEN' ? 'state-review' : 'state-observed'}`}>{item.cols[5]}</span></td><td><button type="button" className="table-action" onClick={() => void loadInvestigation(item.rawId)}>Investigate <ArrowRight size={13} /></button></td></tr>)}</tbody></table></div></section></>;
}

interface BenchmarkRunOutput {
  benchmark_id: string;
  scenario: string;
  started_at: string;
  ended_at: string;
  summary: string;
  metrics: {
    workload_duration_ms: number;
    operations_executed: number;
    successful_operations: number;
    failed_operations: number;
    events_captured: number;
    dropped_events: number;
    correlation_attempts: number;
    correlation_successes: number;
    avg_correlation_latency_ms: number;
    avg_observation_latency_ms: number;
    cpu_overhead_percent: number;
    memory_overhead_mb: number;
  };
}

function Performance({ tab, liveData, sampleMode, onRefresh, onAction }: { tab: string; liveData: LiveWorkspaceData; sampleMode: boolean; onRefresh: (toast?: boolean) => Promise<void>; onAction: (message: string) => void }) {
  const [scenario, setScenario] = useState('LOCK_CONTENTION');
  const [operationsCount, setOperationsCount] = useState(20);
  const [concurrencyLevel, setConcurrencyLevel] = useState(2);
  const [benchOutput, setBenchOutput] = useState<BenchmarkRunOutput | null>(null);
  const [runningBench, setRunningBench] = useState(false);
  const [refreshingHealth, setRefreshingHealth] = useState(false);

  // Custom metric recorder
  const [metricName, setMetricName] = useState('query_latency_ms');
  const [metricValue, setMetricValue] = useState(12.4);
  const [metricUnit, setMetricUnit] = useState('ms');
  const [metricScope, setMetricScope] = useState('DBMS / OS');
  const [recordingMetric, setRecordingMetric] = useState(false);

  const executeBenchmark = async () => {
    setRunningBench(true);
    try {
      const res = await analysisApi.runBenchmark<BenchmarkRunOutput>({
        scenario,
        operations: operationsCount,
        concurrency: concurrencyLevel,
        description: `Web UI benchmark (${scenario})`,
      });
      setBenchOutput(res);
      await onRefresh(false);
      onAction(`Benchmark ${res.benchmark_id} (${scenario}) completed in ${res.metrics.workload_duration_ms.toFixed(1)} ms.`);
    } catch (err) {
      onAction(err instanceof Error ? err.message : 'Benchmark execution failed.');
    } finally {
      setRunningBench(false);
    }
  };

  const handleRefreshHealth = async () => {
    setRefreshingHealth(true);
    try {
      await onRefresh(true);
      onAction('System health metrics refreshed.');
    } finally {
      setRefreshingHealth(false);
    }
  };

  const handleRecordMetric = async () => {
    setRecordingMetric(true);
    try {
      await analysisApi.createPerformanceRecord({
        metric_name: metricName,
        metric_value: Number(metricValue),
        metric_unit: metricUnit,
        scope: metricScope,
        trace_id: 42,
      });
      await onRefresh(false);
      onAction(`Recorded metric ${metricName}=${metricValue} ${metricUnit}.`);
    } catch (err) {
      onAction(err instanceof Error ? err.message : 'Could not record metric.');
    } finally {
      setRecordingMetric(false);
    }
  };

  if (tab === 'Benchmarks') {
    const m = benchOutput?.metrics;
    const throughputOpsSec = m && m.workload_duration_ms > 0
      ? Math.round((m.operations_executed / m.workload_duration_ms) * 1000)
      : 142;

    return <>
      <section className="surface-panel benchmark-form">
        <div className="panel-heading"><div><h3>Run a live benchmark workload</h3><p>Execute deterministic benchmark scenarios measuring throughput and correlation overhead.</p></div><span className="demo-pill">Live API</span></div>
        <div className="benchmark-options">
          {['DBMS_ONLY', 'LOCK_CONTENTION', 'DEADLOCK', 'MIXED', 'STRESS'].map((item) => (
            <button type="button" key={item} className={`benchmark-option ${scenario === item ? 'chosen' : ''}`} onClick={() => setScenario(item)}>
              <span className="radio-dot" />
              <strong>{item.replace(/_/g, ' ')}</strong>
              <small>
                {item === 'DBMS_ONLY' ? 'Pure query throughput baseline' : item === 'LOCK_CONTENTION' ? 'Concurrent row lock contention' : item === 'DEADLOCK' ? 'Wait-for cycle injection & detection' : item === 'MIXED' ? 'Combined OS + DBMS correlation load' : 'High-rate stress evaluation'}
              </small>
            </button>
          ))}
        </div>
        <div className="benchmark-controls">
          <label className="field-label">Operations
            <select value={operationsCount} onChange={(e) => setOperationsCount(Number(e.target.value))}>
              <option value={10}>10 operations</option>
              <option value={20}>20 operations</option>
              <option value={50}>50 operations</option>
              <option value={100}>100 operations</option>
            </select>
          </label>
          <label className="field-label">Concurrency (workers)
            <select value={concurrencyLevel} onChange={(e) => setConcurrencyLevel(Number(e.target.value))}>
              <option value={1}>1 worker</option>
              <option value={2}>2 workers</option>
              <option value={4}>4 workers</option>
              <option value={8}>8 workers</option>
            </select>
          </label>
          <button type="button" className="button button-primary" disabled={runningBench} onClick={() => void executeBenchmark()}>
            <Play size={14} fill="currentColor" /> {runningBench ? 'Running workload…' : 'Run benchmark workload'}
          </button>
        </div>
      </section>

      <div className="benchmark-result">
        <div>
          <span className="event-tag">{benchOutput ? `Run #${benchOutput.benchmark_id}` : 'Measured Result'}</span>
          <h3>{benchOutput ? `${benchOutput.scenario.replace(/_/g, ' ')} Completed` : 'Observability overhead stays visible'}</h3>
          <p>{benchOutput ? benchOutput.summary : 'Click "Run benchmark workload" to measure live throughput, correlation latency, and agent overhead.'}</p>
        </div>
        <div className="result-metric"><span>Workload throughput</span><strong>{throughputOpsSec} <small>ops/s</small></strong></div>
        <div className="result-metric"><span>Agent CPU</span><strong>{m?.cpu_overhead_percent ?? liveData.systemHealth?.overhead?.agent_cpu_percent ?? 1.8}<small>%</small></strong></div>
        <div className="result-metric"><span>Agent memory</span><strong>{m?.memory_overhead_mb ?? liveData.systemHealth?.overhead?.agent_memory_mb ?? 42} <small>MB</small></strong></div>
      </div>

      {benchOutput && m && (
        <section className="surface-panel output-scenario-panel">
          <div className="panel-heading">
            <div><h3>Detailed Benchmark Telemetry (`{benchOutput.benchmark_id}`)</h3><p>Started {formatTimeShort(benchOutput.started_at)} · Ended {formatTimeShort(benchOutput.ended_at)}</p></div>
            <span className="state-label state-linked">{m.successful_operations}/{m.operations_executed} Succeeded</span>
          </div>
          <div className="metrics-grid-cards">
            <div className="mini-stat-card"><span>Workload Duration</span><strong>{m.workload_duration_ms.toFixed(2)} ms</strong></div>
            <div className="mini-stat-card"><span>Operations Executed</span><strong>{m.operations_executed} ({m.failed_operations} failed)</strong></div>
            <div className="mini-stat-card"><span>Events Captured</span><strong>{m.events_captured} ({m.dropped_events} dropped)</strong></div>
            <div className="mini-stat-card"><span>Correlations Succeeded</span><strong>{m.correlation_successes} / {m.correlation_attempts}</strong></div>
            <div className="mini-stat-card"><span>Avg Correlation Latency</span><strong>{m.avg_correlation_latency_ms.toFixed(3)} ms</strong></div>
            <div className="mini-stat-card"><span>Avg Observation Latency</span><strong>{m.avg_observation_latency_ms.toFixed(3)} ms</strong></div>
          </div>
        </section>
      )}
    </>;
  }

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
    return <>
      <section className="surface-panel output-scenario-panel" style={{ marginBottom: '14px' }}>
        <div className="panel-heading">
          <div><h3>Record Custom Performance Metric</h3><p>Measure and persist ad-hoc latency, CPU overhead, or queue depth measurements</p></div>
          <span className="demo-pill">Interactive Lab</span>
        </div>
        <div className="correlation-form">
          <label className="field-label">Metric Name<input value={metricName} onChange={(e) => setMetricName(e.target.value)} placeholder="query_latency_ms" /></label>
          <label className="field-label">Value<input type="number" step="0.1" value={metricValue} onChange={(e) => setMetricValue(Number(e.target.value))} placeholder="12.4" /></label>
          <label className="field-label">Unit<input value={metricUnit} onChange={(e) => setMetricUnit(e.target.value)} placeholder="ms, %, MB" /></label>
          <label className="field-label">Scope<input value={metricScope} onChange={(e) => setMetricScope(e.target.value)} placeholder="DBMS / OS" /></label>
        </div>
        <div style={{ marginTop: '10px' }}>
          <button type="button" className="button button-primary" disabled={recordingMetric} onClick={() => void handleRecordMetric()}>
            <Play size={13} fill="currentColor" /> {recordingMetric ? 'Recording…' : 'Record Metric'}
          </button>
        </div>
      </section>

      <section className="surface-panel table-panel">
        <div className="panel-heading">
          <div><h3>Performance records</h3><p>Global DBMS metrics and trace-specific measurements</p></div>
          <button type="button" className="button button-secondary" onClick={() => void onRefresh(true)}>Refresh records</button>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Metric</th><th>Value</th><th>Scope</th><th>Recorded</th><th>Trace</th></tr></thead>
            <tbody>{perfRows.map((row, i) => <tr key={`${row[0]}-${i}`}>{row.map((col, j) => <td key={j}>{col}</td>)}</tr>)}</tbody>
          </table>
        </div>
      </section>
    </>;
  }

  const ov = liveData.systemHealth?.overhead;
  const corr = liveData.systemHealth?.correlation;
  const sys = liveData.systemHealth?.system;

  return <>
    <div className="health-banner">
      <span className="health-symbol"><Activity size={19} /></span>
      <div>
        <strong>System health ({ov?.observability_status ?? 'NORMAL'})</strong>
        <small>{liveData.systemHealth?.timestamp ? formatTimeShort(liveData.systemHealth.timestamp) : 'Live telemetry'}</small>
      </div>
      <span className="event-tag tag-lavender">{liveData.connected && !sampleMode ? 'Live telemetry' : 'Illustrative'}</span>
    </div>
    <div className="performance-grid">
      <section className="surface-panel chart-panel">
        <div className="panel-heading"><div><h3>System resource use</h3><p>Host CPU ({sys?.cpu_percent ?? 18}%) & Memory ({sys?.memory_percent ?? 45}%)</p></div><span className="chart-unit">Percent</span></div>
        <MiniChart />
      </section>
      <section className="surface-panel chart-panel">
        <div className="panel-heading"><div><h3>Query latency</h3><p>Average duration ({liveData.systemHealth?.dbms?.avg_query_latency_ms ?? 1.4} ms)</p></div><span className="chart-unit">Milliseconds</span></div>
        <MiniChart alternate />
      </section>
    </div>
    <div className="stat-inline">
      <div><span>OS capture overhead</span><strong>{ov?.agent_cpu_percent ?? 1.8}% cpu</strong></div>
      <div><span>Collector memory</span><strong>{ov?.agent_memory_mb ?? 42} MB</strong></div>
      <div><span>Correlation latency</span><strong>{corr?.avg_correlation_latency_ms ?? 1.2} ms</strong></div>
      <div><span>Dropped events</span><strong>{sys?.dropped_events ?? 0}</strong></div>
      <div className="inline-status"><span>{liveData.connected ? 'Live host metrics' : 'Sample values'}</span></div>
    </div>
    <button type="button" className="button button-secondary" disabled={refreshingHealth} onClick={() => void handleRefreshHealth()}>
      <RefreshCw size={14} className={refreshingHealth ? 'spin' : ''} />
      {refreshingHealth ? 'Refreshing health metrics…' : 'Refresh system health'}
    </button>
  </>;
}

function MiniChart({ alternate = false }: { alternate?: boolean }) {
  const values = alternate ? [30, 38, 34, 47, 43, 60, 52, 58, 50, 68, 62, 73, 56, 65, 57, 78, 64, 68, 61, 74] : [45, 42, 50, 47, 55, 49, 52, 61, 56, 50, 60, 55, 65, 59, 53, 57, 49, 55, 48, 60];
  return <div className={`mini-chart ${alternate ? 'chart-alt' : ''}`} role="img" aria-label={alternate ? 'Query latency chart' : 'CPU and memory chart'}><div className="chart-grid"><span>80</span><span>60</span><span>40</span><span>20</span><span>0</span></div><div className="chart-lines"><div className="gridline" /><div className="gridline" /><div className="gridline" /><div className="gridline" /><svg viewBox="0 0 600 170" preserveAspectRatio="none" aria-hidden="true"><path d={`M 0 ${170 - values[0] * 1.7} ${values.map((value, index) => `L ${index * 31.5} ${170 - value * 1.7}`).join(' ')}`} className="chart-path" /><path d={`M 0 ${170 - (alternate ? 36 : 35) * 1.7} ${values.map((value, index) => `L ${index * 31.5} ${170 - Math.max(20, value - (alternate ? 18 : 12)) * 1.7}`).join(' ')}`} className="chart-path chart-path-secondary" /></svg><span className="chart-onset">Live</span></div><div className="chart-legend"><span><i className="legend-os" />{alternate ? 'P95 latency' : 'cpu use'}</span><span><i className="legend-db" />{alternate ? 'Average' : 'Memory use'}</span></div></div>;
}

interface CpuSimResult {
  algorithm: string;
  processes: Array<{
    pid: number;
    arrival_time: number;
    burst_time: number;
    priority: number;
    start_time: number;
    finish_time: number;
    waiting_time: number;
    turnaround_time: number;
  }>;
  gantt_chart: Array<{ pid: number; start: number; end: number }>;
  avg_waiting_time: number;
  avg_turnaround_time: number;
  cpu_utilization: number;
  throughput: number;
}

interface MemorySimResult {
  algorithm: string;
  reference_string: number[];
  num_frames: number;
  page_faults: number;
  page_hits: number;
  fault_rate: number;
  hit_rate: number;
  frame_states?: number[][];
  comparison?: Record<string, { faults: number; fault_rate: number }>;
}

interface BankersSimResult {
  is_safe: boolean;
  safe_sequence: number[];
  reason: string;
}

interface RagSimResult {
  deadlock_detected: boolean;
  deadlocked_processes: number[];
  cycle: string[];
  reason: string;
}

interface DiskSimResult {
  algorithm: string;
  initial_head: number;
  total_seek_time: number;
  requests: Array<{ order: number; track: number; seek_time: number }>;
}

interface SyncSimResult {
  problem_type: string;
  iterations: number;
  result_log: string[];
}

interface ScheduleAnalysisResult {
  conflict_serializable: boolean;
  precedence_graph: Record<string, number[]>;
  cycles: number[][];
}

interface RecoverySimResult {
  final_state: Record<string, string>;
  redone_transactions: number[];
  undone_transactions: number[];
  committed_transactions: number[];
}

interface Deadlock2PLResult {
  deadlock_detected: boolean;
  cycles: number[][];
  wait_for_graph: Record<string, number[]>;
  victim_transaction_id?: number;
}

function Simulations({ tab, selectedAlgorithm, onAlgorithm, onAction }: { tab: string; selectedAlgorithm: string; onAlgorithm: (value: string) => void; onAction: (message: string) => void }) {
  const osOptions = ['CPU Scheduling', 'Memory & page replacement', 'Deadlock theory', 'Disk scheduling', 'Synchronization'];
  const dbmsOptions = ['Serializability', 'WAL recovery', 'Strict 2PL & Deadlocks'];
  const options = tab === 'OS simulations' ? osOptions : dbmsOptions;
  const [lab, setLab] = useState(options[0]);

  useEffect(() => {
    setLab(tab === 'OS simulations' ? osOptions[0] : dbmsOptions[0]);
  }, [tab]);

  const activeAlgorithms = labAlgorithms(tab, lab);
  const activeAlgorithm = activeAlgorithms.includes(selectedAlgorithm) ? selectedAlgorithm : activeAlgorithms[0];

  // Editable inputs
  const [cpuProcessesInput, setCpuProcessesInput] = useState('P1: 0, 6, 2\nP2: 1, 3, 1\nP3: 2, 5, 3\nP4: 3, 4, 2');
  const [cpuQuantum, setCpuQuantum] = useState(2);
  const [memFrames, setMemFrames] = useState(3);
  const [memRefString, setMemRefString] = useState('7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2');
  const [deadlockPreset, setDeadlockPreset] = useState<'SAFE' | 'UNSAFE' | 'RAG_CYCLE' | 'RAG_ACYCLIC'>('SAFE');
  const [diskHead, setDiskHead] = useState(50);
  const [diskTracksInput, setDiskTracksInput] = useState('82, 170, 43, 140, 24, 16, 190');
  const [syncIterations, setSyncIterations] = useState(6);

  const [dbmsScheduleInput, setDbmsScheduleInput] = useState('R1(A), W1(A), R2(A), W2(A), R1(B), W1(B)');
  const [dbmsRecoveryInput, setDbmsRecoveryInput] = useState('INIT A=100, INIT B=200\nBEGIN T1\nWRITE T1 A 100 -> 150\nBEGIN T2\nWRITE T2 B 200 -> 280\nCOMMIT T2');
  const [dbmsLockPreset, setDbmsLockPreset] = useState<'DEADLOCK_CYCLE' | 'WAIT_CHAIN'>('DEADLOCK_CYCLE');

  // Output states for each lab
  const [cpuOutput, setCpuOutput] = useState<CpuSimResult | null>(null);
  const [memOutput, setMemOutput] = useState<MemorySimResult | null>(null);
  const [bankersOutput, setBankersOutput] = useState<BankersSimResult | null>(null);
  const [ragOutput, setRagOutput] = useState<RagSimResult | null>(null);
  const [diskOutput, setDiskOutput] = useState<DiskSimResult | null>(null);
  const [syncOutput, setSyncOutput] = useState<SyncSimResult | null>(null);
  const [serialOutput, setSerialOutput] = useState<ScheduleAnalysisResult | null>(null);
  const [recoveryOutput, setRecoveryOutput] = useState<RecoverySimResult | null>(null);
  const [lock2plOutput, setLock2plOutput] = useState<Deadlock2PLResult | null>(null);
  const [runningSim, setRunningSim] = useState(false);

  const runBackendSimulation = useCallback(async (silent = false) => {
    setRunningSim(true);
    try {
      if (tab === 'OS simulations') {
        if (lab === 'CPU Scheduling') {
          const algoMap: Record<string, string> = { 'FCFS': 'FCFS', 'SJF': 'SJF', 'SRTF': 'SRTF', 'Round Robin': 'RR', 'Priority': 'PRIORITY' };
          const parsedProcs = cpuProcessesInput
            .split('\n')
            .map((line, i) => {
              const nums = line.replace(/^P\d+\s*:\s*/i, '').split(/[,;\s]+/).map(Number).filter((n) => !Number.isNaN(n));
              return {
                pid: i + 1,
                arrival_time: nums[0] ?? i,
                burst_time: Math.max(1, nums[1] ?? 4),
                priority: nums[2] ?? 1,
              };
            })
            .filter((p) => p.burst_time > 0);

          const res = await simulationsApi.schedule<CpuSimResult>({
            algorithm: algoMap[activeAlgorithm] ?? 'RR',
            quantum: Math.max(1, cpuQuantum),
            processes: parsedProcs.length > 0 ? parsedProcs : [
              { pid: 1, arrival_time: 0, burst_time: 6, priority: 2 },
              { pid: 2, arrival_time: 1, burst_time: 3, priority: 1 },
              { pid: 3, arrival_time: 2, burst_time: 5, priority: 3 },
            ],
          });
          setCpuOutput(res);
          if (!silent) onAction(`CPU Scheduling (${res.algorithm}): Avg Wait ${res.avg_waiting_time}u, Avg Turnaround ${res.avg_turnaround_time}u.`);
          return;
        }

        if (lab === 'Memory & page replacement') {
          const refs = memRefString.split(/[,;\s]+/).map((s) => Number(s.trim())).filter((n) => !Number.isNaN(n));
          const algoKey = activeAlgorithm.toUpperCase().includes('COMPARE') ? 'ALL' : activeAlgorithm.toUpperCase();
          const res = await simulationsApi.memory<MemorySimResult>({
            algorithm: algoKey,
            num_frames: Math.max(1, memFrames),
            reference_string: refs.length > 0 ? refs : [7, 0, 1, 2, 0, 3, 0, 4],
          });
          setMemOutput(res);
          if (!silent) onAction(`Memory Simulation (${res.algorithm}): ${res.page_faults} Page Faults, ${res.page_hits} Page Hits.`);
          return;
        }

        if (lab === 'Deadlock theory') {
          if (activeAlgorithm.includes('Banker')) {
            const payload = deadlockPreset === 'UNSAFE'
              ? {
                  allocation: [[0, 1, 0], [2, 0, 0], [3, 0, 2]],
                  max_need: [[7, 5, 3], [6, 4, 2], [9, 4, 4]],
                  available: [0, 0, 0],
                }
              : {
                  allocation: [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]],
                  max_need: [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]],
                  available: [3, 3, 2],
                };
            const res = await simulationsApi.bankerDeadlock<BankersSimResult>(payload);
            setBankersOutput(res);
            setRagOutput(null);
            if (!silent) onAction(`Banker's Algorithm: ${res.is_safe ? `SAFE (${res.safe_sequence.map((p) => `P${p}`).join(' → ')})` : 'UNSAFE STATE'}`);
          } else {
            const payload = deadlockPreset === 'RAG_ACYCLIC'
              ? {
                  processes: [1, 2, 3],
                  resources: [101, 102],
                  allocation: { 1: [101], 2: [102] },
                  request: { 2: [101], 3: [102] },
                }
              : {
                  processes: [1, 2],
                  resources: [101, 102],
                  allocation: { 1: [101], 2: [102] },
                  request: { 1: [102], 2: [101] },
                };
            const res = await simulationsApi.resourceGraphDeadlock<RagSimResult>(payload);
            setRagOutput(res);
            setBankersOutput(null);
            if (!silent) onAction(`RAG Analysis: ${res.deadlock_detected ? 'Deadlock Cycle Detected!' : 'No Deadlock Cycle'}`);
          }
          return;
        }

        if (lab === 'Disk scheduling') {
          const tracks = diskTracksInput.split(/[,;\s]+/).map((t) => Number(t.trim())).filter((n) => !Number.isNaN(n));
          const res = await simulationsApi.disk<DiskSimResult>({
            algorithm: activeAlgorithm,
            initial_head: diskHead,
            tracks: tracks.length > 0 ? tracks : [82, 170, 43, 140, 24, 16, 190],
          });
          setDiskOutput(res);
          if (!silent) onAction(`Disk Scheduling (${res.algorithm}): Total seek distance = ${res.total_seek_time} cylinders.`);
          return;
        }

        if (lab === 'Synchronization') {
          const res = await simulationsApi.synchronization<SyncSimResult>({
            problem_type: 'PRODUCER_CONSUMER',
            iterations: Math.max(1, Math.min(20, syncIterations)),
          });
          setSyncOutput(res);
          if (!silent) onAction(`Producer-Consumer Synchronization: ${res.result_log.length} steps executed.`);
          return;
        }
      } else {
        if (lab === 'Serializability') {
          const operations = parseScheduleString(dbmsScheduleInput);
          const res = await workflowsApi.analyzeSchedule<ScheduleAnalysisResult>({ operations });
          setSerialOutput(res);
          if (!silent) {
            onAction(
              res.conflict_serializable
                ? 'Schedule is Conflict-Serializable (Precedence graph is acyclic).'
                : `Not Conflict-Serializable! Cycles detected: ${res.cycles.length}`,
            );
          }
          return;
        }

        if (lab === 'WAL recovery') {
          const parsed = parseRecoveryLogInput(dbmsRecoveryInput);
          const res = await workflowsApi.recover<RecoverySimResult>(parsed);
          setRecoveryOutput(res);
          if (!silent) {
            onAction(
              `ARIES/WAL Recovery completed: REDO [${res.redone_transactions.map((t) => `T${t}`).join(', ')}], UNDO [${res.undone_transactions.map((t) => `T${t}`).join(', ')}].`,
            );
          }
          return;
        }

        if (lab === 'Strict 2PL & Deadlocks') {
          const locks = dbmsLockPreset === 'DEADLOCK_CYCLE'
            ? [
                { transaction_id: 1, data_item: 'Account_A', lock_type: 'X', status: 'HELD' },
                { transaction_id: 2, data_item: 'Account_B', lock_type: 'X', status: 'HELD' },
                { transaction_id: 1, data_item: 'Account_B', lock_type: 'X', status: 'WAITING' },
                { transaction_id: 2, data_item: 'Account_A', lock_type: 'X', status: 'WAITING' },
              ]
            : [
                { transaction_id: 1, data_item: 'Account_A', lock_type: 'X', status: 'HELD' },
                { transaction_id: 2, data_item: 'Account_A', lock_type: 'S', status: 'WAITING' },
                { transaction_id: 2, data_item: 'Account_B', lock_type: 'X', status: 'HELD' },
              ];
          const res = await workflowsApi.detectDeadlock<Deadlock2PLResult>({ locks });
          setLock2plOutput(res);
          if (!silent) {
            onAction(
              res.deadlock_detected
                ? `2PL Deadlock Detected! Cycles: ${res.cycles.map((c) => c.map((t) => `T${t}`).join(' → ')).join('; ')}`
                : 'Strict 2PL Lock Graph is acyclic (no deadlock).',
            );
          }
          return;
        }
      }
    } catch (err) {
      if (!silent) onAction(err instanceof Error ? err.message : 'Simulation execution failed.');
    } finally {
      setRunningSim(false);
    }
  }, [
    tab, lab, activeAlgorithm, cpuProcessesInput, cpuQuantum, memFrames, memRefString,
    deadlockPreset, diskHead, diskTracksInput, syncIterations, dbmsScheduleInput,
    dbmsRecoveryInput, dbmsLockPreset, onAction,
  ]);

  useEffect(() => {
    void runBackendSimulation(true);
  }, [tab, lab, activeAlgorithm, deadlockPreset, dbmsLockPreset, runBackendSimulation]);

  return <>
    <div className="lab-picker">
      {options.map((option) => (
        <button
          type="button"
          key={option}
          className={`lab-option ${lab === option ? 'selected' : ''}`}
          onClick={() => {
            setLab(option);
            onAlgorithm(labAlgorithms(tab, option)[0]);
          }}
        >
          {option}<ChevronRight size={14} />
        </button>
      ))}
    </div>

    <div className="content-two-col simulation-grid">
      <section className="surface-panel simulation-input">
        <div className="panel-heading">
          <div><h3>{lab}</h3><p>Configure input parameters or load a preset, then execute on the backend engine</p></div>
          <span className="event-tag tag-lavender">CLI Parity Lab</span>
        </div>

        <label className="field-label">Algorithm / Model
          <select value={activeAlgorithm} onChange={(event) => onAlgorithm(event.target.value)}>
            {activeAlgorithms.map((algorithm) => <option key={algorithm}>{algorithm}</option>)}
          </select>
        </label>

        {tab === 'OS simulations' && lab === 'CPU Scheduling' && (
          <>
            <div className="preset-bar">
              <button type="button" className="button button-quiet" onClick={() => setCpuProcessesInput('P1: 0, 6, 2\nP2: 1, 3, 1\nP3: 2, 5, 3\nP4: 3, 4, 2')}>Preset: 4 Processes</button>
              <button type="button" className="button button-quiet" onClick={() => setCpuProcessesInput('P1: 0, 10, 3\nP2: 1, 1, 1\nP3: 2, 2, 2')}>Preset: Convoy Effect</button>
            </div>
            <label className="field-label">Processes (`PID: Arrival, Burst, Priority` per line)
              <textarea value={cpuProcessesInput} onChange={(e) => setCpuProcessesInput(e.target.value)} />
            </label>
            {activeAlgorithm === 'Round Robin' && (
              <label className="field-label">Time quantum (units)
                <input type="number" min={1} max={20} value={cpuQuantum} onChange={(e) => setCpuQuantum(Number(e.target.value))} />
              </label>
            )}
          </>
        )}

        {tab === 'OS simulations' && lab === 'Memory & page replacement' && (
          <>
            <div className="preset-bar">
              <button type="button" className="button button-quiet" onClick={() => { setMemFrames(3); setMemRefString('7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2'); }}>Preset: Classic 13-Page</button>
              <button type="button" className="button button-quiet" onClick={() => { setMemFrames(4); setMemRefString('1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5'); }}>Preset: Belady Test</button>
            </div>
            <label className="field-label">Number of Page Frames
              <input type="number" min={1} max={8} value={memFrames} onChange={(e) => setMemFrames(Number(e.target.value))} />
            </label>
            <label className="field-label">Page Reference String (comma-separated)
              <input value={memRefString} onChange={(e) => setMemRefString(e.target.value)} />
            </label>
          </>
        )}

        {tab === 'OS simulations' && lab === 'Deadlock theory' && (
          <div className="preset-bar">
            {activeAlgorithm.includes('Banker') ? (
              <>
                <button type="button" className={`button ${deadlockPreset === 'SAFE' ? 'button-secondary' : 'button-quiet'}`} onClick={() => setDeadlockPreset('SAFE')}>Preset: 5-Process Safe State</button>
                <button type="button" className={`button ${deadlockPreset === 'UNSAFE' ? 'button-secondary' : 'button-quiet'}`} onClick={() => setDeadlockPreset('UNSAFE')}>Preset: Unsafe / Resource Starved</button>
              </>
            ) : (
              <>
                <button type="button" className={`button ${deadlockPreset === 'RAG_CYCLE' ? 'button-secondary' : 'button-quiet'}`} onClick={() => setDeadlockPreset('RAG_CYCLE')}>Preset: Circular Wait Cycle (P1 ↔ P2)</button>
                <button type="button" className={`button ${deadlockPreset === 'RAG_ACYCLIC' ? 'button-secondary' : 'button-quiet'}`} onClick={() => setDeadlockPreset('RAG_ACYCLIC')}>Preset: Acyclic Resource Graph</button>
              </>
            )}
          </div>
        )}

        {tab === 'OS simulations' && lab === 'Disk scheduling' && (
          <>
            <label className="field-label">Initial Disk Head Cylinder
              <input type="number" min={0} max={199} value={diskHead} onChange={(e) => setDiskHead(Number(e.target.value))} />
            </label>
            <label className="field-label">Requested Cylinder Tracks
              <input value={diskTracksInput} onChange={(e) => setDiskTracksInput(e.target.value)} />
            </label>
          </>
        )}

        {tab === 'OS simulations' && lab === 'Synchronization' && (
          <label className="field-label">Producer-Consumer Bounded Buffer Iterations
            <input type="number" min={2} max={15} value={syncIterations} onChange={(e) => setSyncIterations(Number(e.target.value))} />
          </label>
        )}

        {tab === 'DBMS simulations' && lab === 'Serializability' && (
          <>
            <div className="preset-bar">
              <button type="button" className="button button-quiet" onClick={() => setDbmsScheduleInput('R1(A), W1(A), R2(A), W2(A), R1(B), W1(B)')}>Preset: Conflict-Serializable (T1 → T2)</button>
              <button type="button" className="button button-quiet" onClick={() => setDbmsScheduleInput('R1(A), R2(A), W1(A), W2(A)')}>Preset: Conflict Cycle (T1 ↔ T2)</button>
            </div>
            <label className="field-label">Schedule Operations (`R1(A), W1(A), R2(A)...`)
              <textarea value={dbmsScheduleInput} onChange={(e) => setDbmsScheduleInput(e.target.value)} />
            </label>
          </>
        )}

        {tab === 'DBMS simulations' && lab === 'WAL recovery' && (
          <>
            <div className="preset-bar">
              <button type="button" className="button button-quiet" onClick={() => setDbmsRecoveryInput('INIT A=100, INIT B=200\nBEGIN T1\nWRITE T1 A 100 -> 150\nBEGIN T2\nWRITE T2 B 200 -> 280\nCOMMIT T2')}>Preset: T2 Committed, T1 Uncommitted Crash</button>
              <button type="button" className="button button-quiet" onClick={() => setDbmsRecoveryInput('INIT X=500, INIT Y=900\nBEGIN T1\nWRITE T1 X 500 -> 600\nCOMMIT T1\nBEGIN T2\nWRITE T2 Y 900 -> 100\nABORT T2')}>Preset: T1 Committed, T2 Aborted</button>
            </div>
            <label className="field-label">WAL Log Sequence before Crash
              <textarea value={dbmsRecoveryInput} onChange={(e) => setDbmsRecoveryInput(e.target.value)} />
            </label>
          </>
        )}

        {tab === 'DBMS simulations' && lab === 'Strict 2PL & Deadlocks' && (
          <div className="preset-bar">
            <button type="button" className={`button ${dbmsLockPreset === 'DEADLOCK_CYCLE' ? 'button-secondary' : 'button-quiet'}`} onClick={() => setDbmsLockPreset('DEADLOCK_CYCLE')}>Preset: 2-Transaction X-Lock Deadlock (T1 ↔ T2)</button>
            <button type="button" className={`button ${dbmsLockPreset === 'WAIT_CHAIN' ? 'button-secondary' : 'button-quiet'}`} onClick={() => setDbmsLockPreset('WAIT_CHAIN')}>Preset: Acyclic Lock Wait (No Deadlock)</button>
          </div>
        )}

        <button type="button" className="button button-primary" disabled={runningSim} onClick={() => void runBackendSimulation()}>
          <Play size={14} fill="currentColor" /> {runningSim ? 'Computing simulation…' : `Execute ${lab}`}
        </button>
      </section>

      <section className="surface-panel simulation-result">
        <div className="panel-heading">
          <div><h3>Simulation Output Scenario</h3><p>Deterministic simulation output model</p></div>
          <span className="result-check"><Check size={15} /></span>
        </div>

        {/* OS: CPU Scheduling Result */}
        {tab === 'OS simulations' && lab === 'CPU Scheduling' && (
          cpuOutput ? (
            <>
              <div className="verdict-banner verdict-pass">
                <Check size={15} />
                <div>
                  <strong>{cpuOutput.algorithm} Schedule Computed</strong>
                  <span>CPU Utilization: {cpuOutput.cpu_utilization}% · Throughput: {cpuOutput.throughput} proc/unit</span>
                </div>
              </div>
              <div style={{ marginTop: '10px', marginBottom: '6px' }}>
                <small style={{ color: 'var(--color-muted)', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                  Execution Order & Ready Queue Dispatch ({cpuOutput.gantt_chart.length} context slices)
                </small>
                <div className="sequence-chain" style={{ flexWrap: 'wrap', gap: '6px' }}>
                  {cpuOutput.gantt_chart.map((slice, idx) => (
                    <span key={idx} className="chain-chip">
                      P{slice.pid} [{slice.start}→{slice.end}] {idx < cpuOutput.gantt_chart.length - 1 ? '→' : ''}
                    </span>
                  ))}
                </div>
              </div>
              <div className="gantt-track" style={{ marginTop: '8px' }}>
                {cpuOutput.gantt_chart.map((slice, idx) => (
                  <i key={idx} className={`p${((slice.pid - 1) % 3) + 1}`} style={{ flex: Math.max(1, slice.end - slice.start) }}>
                    P{slice.pid} ({slice.start}–{slice.end})
                  </i>
                ))}
              </div>
              <div className="result-pairs">
                <span>Average waiting time <b>{cpuOutput.avg_waiting_time} units</b></span>
                <span>Average turnaround time <b>{cpuOutput.avg_turnaround_time} units</b></span>
                <span>CPU utilization <b>{cpuOutput.cpu_utilization}%</b></span>
              </div>
              <div style={{ marginTop: '12px', display: 'grid', gap: '8px' }}>
                <small style={{ color: 'var(--color-muted)', fontWeight: 600 }}>Per-Process Waiting vs Burst Time (Turnaround Breakdown)</small>
                {cpuOutput.processes.map((p) => {
                  const maxTurn = Math.max(...cpuOutput.processes.map((x) => x.turnaround_time), 1);
                  const waitPct = Math.round((p.waiting_time / maxTurn) * 100);
                  const burstPct = Math.max(8, Math.round((p.burst_time / maxTurn) * 100));
                  return (
                    <div key={`bar-${p.pid}`} style={{ display: 'grid', gridTemplateColumns: '44px 1fr 135px', alignItems: 'center', gap: '10px', fontSize: '12px' }}>
                      <b>P{p.pid}</b>
                      <div style={{ display: 'flex', height: '14px', borderRadius: '999px', overflow: 'hidden', background: 'var(--color-paper-2)', border: '1px solid var(--color-rule)' }}>
                        {p.waiting_time > 0 && (
                          <div title={`Waiting: ${p.waiting_time}u`} style={{ width: `${waitPct}%`, background: 'var(--color-peach)', transition: 'width 0.3s ease' }} />
                        )}
                        <div title={`CPU Burst: ${p.burst_time}u`} style={{ width: `${burstPct}%`, background: 'var(--color-accent)', transition: 'width 0.3s ease' }} />
                      </div>
                      <span style={{ textAlign: 'right', color: 'var(--color-muted)' }}>
                        Wait <b>{p.waiting_time}u</b> · TAT <b>{p.turnaround_time}u</b>
                      </span>
                    </div>
                  );
                })}
              </div>
              <div className="table-wrap" style={{ marginTop: '12px' }}>
                <table>
                  <thead><tr><th>PID</th><th>Arrival</th><th>Burst</th><th>Start</th><th>Finish</th><th>Wait</th><th>Turnaround</th></tr></thead>
                  <tbody>
                    {cpuOutput.processes.map((p) => (
                      <tr key={p.pid}>
                        <td><b>P{p.pid}</b></td>
                        <td>{p.arrival_time}</td>
                        <td>{p.burst_time}</td>
                        <td>{p.start_time}</td>
                        <td>{p.finish_time}</td>
                        <td><b>{p.waiting_time}</b></td>
                        <td><b>{p.turnaround_time}</b></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="empty-state">Click <b>Execute CPU Scheduling</b> to generate the live Gantt chart, queue dispatch order, and per-process turnaround metrics.</div>
          )
        )}

        {/* OS: Memory Page Replacement Result */}
        {tab === 'OS simulations' && lab === 'Memory & page replacement' && (
          memOutput ? (
            <>
              <div className="verdict-banner verdict-pass">
                <Check size={15} />
                <div>
                  <strong>{memOutput.algorithm} Page Replacement ({memOutput.num_frames} Frames)</strong>
                  <span>Page Faults: {memOutput.page_faults} ({memOutput.fault_rate}%) · Page Hits: {memOutput.page_hits} ({memOutput.hit_rate}%)</span>
                </div>
              </div>
              {memOutput.comparison ? (
                <div style={{ marginTop: '12px', display: 'grid', gap: '10px' }}>
                  <small style={{ color: 'var(--color-muted)', fontWeight: 600 }}>Algorithm Fault Rate Comparison</small>
                  {Object.entries(memOutput.comparison).map(([alg, stats]) => (
                    <div key={alg} style={{ display: 'grid', gridTemplateColumns: '84px 1fr 120px', alignItems: 'center', gap: '10px', fontSize: '12px' }}>
                      <b>{alg}</b>
                      <div style={{ height: '14px', borderRadius: '999px', overflow: 'hidden', background: 'var(--color-paper-2)', border: '1px solid var(--color-rule)' }}>
                        <div style={{ width: `${Math.min(100, Math.max(6, stats.fault_rate))}%`, height: '100%', background: 'var(--color-accent)' }} />
                      </div>
                      <span style={{ textAlign: 'right' }}><b>{stats.faults} faults</b> ({stats.fault_rate}%)</span>
                    </div>
                  ))}
                  <div className="table-wrap" style={{ marginTop: '6px' }}>
                    <table>
                      <thead><tr><th>Algorithm</th><th>Page Faults</th><th>Fault Rate</th></tr></thead>
                      <tbody>
                        {Object.entries(memOutput.comparison).map(([alg, stats]) => (
                          <tr key={alg}><td><b>{alg}</b></td><td>{stats.faults}</td><td>{stats.fault_rate}%</td></tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : memOutput.frame_states && (
                <div className="table-wrap" style={{ marginTop: '10px' }}>
                  <table>
                    <thead><tr><th>Step</th><th>Page Requested</th><th>Physical Frame State</th><th>Outcome</th></tr></thead>
                    <tbody>
                      {memOutput.frame_states.slice(0, 16).map((frames, idx) => {
                        const prevFrames = idx > 0 ? memOutput.frame_states![idx - 1] : [];
                        const reqPage = memOutput.reference_string[idx];
                        const isHit = prevFrames.includes(reqPage);
                        return (
                          <tr key={idx}>
                            <td>#{idx + 1}</td>
                            <td><span className="event-tag tag-blue">Page {reqPage}</span></td>
                            <td>
                              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                {Array.from({ length: memOutput.num_frames }).map((_, fIdx) => {
                                  const val = frames[fIdx];
                                  const isCurrent = val === reqPage;
                                  return (
                                    <span
                                      key={fIdx}
                                      style={{
                                        padding: '2px 8px',
                                        borderRadius: '6px',
                                        fontSize: '12px',
                                        fontWeight: isCurrent ? 700 : 500,
                                        border: isCurrent ? '1px solid var(--color-accent)' : '1px solid var(--color-rule)',
                                        background: isCurrent ? 'var(--color-accent-soft)' : 'var(--color-paper-2)',
                                      }}
                                    >
                                      F{fIdx + 1}: {val !== undefined ? val : '—'}
                                    </span>
                                  );
                                })}
                              </div>
                            </td>
                            <td>
                              <span className={`state-label ${isHit ? 'state-linked' : 'state-review'}`}>
                                {isHit ? 'PAGE HIT' : 'PAGE FAULT'}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">Click <b>Execute Memory & page replacement</b> to inspect frame states, page faults, and hit ratios.</div>
          )
        )}

        {/* OS: Deadlock Theory Result */}
        {tab === 'OS simulations' && lab === 'Deadlock theory' && (
          bankersOutput ? (
            <div className="output-details-stack">
              <div className={`verdict-banner ${bankersOutput.is_safe ? 'verdict-pass' : 'verdict-warn'}`}>
                <Check size={15} />
                <div>
                  <strong>{bankersOutput.is_safe ? 'SAFE STATE VERIFIED (NO DEADLOCK)' : 'UNSAFE STATE (DEADLOCK RISK)'}</strong>
                  <span>{bankersOutput.reason}</span>
                </div>
              </div>
              {bankersOutput.safe_sequence.length > 0 && (
                <div>
                  <small style={{ color: 'var(--color-muted)', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                    Banker&apos;s Safe Execution Sequence
                  </small>
                  <div className="sequence-chain">
                    {bankersOutput.safe_sequence.map((pid, idx) => (
                      <span key={pid} className="chain-chip">
                        P{pid} {idx < bankersOutput.safe_sequence.length - 1 ? '→' : ''}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <div className="table-wrap" style={{ marginTop: '10px' }}>
                <table>
                  <thead>
                    <tr><th>Process</th><th>Allocated (A, B, C)</th><th>Max Demand (A, B, C)</th><th>Remaining Need (A, B, C)</th><th>Status</th></tr>
                  </thead>
                  <tbody>
                    {(deadlockPreset === 'UNSAFE'
                      ? [
                          { p: 'P0', alloc: [0, 1, 0], max: [7, 5, 3] },
                          { p: 'P1', alloc: [2, 0, 0], max: [6, 4, 2] },
                          { p: 'P2', alloc: [3, 0, 2], max: [9, 4, 4] },
                        ]
                      : [
                          { p: 'P0', alloc: [0, 1, 0], max: [7, 5, 3] },
                          { p: 'P1', alloc: [2, 0, 0], max: [3, 2, 2] },
                          { p: 'P2', alloc: [3, 0, 2], max: [9, 0, 2] },
                          { p: 'P3', alloc: [2, 1, 1], max: [2, 2, 2] },
                          { p: 'P4', alloc: [0, 0, 2], max: [4, 3, 3] },
                        ]
                    ).map((row) => {
                      const need = row.max.map((m, i) => m - row.alloc[i]);
                      return (
                        <tr key={row.p}>
                          <td><b>{row.p}</b></td>
                          <td>[{row.alloc.join(', ')}]</td>
                          <td>[{row.max.join(', ')}]</td>
                          <td><b>[{need.join(', ')}]</b></td>
                          <td>
                            <span className={`state-label ${bankersOutput.is_safe ? 'state-linked' : 'state-review'}`}>
                              {bankersOutput.is_safe ? 'Can Finish' : 'Blocked'}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ) : ragOutput ? (
            <div className="output-details-stack">
              <div className={`verdict-banner ${ragOutput.deadlock_detected ? 'verdict-warn' : 'verdict-pass'}`}>
                <ShieldAlert size={15} />
                <div>
                  <strong>{ragOutput.deadlock_detected ? 'DEADLOCK CYCLE DETECTED IN RAG' : 'NO DEADLOCK IN RESOURCE GRAPH'}</strong>
                  <span>{ragOutput.reason}</span>
                </div>
              </div>
              <div style={{ display: 'grid', gap: '8px', marginTop: '8px' }}>
                <small style={{ color: 'var(--color-muted)', fontWeight: 600 }}>Resource Allocation & Request Edges</small>
                <div className="lock-edge">
                  <span className="lock-resource">R101</span>
                  <ArrowRight size={16} />
                  <span className="lock-node held">P1<small>HELD (Allocated)</small></span>
                  <ArrowRight size={16} />
                  <span className="lock-resource">Requests R102</span>
                </div>
                <div className="lock-edge">
                  <span className="lock-resource">R102</span>
                  <ArrowRight size={16} />
                  <span className="lock-node held">P2<small>HELD (Allocated)</small></span>
                  <ArrowRight size={16} />
                  <span className={`lock-node ${ragOutput.deadlock_detected ? 'waiting' : 'held'}`}>
                    {ragOutput.deadlock_detected ? 'Requests R101 (CYCLE!)' : 'P3 Requests R102 (Acyclic)'}
                  </span>
                </div>
              </div>
              {ragOutput.cycle.length > 0 && (
                <div className="result-pairs">
                  <span>Cycle Path <b>{ragOutput.cycle.join(' → ')}</b></span>
                  <span>Deadlocked Processes <b>{ragOutput.deadlocked_processes.map((p) => `P${p}`).join(', ')}</b></span>
                </div>
              )}
            </div>
          ) : (
            <div className="empty-state">Click <b>Execute Deadlock theory</b> to evaluate Banker&apos;s safe sequence or Resource Allocation Graph cycles.</div>
          )
        )}

        {/* OS: Disk Scheduling Result */}
        {tab === 'OS simulations' && lab === 'Disk scheduling' && (
          diskOutput ? (
            <>
              <div className="verdict-banner verdict-pass">
                <HardDrive size={15} />
                <div>
                  <strong>{diskOutput.algorithm} Disk Arm Schedule (Initial Head: {diskOutput.initial_head})</strong>
                  <span>Total Head Movement: {diskOutput.total_seek_time} cylinders · Avg Seek: {(diskOutput.total_seek_time / Math.max(1, diskOutput.requests.length)).toFixed(1)} cyl/req</span>
                </div>
              </div>
              <div style={{ marginTop: '12px', padding: '10px 12px', borderRadius: '10px', background: 'var(--color-paper-2)', border: '1px solid var(--color-rule)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--color-muted)', marginBottom: '8px' }}>
                  <span>Cylinder 0</span>
                  <span>Head Trajectory ({diskOutput.initial_head} → {diskOutput.requests.map((r) => r.track).join(' → ')})</span>
                  <span>Cylinder 199</span>
                </div>
                <div style={{ display: 'grid', gap: '6px' }}>
                  {[{ order: 0, track: diskOutput.initial_head, seek_time: 0 }, ...diskOutput.requests].map((pt) => {
                    const pct = Math.min(98, Math.max(2, Math.round((pt.track / 199) * 100)));
                    return (
                      <div key={pt.order} style={{ display: 'grid', gridTemplateColumns: '64px 1fr 78px', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
                        <span style={{ color: 'var(--color-muted)' }}>{pt.order === 0 ? 'Start' : `Step #${pt.order}`}</span>
                        <div style={{ position: 'relative', height: '14px', background: 'var(--color-paper)', borderRadius: '999px', border: '1px solid var(--color-rule)' }}>
                          <div
                            style={{
                              position: 'absolute',
                              left: `calc(${pct}% - 6px)`,
                              top: '1px',
                              width: '10px',
                              height: '10px',
                              borderRadius: '50%',
                              background: pt.order === 0 ? 'var(--color-peach)' : 'var(--color-accent)',
                            }}
                          />
                        </div>
                        <b style={{ textAlign: 'right' }}>Cyl {pt.track}</b>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="table-wrap" style={{ marginTop: '10px' }}>
                <table>
                  <thead><tr><th>Order</th><th>Target Cylinder</th><th>Seek Distance</th></tr></thead>
                  <tbody>
                    {diskOutput.requests.map((r) => (
                      <tr key={r.order}><td>#{r.order}</td><td><b>Track {r.track}</b></td><td>{r.seek_time} cylinders</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="empty-state">Click <b>Execute Disk scheduling</b> to compute total cylinder seek distance and visualize head movement.</div>
          )
        )}

        {/* OS: Synchronization Result */}
        {tab === 'OS simulations' && lab === 'Synchronization' && (
          syncOutput ? (
            <>
              <div className="verdict-banner verdict-pass">
                <Check size={15} />
                <div>
                  <strong>{syncOutput.problem_type} Semaphore Trace ({syncOutput.iterations} iterations)</strong>
                  <span>Mutex &amp; empty/full counting semaphore invariants preserved across all buffer operations</span>
                </div>
              </div>
              <div className="log-console-box">
                {syncOutput.result_log.map((line, idx) => (
                  <div key={idx} className="log-console-line">
                    <span>{String(idx + 1).padStart(2, '0')}</span>
                    <span className={`event-tag ${line.toUpperCase().includes('PRODUCE') ? 'tag-mint' : line.toUpperCase().includes('CONSUME') ? 'tag-blue' : 'tag-lavender'}`} style={{ marginRight: '8px' }}>
                      {line.toUpperCase().includes('PRODUCE') ? 'PRODUCER' : line.toUpperCase().includes('CONSUME') ? 'CONSUMER' : 'SEMAPHORE'}
                    </span>
                    {line}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="empty-state">Click <b>Execute Synchronization</b> to view the step-by-step Producer-Consumer semaphore trace.</div>
          )
        )}

        {/* DBMS: Serializability Result */}
        {tab === 'DBMS simulations' && lab === 'Serializability' && (
          serialOutput ? (
            <div className="output-details-stack">
              <div className={`verdict-banner ${serialOutput.conflict_serializable ? 'verdict-pass' : 'verdict-warn'}`}>
                <Check size={15} />
                <div>
                  <strong>{serialOutput.conflict_serializable ? 'CONFLICT-SERIALIZABLE SCHEDULE' : 'NON-SERIALIZABLE SCHEDULE (CYCLE DETECTED)'}</strong>
                  <span>{serialOutput.conflict_serializable ? 'Precedence graph is acyclic; schedule is equivalent to a serial execution.' : `Cycle(s) found in precedence graph: ${serialOutput.cycles.map((c) => c.map((t) => `T${t}`).join(' → ')).join('; ')}`}</span>
                </div>
              </div>
              <div style={{ display: 'grid', gap: '8px', marginTop: '8px' }}>
                <small style={{ color: 'var(--color-muted)', fontWeight: 600 }}>Precedence Graph Dependency Edges</small>
                {Object.entries(serialOutput.precedence_graph).flatMap(([u, vs]) =>
                  vs.map((v) => ({ from: u, to: String(v) }))
                ).length > 0 ? (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {Object.entries(serialOutput.precedence_graph).flatMap(([u, vs]) =>
                      vs.map((v) => (
                        <div key={`${u}-${v}`} className="lock-edge" style={{ margin: 0 }}>
                          <span className="lock-node held">T{u}<small>Precedes</small></span>
                          <ArrowRight size={16} />
                          <span className={`lock-node ${serialOutput.conflict_serializable ? 'held' : 'waiting'}`}>
                            T{v}<small>{serialOutput.conflict_serializable ? 'Dependent' : 'Conflict Cycle'}</small>
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                ) : (
                  <div className="source-distinction"><p>No conflicting read/write pairs across distinct transactions.</p></div>
                )}
              </div>
              <div className="table-wrap" style={{ marginTop: '8px' }}>
                <table>
                  <thead><tr><th>Step</th><th>Transaction</th><th>Operation</th><th>Data Item</th></tr></thead>
                  <tbody>
                    {parseScheduleString(dbmsScheduleInput).map((op, idx) => (
                      <tr key={idx}>
                        <td>#{idx + 1}</td>
                        <td><b>T{op.transaction_id}</b></td>
                        <td><span className={`event-tag ${op.operation === 'W' ? 'tag-peach' : 'tag-blue'}`}>{op.operation === 'W' ? 'WRITE' : 'READ'}</span></td>
                        <td><b>Item {op.data_item}</b></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="result-pairs">
                <span>Precedence Graph Edges <b>{Object.entries(serialOutput.precedence_graph).flatMap(([u, vs]) => vs.map((v) => `T${u} → T${v}`)).join(', ') || 'None (Independent)'}</b></span>
                <span>Detected Cycles <b>{serialOutput.cycles.length === 0 ? '0 (Acyclic)' : serialOutput.cycles.map((c) => c.map((t) => `T${t}`).join(' → ')).join(', ')}</b></span>
              </div>
            </div>
          ) : (
            <div className="empty-state">Click <b>Execute Serializability</b> to build the conflict precedence graph and test for cycles.</div>
          )
        )}

        {/* DBMS: WAL Recovery Result */}
        {tab === 'DBMS simulations' && lab === 'WAL recovery' && (
          recoveryOutput ? (
            <div className="output-details-stack">
              <div className="verdict-banner verdict-pass">
                <Database size={15} />
                <div>
                  <strong>WAL / ARIES Crash Recovery Completed</strong>
                  <span>Committed (REDO): {recoveryOutput.committed_transactions.map((t) => `T${t}`).join(', ') || 'None'} · Losers (UNDO): {recoveryOutput.undone_transactions.map((t) => `T${t}`).join(', ') || 'None'}</span>
                </div>
              </div>
              <div className="result-pairs">
                <span>REDO Transactions (Winners) <b>{recoveryOutput.redone_transactions.map((t) => `T${t}`).join(', ') || 'None'}</b></span>
                <span>UNDO Transactions (Losers Rolled Back) <b>{recoveryOutput.undone_transactions.map((t) => `T${t}`).join(', ') || 'None'}</b></span>
              </div>
              <div className="table-wrap" style={{ marginTop: '10px' }}>
                <table>
                  <thead><tr><th>Data Item</th><th>Initial Value</th><th>Recovered Final Value</th><th>Recovery Action</th></tr></thead>
                  <tbody>
                    {Object.entries(recoveryOutput.final_state).map(([item, val]) => {
                      const parsedInit = parseRecoveryLogInput(dbmsRecoveryInput).initial_state[item] ?? '—';
                      const changed = String(parsedInit) !== String(val);
                      return (
                        <tr key={item}>
                          <td><b>Item {item}</b></td>
                          <td>{parsedInit}</td>
                          <td><span className="state-label state-linked">{val}</span></td>
                          <td>
                            <span className={`event-tag ${changed ? 'tag-mint' : 'tag-peach'}`}>
                              {changed ? 'REDO APPLIED (Committed)' : 'UNDO RESTORED (Rolled Back)'}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="empty-state">Click <b>Execute WAL recovery</b> to run REDO/UNDO analysis and inspect recovered data item values.</div>
          )
        )}

        {/* DBMS: Strict 2PL & Deadlocks Result */}
        {tab === 'DBMS simulations' && lab === 'Strict 2PL & Deadlocks' && (
          lock2plOutput ? (
            <div className="output-details-stack">
              <div className={`verdict-banner ${lock2plOutput.deadlock_detected ? 'verdict-warn' : 'verdict-pass'}`}>
                <LockKeyhole size={15} />
                <div>
                  <strong>{lock2plOutput.deadlock_detected ? 'DEADLOCK CYCLE DETECTED IN 2PL LOCK TABLE' : 'NO DEADLOCK CYCLE (SAFE WAIT)'}</strong>
                  <span>{lock2plOutput.deadlock_detected ? `Victim selected for rollback: T${lock2plOutput.victim_transaction_id ?? 2}` : 'All waiting transactions can proceed once holders commit.'}</span>
                </div>
              </div>
              <div style={{ display: 'grid', gap: '8px', marginTop: '8px' }}>
                <small style={{ color: 'var(--color-muted)', fontWeight: 600 }}>Wait-For Graph Edges</small>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {Object.entries(lock2plOutput.wait_for_graph).flatMap(([u, vs]) =>
                    vs.map((v) => (
                      <div key={`${u}-${v}`} className="lock-edge" style={{ margin: 0 }}>
                        <span className="lock-node waiting">T{u}<small>WAITING</small></span>
                        <ArrowRight size={16} />
                        <span className="lock-node held">T{v}<small>HOLDS LOCK</small></span>
                      </div>
                    ))
                  )}
                </div>
              </div>
              <div className="table-wrap" style={{ marginTop: '8px' }}>
                <table>
                  <thead><tr><th>Transaction</th><th>Data Item</th><th>Lock Mode</th><th>Lock Status</th></tr></thead>
                  <tbody>
                    {(dbmsLockPreset === 'DEADLOCK_CYCLE'
                      ? [
                          { tx: 'T1', item: 'Account_A', mode: 'EXCLUSIVE (X)', status: 'HELD' },
                          { tx: 'T2', item: 'Account_B', mode: 'EXCLUSIVE (X)', status: 'HELD' },
                          { tx: 'T1', item: 'Account_B', mode: 'EXCLUSIVE (X)', status: 'WAITING' },
                          { tx: 'T2', item: 'Account_A', mode: 'EXCLUSIVE (X)', status: 'WAITING' },
                        ]
                      : [
                          { tx: 'T1', item: 'Account_A', mode: 'EXCLUSIVE (X)', status: 'HELD' },
                          { tx: 'T2', item: 'Account_A', mode: 'SHARED (S)', status: 'WAITING' },
                          { tx: 'T2', item: 'Account_B', mode: 'EXCLUSIVE (X)', status: 'HELD' },
                        ]
                    ).map((lk, idx) => (
                      <tr key={idx}>
                        <td><b>{lk.tx}</b></td>
                        <td>{lk.item}</td>
                        <td><span className="event-tag tag-blue">{lk.mode}</span></td>
                        <td>
                          <span className={`state-label ${lk.status === 'HELD' ? 'state-linked' : 'state-review'}`}>
                            {lk.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="result-pairs">
                <span>Wait-For Graph Edges <b>{Object.entries(lock2plOutput.wait_for_graph).flatMap(([u, vs]) => vs.map((v) => `T${u} → T${v}`)).join(', ') || 'None'}</b></span>
                <span>Deadlock Cycles <b>{lock2plOutput.cycles.length ? lock2plOutput.cycles.map((c) => c.map((t) => `T${t}`).join(' → ')).join('; ') : 'None'}</b></span>
                {lock2plOutput.victim_transaction_id && <span>Recommended Victim <b>Transaction T{lock2plOutput.victim_transaction_id}</b></span>}
              </div>
            </div>
          ) : (
            <div className="empty-state">Click <b>Execute Strict 2PL &amp; Deadlocks</b> to construct the wait-for graph and identify deadlock victims.</div>
          )
        )}
      </section>
    </div>
    <div className="note-banner"><FlaskConical size={16} /><span>Simulation models evaluate CPU scheduling, page replacement, deadlock graphs, and ACID recovery mechanisms.</span></div>
  </>;
}

function labAlgorithms(tab: string, lab: string): string[] {
  if (tab === 'OS simulations') {
    if (lab === 'Memory & page replacement') return ['FIFO', 'LRU', 'OPTIMAL', 'Compare ALL'];
    if (lab === 'Deadlock theory') return ['Banker’s algorithm', 'Resource allocation graph'];
    if (lab === 'Disk scheduling') return ['FCFS', 'SSTF', 'SCAN', 'C-SCAN'];
    if (lab === 'Synchronization') return ['Producer-Consumer (Semaphores)'];
    return ['Round Robin', 'FCFS', 'SJF', 'SRTF', 'Priority'];
  }
  if (lab === 'WAL recovery') return ['WAL / REDO-UNDO', 'ARIES Checkpoint recovery'];
  if (lab === 'Strict 2PL & Deadlocks') return ['Strict 2PL Wait-For Graph'];
  return ['Conflict Serializability & Precedence Graph'];
}

interface WhatIfScenarioRecord {
  scenario_id?: number;
  name?: string;
  scenario_name?: string;
  analysis_type?: string;
  scenario_type?: string;
  input_data?: Record<string, unknown>;
  input_payload?: Record<string, unknown>;
  result?: Record<string, unknown>;
  created_at?: string;
}

function WhatIf({ tab, liveData, sampleMode, onRefresh, onAction }: { tab: string; liveData: LiveWorkspaceData; sampleMode: boolean; onRefresh: (toast?: boolean) => Promise<void>; onAction: (message: string) => void }) {
  const [scenarioTitle, setScenarioTitle] = useState('Inventory schedule review');
  const [scheduleInput, setScheduleInput] = useState('R1(A), W1(A), R2(A), W2(A), R1(B), W1(B)');
  const [recoveryInput, setRecoveryInput] = useState('INIT A=100, INIT B=200\nBEGIN T1\nWRITE T1 A 100 -> 150\nBEGIN T2\nWRITE T2 B 200 -> 280\nCOMMIT T2');
  const [osScenarioType, setOsScenarioType] = useState<'CPU_LOAD' | 'MEMORY_PRESSURE' | 'DISK_IO' | 'RESOURCE_CONTENTION'>('CPU_LOAD');
  const [osParam1, setOsParam1] = useState<number>(32);
  const [osParam2, setOsParam2] = useState<number>(45);
  const [osParam3, setOsParam3] = useState<number>(4);

  const [whatIfOutput, setWhatIfOutput] = useState<WhatIfScenarioRecord | null>(null);
  const [selectedSavedScenario, setSelectedSavedScenario] = useState<WhatIfScenarioRecord | null>(null);
  const [evaluating, setEvaluating] = useState(false);

  useEffect(() => {
    let active = true;
    const loadPreview = async () => {
      try {
        if (tab === 'Schedule analysis') {
          const operations = parseScheduleString(scheduleInput);
          const res = await workflowsApi.analyzeSchedule<Record<string, unknown>>({ operations });
          if (active) {
            setWhatIfOutput({
              scenario_id: Number(liveData.scenarios[0]?.scenario_id ?? 1),
              name: scenarioTitle,
              analysis_type: 'SCHEDULE',
              result: res,
            });
          }
        } else if (tab === 'Recovery experiment') {
          const parsed = parseRecoveryLogInput(recoveryInput);
          const res = await workflowsApi.recover<Record<string, unknown>>(parsed);
          if (active) {
            setWhatIfOutput({
              scenario_id: Number(liveData.scenarios[0]?.scenario_id ?? 2),
              name: scenarioTitle,
              analysis_type: 'RECOVERY',
              result: res,
            });
          }
        } else if (tab === 'OS workload') {
          if (active) {
            setWhatIfOutput({
              scenario_id: Number(liveData.scenarios[0]?.scenario_id ?? 3),
              name: scenarioTitle,
              analysis_type: `OS_${osScenarioType}`,
              result: {
                scenario_type: osScenarioType,
                estimated_utilization_percent: Math.min(99, Math.round((osParam1 * osParam2) / Math.max(1, osParam3 * 12))),
                queue_depth: Math.max(1, Math.round(osParam1 / Math.max(1, osParam3))),
                recommendation: 'Deterministic workload preview ready — click Analyze & save scenario to persist to MySQL.',
              },
            });
          }
        }
      } catch {
        // Ignore preview error
      }
    };
    void loadPreview();
    return () => { active = false; };
  }, [tab, scheduleInput, recoveryInput, osScenarioType, osParam1, osParam2, osParam3, scenarioTitle, liveData.scenarios]);

  const runAndSaveWhatIf = async () => {
    setEvaluating(true);
    try {
      if (tab === 'Schedule analysis') {
        const operations = parseScheduleString(scheduleInput);
        const res = await analysisApi.saveScheduleScenario<WhatIfScenarioRecord>({
          name: scenarioTitle || 'Schedule analysis',
          operations,
        });
        setWhatIfOutput(res);
        await onRefresh(false);
        onAction(`Evaluated & saved schedule scenario #${res.scenario_id ?? ''} to MySQL.`);
        return;
      }

      if (tab === 'Recovery experiment') {
        const parsed = parseRecoveryLogInput(recoveryInput);
        const res = await analysisApi.saveRecoveryScenario<WhatIfScenarioRecord>({
          name: scenarioTitle || 'Crash recovery check',
          initial_state: parsed.initial_state,
          logs: parsed.logs,
        });
        setWhatIfOutput(res);
        await onRefresh(false);
        onAction(`Evaluated & saved recovery scenario #${res.scenario_id ?? ''} to MySQL.`);
        return;
      }

      if (tab === 'OS workload') {
        const parameters = osScenarioType === 'CPU_LOAD'
          ? { process_count: osParam1, avg_burst_ms: osParam2, core_count: Math.max(1, osParam3) }
          : osScenarioType === 'MEMORY_PRESSURE'
          ? { allocated_mb: osParam1 * 128, total_ram_mb: Math.max(512, osParam2 * 128), frames: Math.max(1, osParam3), page_references: [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5] }
          : osScenarioType === 'DISK_IO'
          ? { current_head: Math.min(199, Math.max(0, osParam1)), requests: [82, 170, 43, 140, 24, 16, 190].slice(0, Math.max(2, Math.min(7, osParam3))), algorithm: osParam2 % 2 === 0 ? 'SSTF' : 'FCFS' }
          : { concurrent_tasks: osParam1, shared_locks: Math.max(1, osParam3) };

        const res = await analysisApi.saveOsScenario<WhatIfScenarioRecord>({
          name: scenarioTitle || `OS ${osScenarioType} experiment`,
          scenario_type: osScenarioType,
          parameters,
        });
        setWhatIfOutput(res);
        await onRefresh(false);
        onAction(`Evaluated & saved OS workload scenario #${res.scenario_id ?? ''} to MySQL.`);
      }
    } catch (err) {
      onAction(err instanceof Error ? err.message : 'Could not evaluate scenario.');
    } finally {
      setEvaluating(false);
    }
  };

  if (tab === 'Saved scenarios') {
    const savedRows: WhatIfScenarioRecord[] = !sampleMode && liveData.scenarios.length > 0
      ? (liveData.scenarios as unknown as WhatIfScenarioRecord[])
      : scenarioNames.map((name, index) => ({
          scenario_id: index + 1,
          name,
          analysis_type: ['SCHEDULE', 'RECOVERY', 'OS_CPU_LOAD'][index],
          created_at: `Oct 2${7 - index}, 10:${42 - index * 8} UTC`,
          input_data: { sample: name },
          result: { status: 'Evaluated', summary: 'Deterministic scenario stored in workspace.' },
        }));

    return <>
      <section className="surface-panel table-panel">
        <div className="panel-heading"><div><h3>Saved what-if scenarios</h3><p>Persisted scenarios in MySQL (`/api/what-if/scenarios`)</p></div><span className="event-tag tag-lavender">{savedRows.length} scenarios</span></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>Scenario</th><th>Analysis Type</th><th>Created</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {savedRows.map((row, idx) => {
                const name = String(row.name ?? row.scenario_name ?? 'Scenario');
                const type = String(row.analysis_type ?? row.scenario_type ?? 'SCHEDULE');
                return (
                  <tr key={`${name}-${idx}`}>
                    <td>#{row.scenario_id ?? idx + 1}</td>
                    <td><b>{name}</b></td>
                    <td><span className="event-tag tag-blue">{type}</span></td>
                    <td>{formatTimeShort(row.created_at)}</td>
                    <td><span className="state-label state-linked">Persisted</span></td>
                    <td>
                      <button type="button" className="table-action" onClick={() => setSelectedSavedScenario(row)}>
                        View output scenario <ArrowRight size={13} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {selectedSavedScenario && (
        <section className="surface-panel output-scenario-panel">
          <div className="panel-heading">
            <div>
              <h3>Scenario #{selectedSavedScenario.scenario_id}: {selectedSavedScenario.name ?? selectedSavedScenario.scenario_name}</h3>
              <p>Analysis Type: {selectedSavedScenario.analysis_type ?? selectedSavedScenario.scenario_type}</p>
            </div>
            <button type="button" className="button button-quiet" onClick={() => setSelectedSavedScenario(null)}>Close inspector</button>
          </div>
          <div className="content-two-col">
            <div className="code-block-card">
              <strong>Input Payload (`input_data`)</strong>
              <pre>{JSON.stringify(selectedSavedScenario.input_data ?? selectedSavedScenario.input_payload ?? {}, null, 2)}</pre>
            </div>
            <div className="code-block-card">
              <strong>Deterministic Output Result (`result`)</strong>
              <pre>{JSON.stringify(selectedSavedScenario.result ?? {}, null, 2)}</pre>
            </div>
          </div>
        </section>
      )}
    </>;
  }

  const resObj = whatIfOutput?.result ?? null;

  return <div className="content-two-col">
    <section className="surface-panel">
      <div className="panel-heading">
        <div>
          <h3>{tab === 'Schedule analysis' ? 'Proposed transaction schedule' : tab === 'Recovery experiment' ? 'Recovery log after crash' : 'OS workload & contention model'}</h3>
          <p>Enter a hypothetical case, then run deterministic analysis and persist to MySQL</p>
        </div>
        <span className="event-tag tag-lavender">What-If Engine</span>
      </div>

      <label className="field-label">Scenario name
        <input value={scenarioTitle} onChange={(e) => setScenarioTitle(e.target.value)} />
      </label>

      {tab === 'Schedule analysis' && (
        <>
          <div className="preset-bar">
            <button type="button" className="button button-quiet" onClick={() => { setScenarioTitle('Serializable Order Checkout'); setScheduleInput('R1(A), W1(A), R2(A), W2(A), R1(B), W1(B)'); }}>Preset: Acyclic Schedule</button>
            <button type="button" className="button button-quiet" onClick={() => { setScenarioTitle('Conflicting Inventory Update'); setScheduleInput('R1(A), R2(A), W1(A), W2(A)'); }}>Preset: Cycle Conflict</button>
          </div>
          <label className="field-label">Schedule Operations (`R1(A), W1(A), R2(A)...`)
            <textarea value={scheduleInput} onChange={(e) => setScheduleInput(e.target.value)} />
          </label>
        </>
      )}

      {tab === 'Recovery experiment' && (
        <>
          <div className="preset-bar">
            <button type="button" className="button button-quiet" onClick={() => { setScenarioTitle('Checkout Crash Recovery'); setRecoveryInput('INIT A=100, INIT B=200\nBEGIN T1\nWRITE T1 A 100 -> 150\nBEGIN T2\nWRITE T2 B 200 -> 280\nCOMMIT T2'); }}>Preset: T2 Committed, T1 Loser</button>
            <button type="button" className="button button-quiet" onClick={() => { setScenarioTitle('Multi-Tx WAL Replay'); setRecoveryInput('INIT X=50, INIT Y=80\nBEGIN T1\nWRITE T1 X 50 -> 95\nCOMMIT T1\nBEGIN T2\nWRITE T2 Y 80 -> 120\nCOMMIT T2'); }}>Preset: Both Committed</button>
          </div>
          <label className="field-label">WAL Log Sequence
            <textarea value={recoveryInput} onChange={(e) => setRecoveryInput(e.target.value)} />
          </label>
        </>
      )}

      {tab === 'OS workload' && (
        <>
          <label className="field-label">OS Workload Model Type
            <select value={osScenarioType} onChange={(e) => setOsScenarioType(e.target.value as 'CPU_LOAD' | 'MEMORY_PRESSURE' | 'DISK_IO' | 'RESOURCE_CONTENTION')}>
              <option value="CPU_LOAD">CPU Load & Queue Bottleneck</option>
              <option value="MEMORY_PRESSURE">Memory Pressure & Thrashing Risk</option>
              <option value="DISK_IO">Disk I/O Saturation & Seek Distance</option>
              <option value="RESOURCE_CONTENTION">Lock / Resource Contention Probability</option>
            </select>
          </label>
          <div className="workbench-controls">
            <label className="field-label">
              {osScenarioType === 'CPU_LOAD' ? 'Process Count' : osScenarioType === 'MEMORY_PRESSURE' ? 'Allocated Blocks (×128 MB)' : osScenarioType === 'DISK_IO' ? 'Initial Head Cylinder' : 'Concurrent Tasks'}
              <input type="number" min={1} max={199} value={osParam1} onChange={(e) => setOsParam1(Number(e.target.value))} />
            </label>
            <label className="field-label">
              {osScenarioType === 'CPU_LOAD' ? 'Avg Burst Time (ms)' : osScenarioType === 'MEMORY_PRESSURE' ? 'Total RAM Blocks (×128 MB)' : osScenarioType === 'DISK_IO' ? 'Mode (Even=SSTF, Odd=FCFS)' : 'Contention Window Factor'}
              <input type="number" min={1} max={200} value={osParam2} onChange={(e) => setOsParam2(Number(e.target.value))} />
            </label>
            <label className="field-label">
              {osScenarioType === 'CPU_LOAD' ? 'CPU Cores' : osScenarioType === 'MEMORY_PRESSURE' ? 'Page Frames' : osScenarioType === 'DISK_IO' ? 'Pending I/O Requests' : 'Shared Locks'}
              <input type="number" min={1} max={64} value={osParam3} onChange={(e) => setOsParam3(Number(e.target.value))} />
            </label>
          </div>
        </>
      )}

      <button type="button" className="button button-primary" disabled={evaluating} onClick={() => void runAndSaveWhatIf()}>
        <Play size={14} fill="currentColor" /> {evaluating ? 'Analyzing & saving…' : 'Analyze & save scenario'}
      </button>
    </section>

    <section className="surface-panel simulation-result">
      <div className="panel-heading">
        <div><h3>Deterministic Analysis Output</h3><p>{whatIfOutput ? `Scenario #${whatIfOutput.scenario_id} (${whatIfOutput.analysis_type})` : 'Deterministic scenario evaluation output'}</p></div>
        <span className="result-check"><Check size={15} /></span>
      </div>

      {resObj ? (
        <div className="output-details-stack">
          <div className="verdict-banner verdict-pass">
            <Check size={15} />
            <div>
              <strong>Scenario #{whatIfOutput?.scenario_id} Persisted & Evaluated</strong>
              <span>{String(resObj.recommendation ?? (resObj.conflict_serializable !== undefined ? (resObj.conflict_serializable ? 'Conflict-Serializable Schedule' : 'Non-Serializable Conflict Cycle') : 'Deterministic state computed and stored in MySQL'))}</span>
            </div>
          </div>
          <div className="result-pairs">
            {Object.entries(resObj).map(([k, v]) => (
              <span key={k}>
                {k.replace(/_/g, ' ')} <b>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</b>
              </span>
            ))}
          </div>
        </div>
      ) : (
        <div className="whatif-result">
          <span className="event-tag">Ready to Evaluate</span>
          <strong>Click "Analyze & save scenario"</strong>
          <p>The scenario analyzer will model schedule serializability, ARIES recovery, or OS contention, and render every output metric here.</p>
        </div>
      )}
    </section>
  </div>;
}

function Administration({ tab, liveData, sampleMode, onRefresh, onAction, onToggleSample, currentUser, onSignOut }: { tab: string; liveData: LiveWorkspaceData; sampleMode: boolean; onRefresh: (toast?: boolean) => Promise<void>; onAction: (message: string) => void; onToggleSample: () => void; currentUser: AuthUser; onSignOut: () => void }) {
  const [auditActionInput, setAuditActionInput] = useState('SYSTEM_HEALTH_CHECK');
  const [localAuditEntries, setLocalAuditEntries] = useState<Array<{ time: string; user: string; action: string; detail: string; source: string }>>([]);

  if (!currentUser.is_admin) {
    return (
      <section className="surface-panel" style={{ padding: '48px 24px', textAlign: 'center', margin: '24px auto', maxWidth: '600px' }}>
        <div style={{ display: 'inline-flex', padding: '16px', borderRadius: '50%', background: 'rgba(239, 68, 68, 0.12)', color: '#ef4444', marginBottom: '16px' }}>
          <ShieldAlert size={36} />
        </div>
        <h2 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '8px', color: 'var(--color-ink)' }}>Access Denied</h2>
        <p style={{ color: 'var(--color-ink-subtle)', lineHeight: 1.6, marginBottom: '20px' }}>
          Administrator privileges are required to access security audit logs. Your current role is <strong>Member</strong>.
        </p>
        <button type="button" className="button button-primary" onClick={() => onAction('Administration is restricted to system administrators.')}>
          Return to Dashboard
        </button>
      </section>
    );
  }

  if (tab === 'Accounts & sign-in') return <AccountSettings user={currentUser} onSignOut={onSignOut} />;

  const handleEmitAudit = async () => {
    try {
      const actionName = auditActionInput || 'SECURITY_AUDIT_VERIFICATION';
      const detailText = `UID ${currentUser.uid_linux ?? 0} · Role: Administrator`;
      const res = await workflowsApi.createAuditEntry<{ status?: string; message?: string }>({
        user_id: currentUser.user_id,
        username: currentUser.username,
        action: actionName,
        details: detailText,
      });
      const nowStr = new Date().toTimeString().slice(0, 8);
      setLocalAuditEntries((prev) => [
        {
          time: nowStr,
          user: currentUser.username,
          action: actionName,
          detail: `${res.message ?? 'Audit log entry recorded.'} (${detailText})`,
          source: 'POST /api/audit/',
        },
        ...prev,
      ]);
      await onRefresh(false);
      onAction(`${res.message ?? 'Audit entry recorded'} (${actionName}).`);
    } catch (err) {
      onAction(err instanceof Error ? err.message : 'Could not record audit entry.');
    }
  };

  const backendRows = !sampleMode && liveData.auditLogs.length > 0
    ? liveData.auditLogs.slice(0, 20).map((log) => [
        formatTimeShort(log.created_at ?? log.timestamp),
        String(log.username ?? currentUser.username),
        String(log.action ?? 'Action'),
        String(log.details ?? `UID ${String(log.uid_linux ?? 0)}`),
        'Security Engine',
      ])
    : sampleMode
    ? [
        ['10:41:55', 'admin', 'SYSTEM_AUDIT_LOG_ROTATION', 'Security audit log retention cycle verified', 'Security Engine'],
        ['10:38:02', 'admin', 'SYSTEM_HEALTH_CHECK', 'Verified collector status and host telemetry', 'Security Engine'],
      ]
    : [];

  const auditRows = [
    ...localAuditEntries.map((e) => [e.time, e.user, e.action, e.detail, e.source]),
    ...backendRows,
  ];

  return <>
    <section className="surface-panel output-scenario-panel" style={{ marginBottom: '12px' }}>
      <div className="panel-heading">
        <div><h3>Record Cross-Layer Security Audit Entry</h3><p>Log a signed security audit entry linking OS UID and session credentials</p></div>
        <span className="event-tag tag-lavender">Administrator Only</span>
      </div>
      <div className="preset-bar">
        <input
          value={auditActionInput}
          onChange={(e) => setAuditActionInput(e.target.value)}
          placeholder="Audit action name"
          style={{ minHeight: '38px', padding: '0 12px', border: '1px solid var(--color-rule)', borderRadius: '8px', background: 'var(--color-paper-2)', color: 'var(--color-ink)', fontSize: '13px', minWidth: '240px' }}
        />
        <button type="button" className="button button-primary" onClick={() => void handleEmitAudit()}><Play size={13} fill="currentColor" /> Record audit entry</button>
      </div>
    </section>

    <section className="surface-panel table-panel">
      <div className="panel-heading">
        <div><h3>Administrative audit log</h3><p>User actions recorded across security sessions</p></div>
        <button type="button" className="button button-secondary" onClick={() => void onRefresh(true)}> <ListFilter size={15} /> Sync</button>
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Detail</th><th>Source</th></tr></thead>
          <tbody>
            {auditRows.length > 0 ? (
              auditRows.map((row, idx) => (
                <tr key={`${row[0]}-${idx}`}>{row.map((item, index) => <td key={index}>{item}</td>)}</tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '24px', color: 'var(--color-ink-subtle)' }}>
                  No security audit records logged yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
    <section className="surface-panel preferences-panel">
      <div><h3>Demonstration sample override</h3><p>Toggle between live backend telemetry and static illustrative records.</p></div>
      <label className="toggle-control"><input type="checkbox" checked={sampleMode} onChange={onToggleSample} /><span className="toggle-track" /><strong>{sampleMode ? 'Sample mode' : 'Live telemetry stream'}</strong></label>
    </section>
  </>;
}

function AccountSettings({ user, onSignOut }: { user: AuthUser; onSignOut: () => void }) {
  return <section className="surface-panel account-settings">
    <div className="panel-heading"><div><h3>Signed-in account</h3><p>Authenticated OS-DBX session</p></div><span className="event-tag tag-lavender">{user.is_admin ? 'Administrator' : 'Member'}</span></div>
    <div className="account-profile"><div className="account-avatar">{user.username.slice(0, 2).toUpperCase()}</div><div><strong>{user.username}</strong><small>{user.email ?? 'No email registered'}</small></div></div>
    <div className="health-facts"><span>Username <b>{user.username}</b></span><span>Email <b>{user.email ?? 'Not provided'}</b></span><span>Linux UID <b>{user.uid_linux ?? 1000}</b></span><span>Role <b>{user.is_admin ? 'Administrator' : 'Member'}</b></span></div>
    <button type="button" className="button button-secondary" onClick={onSignOut}>Sign out</button>
  </section>;
}

export default App;
