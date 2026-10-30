import { Cpu, Database, GitBranch, ShieldAlert, Zap, Layers, RefreshCw, BarChart2 } from 'lucide-react';

interface FeaturesBentoProps {
  onNavigateSection: (section: string) => void;
}

export default function FeaturesBento({ onNavigateSection }: FeaturesBentoProps) {
  return (
    <section className="osdbx-features-section" aria-label="OS-DBX core features and architectural capabilities">
      <div className="section-header-centered">
        <span className="section-pill">Architectural Highlights</span>
        <h2 className="section-title">Deep Cross-Layer Observability</h2>
        <p className="section-lead">
          Eliminate finger-pointing between systems teams and database administrators by connecting kernel socket activity directly with database engine locks and execution plans.
        </p>
      </div>

      {/* Alternating Zigzag Rows */}
      <div className="features-zigzag-container">
        {/* Row 1: Text Left, Visual Right */}
        <div className="zigzag-row">
          <div className="zigzag-text-col">
            <div className="zigzag-icon-box">
              <Cpu size={24} />
            </div>
            <span className="zigzag-label">Operating System Layer</span>
            <h3 className="zigzag-title">Kernel Socket &amp; Process Instrumentation</h3>
            <p className="zigzag-desc">
              Low-overhead OS collectors continuously trace process thread lifecycles, memory page allocation, disk I/O throughput, and TCP socket file descriptors with microsecond timestamps.
            </p>
            <ul className="zigzag-checklist">
              <li>Socket inode tracking to isolate client network connections</li>
              <li>Per-process memory footprint &amp; CPU scheduler latency</li>
              <li>Kernel filesystem I/O wait monitoring with zero overhead (&lt;1.2%)</li>
            </ul>
            <button
              type="button"
              className="button button-secondary zigzag-cta"
              onClick={() => onNavigateSection('observatory')}
            >
              Explore OS Event Stream &rarr;
            </button>
          </div>
          <div className="zigzag-visual-col">
            <div className="zigzag-preview-window">
              <div className="window-dots"><span /><span /><span /></div>
              <div className="window-terminal">
                <div className="term-line"><span className="term-badge os">OS KERNEL</span> PID: 4211 [checkout-api] · syscall: epoll_wait()</div>
                <div className="term-line"><span className="term-badge net">TCP SOCKET</span> 127.0.0.1:54320 &rarr; 127.0.0.1:5432 [ESTABLISHED]</div>
                <div className="term-line"><span className="term-badge disk">VFS I/O</span> write /var/lib/postgresql/15/data 4096B (0.04ms)</div>
                <div className="term-metric-strip">
                  <div>CPU: <strong>14.2%</strong></div>
                  <div>RSS: <strong>182 MB</strong></div>
                  <div>FD Count: <strong>64</strong></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Row 2: Visual Left, Text Right (SWAPPED) */}
        <div className="zigzag-row row-reverse">
          <div className="zigzag-text-col">
            <div className="zigzag-icon-box">
              <Database size={24} />
            </div>
            <span className="zigzag-label">Database Engine Layer</span>
            <h3 className="zigzag-title">DBMS Query Observations &amp; Lock Graph</h3>
            <p className="zigzag-desc">
              Ingest queries and locks from PostgreSQL Performance Schema and wait event monitors. Inspect active transactions, buffer pool hits, and lock conflicts before queries time out.
            </p>
            <ul className="zigzag-checklist">
              <li>Real-time query execution duration &amp; plan analysis</li>
              <li>RowExclusiveLock and ExclusiveLock conflict graphs</li>
              <li>Backend PID association with Postgres client connections</li>
            </ul>
            <button
              type="button"
              className="button button-secondary zigzag-cta"
              onClick={() => onNavigateSection('observatory')}
            >
              View DBMS Query Observations &rarr;
            </button>
          </div>
          <div className="zigzag-visual-col">
            <div className="zigzag-preview-window">
              <div className="window-dots"><span /><span /><span /></div>
              <div className="window-terminal">
                <div className="term-line"><span className="term-badge db">PG BACKEND</span> PID 8842 · Query ID 994201 · Tx 948120</div>
                <div className="term-line"><span className="term-badge query">SQL</span> UPDATE accounts SET balance = balance - 100 WHERE id = 1</div>
                <div className="term-line"><span className="term-badge lock">LOCK STATE</span> Acquired RowExclusiveLock on tbl_accounts</div>
                <div className="term-metric-strip">
                  <div>Latency: <strong>2.1 ms</strong></div>
                  <div>Cache Hit: <strong>99.8%</strong></div>
                  <div>Status: <strong>idle in tx</strong></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Row 3: Text Left, Visual Right */}
        <div className="zigzag-row">
          <div className="zigzag-text-col">
            <div className="zigzag-icon-box">
              <GitBranch size={24} />
            </div>
            <span className="zigzag-label">Deterministic Correlation</span>
            <h3 className="zigzag-title">Cross-Layer Identity Bridge</h3>
            <p className="zigzag-desc">
              Unify operating system processes and database backends with verified causality. Our correlation engine pairs socket inodes, client ports, and query timestamps to deliver definitive trace evidence.
            </p>
            <ul className="zigzag-checklist">
              <li>100% deterministic socket-to-process matching</li>
              <li>Temporal window correlation for non-socket workflows</li>
              <li>Complete causal timeline view from client click to disk fsync</li>
            </ul>
            <button
              type="button"
              className="button button-secondary zigzag-cta"
              onClick={() => onNavigateSection('correlation')}
            >
              Open Correlation Explorer &rarr;
            </button>
          </div>
          <div className="zigzag-visual-col">
            <div className="zigzag-preview-window">
              <div className="window-dots"><span /><span /><span /></div>
              <div className="window-terminal">
                <div className="term-line highlight"><span className="term-badge bridge">IDENTITY BRIDGE</span> Match confidence: 100% Deterministic</div>
                <div className="term-line">&bull; OS Process: checkout-api (PID 4211, Port 54320)</div>
                <div className="term-line">&bull; DBMS Backend: postgres (PID 8842, Port 5432)</div>
                <div className="term-line">&bull; Inode: 89201 | Established at: 10:14:02.194201</div>
                <div className="term-metric-strip">
                  <div>Correlation: <strong>Microsecond</strong></div>
                  <div>Evidence: <strong>Socket Inode</strong></div>
                  <div>Trace ID: <strong>#4211-8842</strong></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Row 4: Visual Left, Text Right (SWAPPED) */}
        <div className="zigzag-row row-reverse">
          <div className="zigzag-text-col">
            <div className="zigzag-icon-box">
              <ShieldAlert size={24} />
            </div>
            <span className="zigzag-label">Forensic Incidents &amp; Replay</span>
            <h3 className="zigzag-title">Deadlock Cycle Detection &amp; Blast Radius</h3>
            <p className="zigzag-desc">
              When lock contention escalates into a deadlock cycle, OS-DBX pinpoints both competing transactions, reveals the exact sequence of resource acquisitions, and models the blast radius.
            </p>
            <ul className="zigzag-checklist">
              <li>Step-by-step forensic timeline replay</li>
              <li>Dependency graph with automated victim transaction recommendation</li>
              <li>Root-cause blast radius calculation across dependent services</li>
            </ul>
            <button
              type="button"
              className="button button-secondary zigzag-cta"
              onClick={() => onNavigateSection('incidents')}
            >
              Analyze Deadlock Incidents &rarr;
            </button>
          </div>
          <div className="zigzag-visual-col">
            <div className="zigzag-preview-window">
              <div className="window-dots"><span /><span /><span /></div>
              <div className="window-terminal">
                <div className="term-line danger"><span className="term-badge dead">DEADLOCK CYCLE</span> Directed Cycle: T1 &rarr; T2 &rarr; T1</div>
                <div className="term-line">&bull; T1 (checkout-api) holds Lock(inventory) waiting for Lock(orders)</div>
                <div className="term-line">&bull; T2 (order-sync) holds Lock(orders) waiting for Lock(inventory)</div>
                <div className="term-line">&bull; Recommended Action: Abort T2 (lowest transaction cost)</div>
                <div className="term-metric-strip">
                  <div>Wait Time: <strong>4.82 s</strong></div>
                  <div>Blast Radius: <strong>2 services</strong></div>
                  <div>Status: <strong>Remediated</strong></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bento Grid Highlights */}
      <div className="bento-grid-title-row">
        <h3>Platform Capabilities at a Glance</h3>
        <p>Built for production engineering teams, DBAs, and SREs</p>
      </div>

      <div className="bento-grid-container">
        <div className="bento-card card-large">
          <div className="bento-icon"><Zap size={22} /></div>
          <h4>Zero-Overhead Kernel Telemetry</h4>
          <p>
            eBPF and native Windows Event Tracing probes hook directly into socket events and process memory without sampling bias or CPU slowdowns.
          </p>
          <div className="bento-metric-large">&lt; 1.2% <span>CPU Impact</span></div>
        </div>

        <div className="bento-card">
          <div className="bento-icon"><Layers size={22} /></div>
          <h4>Multi-Engine Support</h4>
          <p>Native connectors for PostgreSQL 14+, MySQL 8+, SQLite, and Linux/Windows operating system kernels.</p>
        </div>

        <div className="bento-card">
          <div className="bento-icon"><RefreshCw size={22} /></div>
          <h4>Forensic Timeline Replay</h4>
          <p>Scrub back and forth through transaction timelines to see exactly how lock queues accumulated before a crash.</p>
        </div>

        <div className="bento-card">
          <div className="bento-icon"><BarChart2 size={22} /></div>
          <h4>ACID Simulation Sandbox</h4>
          <p>Validate scheduling safety algorithms (Banker&apos;s, 2PL, Strict 2PL, WAL) before deploying high-concurrency migrations.</p>
        </div>
      </div>
    </section>
  );
}
