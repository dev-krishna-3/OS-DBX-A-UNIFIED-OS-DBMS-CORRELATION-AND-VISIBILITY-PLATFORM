import { useState } from 'react';
import { X, Monitor, Database, GitBranch, ArrowRight, Play, Terminal } from 'lucide-react';

interface OnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onFinish: () => void;
}

export default function OnboardingModal({ isOpen, onClose, onFinish }: OnboardingModalProps) {
  const [currentStep, setCurrentStep] = useState(0);

  if (!isOpen) return null;

  const steps = [
    {
      title: 'Deploy OS Collector Agent',
      subtitle: 'Capture thread execution, memory, and TCP socket file descriptors with under 1.2% CPU overhead.',
      icon: Monitor,
      command: 'python -m app.collector.os_collector --target local --interval 500ms',
      badge: 'Step 1 of 3: Kernel Telemetry',
    },
    {
      title: 'Link Database Performance Engine',
      subtitle: 'Connect to PostgreSQL pg_stat_activity and lock catalogs to stream transactions & queries.',
      icon: Database,
      command: 'python -m app.collector.dbms_collector --host 127.0.0.1 --port 5432 --db osdbx_demo',
      badge: 'Step 2 of 3: DBMS Telemetry',
    },
    {
      title: 'Verify Causal Identity Bridge',
      subtitle: 'Pair socket inodes with PostgreSQL client connections for 100% deterministic cross-layer traces.',
      icon: GitBranch,
      command: 'python -m app.engine.correlation --mode deterministic --eval-deadlocks',
      badge: 'Step 3 of 3: Correlation Engine',
    },
  ];

  const active = steps[currentStep];
  const StepIcon = active.icon;

  return (
    <div className="osdbx-modal-backdrop" role="dialog" aria-modal="true" aria-label="Quick-start onboarding guide">
      <div className="onboarding-modal-card">
        <button
          type="button"
          className="modal-close-button"
          onClick={onClose}
          aria-label="Close guide"
        >
          <X size={18} />
        </button>

        <div className="onboarding-modal-header">
          <div className="onboarding-badge">{active.badge}</div>
          <div className="onboarding-step-indicators">
            {steps.map((_, idx) => (
              <span
                key={idx}
                className={`step-dot ${idx === currentStep ? 'active' : idx < currentStep ? 'completed' : ''}`}
              />
            ))}
          </div>
        </div>

        <div className="onboarding-modal-body">
          <div className="onboarding-icon-illustration">
            <div className="illustration-glow" aria-hidden="true" />
            <div className="illustration-icon-wrapper">
              <StepIcon size={42} strokeWidth={1.5} />
            </div>
          </div>

          <h2 className="onboarding-title">{active.title}</h2>
          <p className="onboarding-subtitle">{active.subtitle}</p>

          <div className="onboarding-command-box">
            <div className="command-box-top">
              <span className="box-dot" />
              <span className="box-dot" />
              <span className="box-dot" />
              <span className="box-label"><Terminal size={12} /> PowerShell / Bash</span>
            </div>
            <code>{active.command}</code>
          </div>
        </div>

        <div className="onboarding-modal-footer">
          {currentStep > 0 ? (
            <button
              type="button"
              className="button button-secondary"
              onClick={() => setCurrentStep((prev) => Math.max(0, prev - 1))}
            >
              Previous Step
            </button>
          ) : (
            <button
              type="button"
              className="button button-quiet"
              onClick={onClose}
            >
              Skip Setup
            </button>
          )}

          {currentStep < steps.length - 1 ? (
            <button
              type="button"
              className="button button-primary"
              onClick={() => setCurrentStep((prev) => Math.min(steps.length - 1, prev + 1))}
            >
              Next Step <ArrowRight size={15} />
            </button>
          ) : (
            <button
              type="button"
              className="button button-primary"
              onClick={() => {
                onFinish();
                onClose();
              }}
            >
              <Play size={14} fill="currentColor" /> Enter Live Workspace
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
