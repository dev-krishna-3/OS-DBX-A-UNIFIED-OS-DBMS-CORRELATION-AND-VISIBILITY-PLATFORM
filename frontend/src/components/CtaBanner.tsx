import { useState, type FormEvent } from 'react';
import { Mail, ArrowRight, CheckCircle2, ShieldCheck } from 'lucide-react';

interface CtaBannerProps {
  onSubscribeSuccess?: (email: string) => void;
}

export default function CtaBanner({ onSubscribeSuccess }: CtaBannerProps) {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!email || !email.includes('@')) return;
    setLoading(true);

    setTimeout(() => {
      setLoading(false);
      setSubmitted(true);
      onSubscribeSuccess?.(email);
    }, 450);
  };

  return (
    <section className="osdbx-cta-banner-wrapper" aria-label="Subscribe to OS-DBX updates">
      <div className="cta-banner-card">
        <div className="cta-banner-glow" aria-hidden="true" />
        
        <div className="cta-banner-content">
          <span className="cta-banner-pill">Enterprise Telemetry Network</span>
          <h2 className="cta-banner-heading">
            Stay Ahead of Kernel Stalls &amp; Database Contention
          </h2>
          <p className="cta-banner-subheading">
            Join 12,000+ systems engineers, DBAs, and infrastructure architects. Receive zero-overhead eBPF probe release alerts, deadlock forensic recipes, and benchmark reports.
          </p>

          {!submitted ? (
            <form className="cta-inline-email-form" onSubmit={handleSubmit}>
              <div className="cta-input-group">
                <Mail size={18} className="cta-mail-icon" aria-hidden="true" />
                <input
                  type="email"
                  required
                  placeholder="Enter your work email address…"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="cta-email-input"
                  aria-label="Email address for telemetry dispatch"
                />
              </div>
              <button
                type="submit"
                className="button button-primary cta-submit-button"
                disabled={loading}
              >
                {loading ? 'Subscribing…' : 'Subscribe to Dispatch'} <ArrowRight size={16} />
              </button>
            </form>
          ) : (
            <div className="cta-success-feedback" role="status">
              <CheckCircle2 size={20} className="success-icon" />
              <span>You&apos;re subscribed! Welcome to the OS-DBX systems engineering dispatch.</span>
            </div>
          )}

          <div className="cta-guarantee-row">
            <span className="guarantee-item"><ShieldCheck size={14} /> Zero spam guarantee</span>
            <span className="guarantee-dot">&bull;</span>
            <span className="guarantee-item">Unsubscribe anytime with 1 click</span>
            <span className="guarantee-dot">&bull;</span>
            <span className="guarantee-item">Strict enterprise privacy</span>
          </div>
        </div>
      </div>
    </section>
  );
}
