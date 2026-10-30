import { useState } from 'react';
import { Play, ArrowRight, Monitor, Database, Network, ShieldCheck, Zap } from 'lucide-react';

interface HeroSectionProps {
  onLaunchObservatory: () => void;
  onExploreCorrelation: () => void;
  onOpenQuickStart: () => void;
  connected?: boolean;
}

export default function HeroSection({
  onLaunchObservatory,
  onExploreCorrelation,
  onOpenQuickStart,
  connected = true,
}: HeroSectionProps) {
  const [activeTab, setActiveTab] = useState<'trace' | 'correlation' | 'deadlock'>('trace');

  return (
    <section className="osdbx-hero-wrapper" aria-label="OS-DBX platform introduction">
      {/* Animated gradient mesh background */}
      <div className="hero-gradient-mesh" aria-hidden="true">
        <div className="mesh-orb orb-1" />
        <div className="mesh-orb orb-2" />
        <div className="mesh-orb orb-3" />
        <div className="mesh-grid-overlay" />
      </div>

      <div className="hero-split-container">
        {/* Left Column: Heading, Subheading, CTAs, Highlights */}
        <div className="hero-content-column">
          <div className="hero-eyebrow">
            <span className="live-pill">
              <span className="live-dot" />
              {connected ? 'Real-Time Causal Engine' : 'Offline Simulation Mode'}
            </span>
            <span className="eyebrow-text">v2.4 Kernel-to-SQL Visibility</span>
          </div>

          <h1 className="hero-headline">
            Unified OS-DBMS <span className="gradient-highlight">Correlation & Visibility</span>
          </h1>

          <p className="hero-subheading">
            Connect operating system kernel sockets, thread schedulers, and I/O syscalls with database transaction locks and query execution plans in real time with zero-overhead causal tracing.
          </p>

          <div className="hero-cta-group">
            <button
              type="button"
              className="button button-primary hero-btn-main"
              onClick={onLaunchObservatory}
            >
              <Play size={16} fill="currentColor" /> Launch Live Observatory
            </button>
            <button
              type="button"
              className="button button-secondary hero-btn-sub"
              onClick={onExploreCorrelation}
            >
              Explore Correlation <ArrowRight size={15} />
            </button>
            <button
              type="button"
              className="button button-quiet"
              onClick={onOpenQuickStart}
            >
              Quick-Start Wizard
            </button>
          </div>

          <div className="hero-proof-badges">
            <div className="proof-badge">
              <ShieldCheck size={16} className="proof-icon" />
              <span>&lt;1.2% CPU Overhead</span>
            </div>
            <div className="proof-badge">
              <Zap size={16} className="proof-icon" />
              <span>Microsecond Accuracy</span>
            </div>
            <div className="proof-badge">
              <Network size={16} className="proof-icon" />
              <span>Deterministic Causal Link</span>
            </div>
          </div>
        </div>

        {/* Right Column: Interactive Product Mockup Visual */}
        <div className="hero-mockup-column" role="region" aria-label="Interactive product preview">
          <div className="product-mockup-card">
            <div className="mockup-header">
              <div className="mockup-window-controls">
                <span className="win-dot dot-red" />
                <span className="win-dot dot-yellow" />
                <span className="win-dot dot-green" />
              </div>
              <div className="mockup-tabs">
                <button
                  type="button"
                  className={`mockup-tab ${activeTab === 'trace' ? 'active' : ''}`}
                  onClick={() => setActiveTab('trace')}
                >
                  Cross-Layer Trace
                </button>
                <button
                  type="button"
                  className={`mockup-tab ${activeTab === 'correlation' ? 'active' : ''}`}
                  onClick={() => setActiveTab('correlation')}
                >
                  Socket ⟷ PID Match
                </button>
                <button
                  type="button"
                  className={`mockup-tab ${activeTab === 'deadlock' ? 'active' : ''}`}
                  onClick={() => setActiveTab('deadlock')}
                >
                  Deadlock Replay
                </button>
              </div>
              <span className="mockup-badge">LIVE 60 FPS</span>
            </div>

            <div className="mockup-body">
              {activeTab === 'trace' && (
                <div className="trace-animation-view">
                  <div className="trace-flow-lane lane-os">
                    <div className="lane-header">
                      <Monitor size={15} />
                      <span>OS Kernel Layer (Linux/Win)</span>
                    </div>
                    <div className="trace-capsule">
                      <span className="capsule-id">PID 4211</span>
                      <span className="capsule-title">checkout-api</span>
                      <span className="capsule-sub">socket fd=18 · write(4096)</span>
                    </div>
                  </div>

                  <div className="trace-flow-connector">
                    <div className="connector-pulse-line" />
                    <div className="connector-bridge-badge">
                      <Network size={13} />
                      <span>Identity Bridge : Inode 89201</span>
                    </div>
                    <div className="connector-pulse-line" />
                  </div>

                  <div className="trace-flow-lane lane-dbms">
                    <div className="lane-header">
                      <Database size={15} />
                      <span>PostgreSQL Engine</span>
                    </div>
                    <div className="trace-capsule">
                      <span className="capsule-id">BACKEND 8842</span>
                      <span className="capsule-title">UPDATE inventory SET stock = stock - 1</span>
                      <span className="capsule-sub">RowExclusiveLock · tx: 948120</span>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'correlation' && (
                <div className="correlation-matrix-preview">
                  <div className="matrix-row matched">
                    <span className="status-indicator live" />
                    <span className="matrix-cell font-mono">127.0.0.1:54320</span>
                    <span className="matrix-arrow">⟷</span>
                    <span className="matrix-cell font-mono">PID 4211 [checkout-api]</span>
                    <span className="matrix-score">100% Deterministic</span>
                  </div>
                  <div className="matrix-row matched">
                    <span className="status-indicator live" />
                    <span className="matrix-cell font-mono">127.0.0.1:54322</span>
                    <span className="matrix-arrow">⟷</span>
                    <span className="matrix-cell font-mono">PID 4298 [payment-worker]</span>
                    <span className="matrix-score">99.8% Match</span>
                  </div>
                  <div className="matrix-row">
                    <span className="status-indicator pending" />
                    <span className="matrix-cell font-mono">127.0.0.1:54326</span>
                    <span className="matrix-arrow">⟷</span>
                    <span className="matrix-cell font-mono">PID 4310 [analytics-sync]</span>
                    <span className="matrix-score">Temporal &plusmn;2ms</span>
                  </div>
                </div>
              )}

              {activeTab === 'deadlock' && (
                <div className="deadlock-replay-preview">
                  <div className="replay-cycle-alert">
                    <span className="cycle-badge">Cycle Detected</span>
                    <span>T1 holds Lock(orders) waits for Lock(inventory) · T2 holds Lock(inventory) waits for Lock(orders)</span>
                  </div>
                  <div className="replay-nodes-row">
                    <div className="replay-box">Tx 1042 (Orders)</div>
                    <div className="replay-arrow-danger">Wait ➔</div>
                    <div className="replay-box">Tx 1043 (Inventory)</div>
                    <div className="replay-arrow-danger">Wait ➔ Cycle</div>
                  </div>
                </div>
              )}
            </div>

            <div className="mockup-footer">
              <span>Cross-layer latency: <strong>0.32 ms</strong></span>
              <span>Buffer pool hit: <strong>99.4%</strong></span>
              <span>eBPF probes active: <strong>14/14</strong></span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
