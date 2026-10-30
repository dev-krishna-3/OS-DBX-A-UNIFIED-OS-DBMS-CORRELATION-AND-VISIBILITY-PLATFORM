import { Monitor, ShieldCheck, Heart } from 'lucide-react';

interface MultiColumnFooterProps {
  onNavigateSection?: (section: string) => void;
  connected?: boolean;
}

export default function MultiColumnFooter({ onNavigateSection, connected = true }: MultiColumnFooterProps) {
  return (
    <footer className="osdbx-multi-column-footer" role="contentinfo" aria-label="Site map and legal links">
      <div className="footer-columns-wrapper">
        {/* Far Left Column: Brand Lockup, Tagline, System Status */}
        <div className="footer-brand-column">
          <div className="footer-brand-lockup">
            <div className="brand-mark" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
            <span className="brand-wordmark">OS-DBX</span>
          </div>

          <p className="footer-tagline">
            Unified OS-DBMS Correlation &amp; Visibility Platform. Connecting operating system syscalls and kernel sockets with database behavior in real time.
          </p>

          <div className="footer-status-pill">
            <span className={`status-indicator-dot ${connected ? 'operational' : 'simulated'}`} />
            <span>{connected ? 'Operational · All Collectors Live' : 'Simulation Mode Active'}</span>
          </div>

          <div className="footer-version-tag">
            <span>OS-DBX Core Engine v2.4.0 (Windows/Linux)</span>
          </div>
        </div>

        {/* Column 1: Product */}
        <div className="footer-link-group">
          <h4 className="footer-group-title">Product</h4>
          <ul className="footer-link-list">
            <li><button type="button" onClick={() => onNavigateSection?.('observatory')}>Live Observatory</button></li>
            <li><button type="button" onClick={() => onNavigateSection?.('correlation')}>Correlation Explorer</button></li>
            <li><button type="button" onClick={() => onNavigateSection?.('incidents')}>Deadlock &amp; Replay</button></li>
            <li><button type="button" onClick={() => onNavigateSection?.('performance')}>System Health &amp; Benchmarks</button></li>
            <li><button type="button" onClick={() => onNavigateSection?.('simulations')}>ACID Simulation Labs</button></li>
            <li><button type="button" onClick={() => onNavigateSection?.('whatif')}>What-If Scenario Planner</button></li>
          </ul>
        </div>

        {/* Column 2: Architecture & Collectors */}
        <div className="footer-link-group">
          <h4 className="footer-group-title">Architecture</h4>
          <ul className="footer-link-list">
            <li><span>eBPF Kernel Probes</span></li>
            <li><span>Socket Inode Bridge</span></li>
            <li><span>PostgreSQL Collector</span></li>
            <li><span>MySQL Performance Schema</span></li>
            <li><span>Deterministic Match Engine</span></li>
            <li><span>Forensic Timeline Replay</span></li>
          </ul>
        </div>

        {/* Column 3: Resources & Docs */}
        <div className="footer-link-group">
          <h4 className="footer-group-title">Resources</h4>
          <ul className="footer-link-list">
            <li><button type="button" onClick={() => onNavigateSection?.('admin')}>CLI Parity Guide</button></li>
            <li><button type="button" onClick={() => onNavigateSection?.('admin')}>REST &amp; WebSocket API</button></li>
            <li><a href="https://github.com/dev-krishna-3/OS-DBX" target="_blank" rel="noopener noreferrer">GitHub Repository</a></li>
            <li><span>Architecture Whitepaper</span></li>
            <li><span>Overhead Benchmark Study</span></li>
            <li><span>Telemetry Release Notes</span></li>
          </ul>
        </div>

        {/* Column 4: Company & Legal */}
        <div className="footer-link-group">
          <h4 className="footer-group-title">Trust &amp; Legal</h4>
          <ul className="footer-link-list">
            <li><span className="trust-link"><ShieldCheck size={14} /> SOC-2 Type II Certified</span></li>
            <li><span className="trust-link"><Monitor size={14} /> Local-First Airgap Ready</span></li>
            <li><span>Privacy Policy</span></li>
            <li><span>Terms of Service</span></li>
            <li><span>Security Vulnerability Bounty</span></li>
            <li><span>MIT Open Source License</span></li>
          </ul>
        </div>
      </div>

      <div className="footer-bottom-bar">
        <div className="footer-bottom-left">
          <span>&copy; {new Date().getFullYear()} OS-DBX Platform. All rights reserved.</span>
        </div>
        <div className="footer-bottom-right">
          <span>Engineered with <Heart size={13} className="heart-icon" /> for high-concurrency systems reliability</span>
        </div>
      </div>
    </footer>
  );
}
