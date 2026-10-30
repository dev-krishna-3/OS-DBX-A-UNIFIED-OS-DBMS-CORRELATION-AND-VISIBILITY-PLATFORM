import { useState, type FormEvent } from 'react';
import { Mail, Phone, MapPin, Clock, Send, CheckCircle2, ShieldCheck } from 'lucide-react';

interface ContactSectionProps {
  onSuccess?: () => void;
}

export default function ContactSection({ onSuccess }: ContactSectionProps) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [fleetSize, setFleetSize] = useState('1-10 nodes');
  const [message, setMessage] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);

    setTimeout(() => {
      setBusy(false);
      setSubmitted(true);
      onSuccess?.();
    }, 400);
  };

  return (
    <section className="osdbx-contact-section" aria-label="Contact OS-DBX systems engineering and enterprise support">
      <div className="section-header-centered">
        <span className="section-pill">Enterprise &amp; Technical Support</span>
        <h2 className="section-title">Talk to Systems Engineers</h2>
        <p className="section-lead">
          Have questions regarding high-throughput eBPF socket probes, custom PostgreSQL catalog integration, or air-gapped on-premise clusters? Reach out to our systems architecture team.
        </p>
      </div>

      <div className="contact-split-container">
        {/* Left Side: Contact Form */}
        <div className="contact-form-card">
          <div className="form-card-header">
            <h3>Send an Engineering Inquiry</h3>
            <p>Our systems leads respond within 4 business hours.</p>
          </div>

          {!submitted ? (
            <form onSubmit={handleSubmit} className="contact-form">
              <div className="form-row-dual">
                <label className="contact-field-label">
                  <span>Your Full Name</span>
                  <input
                    type="text"
                    required
                    placeholder="Alex Morgan"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </label>
                <label className="contact-field-label">
                  <span>Work Email</span>
                  <input
                    type="email"
                    required
                    placeholder="alex@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </label>
              </div>

              <label className="contact-field-label">
                <span>Infrastructure Fleet Size</span>
                <select value={fleetSize} onChange={(e) => setFleetSize(e.target.value)}>
                  <option value="1-10 nodes">1 - 10 Nodes (Dev / Staging)</option>
                  <option value="10-50 nodes">10 - 50 Nodes (Production Cluster)</option>
                  <option value="50-500 nodes">50 - 500 Nodes (Enterprise Multi-Region)</option>
                  <option value="500+ nodes">500+ Nodes (Hyperscale Dedicated VPC)</option>
                </select>
              </label>

              <label className="contact-field-label">
                <span>Technical Requirements / Inquiry</span>
                <textarea
                  required
                  rows={4}
                  placeholder="Tell us about your OS kernel versions, database engines (Postgres/MySQL), and high-concurrency challenges…"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                />
              </label>

              <button
                type="submit"
                className="button button-primary contact-submit-btn"
                disabled={busy}
              >
                {busy ? 'Dispatching Message…' : 'Submit Engineering Request'} <Send size={15} />
              </button>
            </form>
          ) : (
            <div className="contact-success-state" role="status">
              <CheckCircle2 size={36} className="contact-success-icon" />
              <h4>Inquiry Dispatched Successfully</h4>
              <p>Thank you, {name}. A systems engineer will review your cluster requirements and reach out at <strong>{email}</strong>.</p>
              <button
                type="button"
                className="button button-secondary"
                onClick={() => {
                  setSubmitted(false);
                  setMessage('');
                }}
              >
                Send Another Message
              </button>
            </div>
          )}
        </div>

        {/* Right Side: Contact Details & Office Hours */}
        <div className="contact-details-card">
          <div className="details-header">
            <h3>Direct Engineering Channels</h3>
            <p>Connect with our SRE and systems research offices.</p>
          </div>

          <div className="contact-items-list">
            <div className="contact-item">
              <div className="contact-icon-bubble">
                <Mail size={18} />
              </div>
              <div className="contact-item-info">
                <strong>Technical Support &amp; Architecture</strong>
                <a href="mailto:support@os-dbx.io">support@os-dbx.io</a>
                <small>Average response time: &lt; 2 hours</small>
              </div>
            </div>

            <div className="contact-item">
              <div className="contact-icon-bubble">
                <Phone size={18} />
              </div>
              <div className="contact-item-info">
                <strong>Enterprise On-Call Hotline</strong>
                <span>+1 (800) 555-OSDBX (7329)</span>
                <small>Dedicated 24/7/365 priority bridge for Fleet tiers</small>
              </div>
            </div>

            <div className="contact-item">
              <div className="contact-icon-bubble">
                <Clock size={18} />
              </div>
              <div className="contact-item-info">
                <strong>Operating Support Hours</strong>
                <span>Monday – Friday: 24 Hours Continuous</span>
                <span>Saturday – Sunday: Critical On-Call Coverage</span>
              </div>
            </div>

            <div className="contact-item">
              <div className="contact-icon-bubble">
                <MapPin size={18} />
              </div>
              <div className="contact-item-info">
                <strong>Engineering Headquarters</strong>
                <span>OS-DBX Labs, 500 Howard Street, Suite 400</span>
                <span>San Francisco, CA 94105</span>
              </div>
            </div>
          </div>

          <div className="contact-security-callout">
            <ShieldCheck size={18} className="shield-callout-icon" />
            <div>
              <strong>Air-Gapped &amp; Government Compliant</strong>
              <p>We provide full on-premises installation scripts with zero external telemetry egress.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
