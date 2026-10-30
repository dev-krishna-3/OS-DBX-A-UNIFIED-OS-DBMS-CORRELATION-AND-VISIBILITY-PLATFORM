import { useState } from 'react';
import { Check, Sparkles, Server, Zap, Shield, ArrowRight } from 'lucide-react';

interface PricingSectionProps {
  onSelectTier?: (tierName: string) => void;
}

export default function PricingSection({ onSelectTier }: PricingSectionProps) {
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'annual'>('annual');

  const tiers = [
    {
      id: 'starter',
      name: 'Developer Community',
      badge: null,
      priceMonthly: 0,
      priceAnnual: 0,
      credits: '500,000',
      nodes: '1 Host Node',
      description: 'Perfect for local debugging, developer workstations, and OSS exploration.',
      features: [
        '1 Monitored OS Host (Linux or Windows)',
        '1 Monitored PostgreSQL / MySQL instance',
        '500,000 monthly telemetry trace credits',
        '24-hour trace retention & forensic replay',
        'Full CLI parity & simulation workbenches',
        'Community Discord & GitHub support',
      ],
      cta: 'Start Free',
      popular: false,
    },
    {
      id: 'pro',
      name: 'Production Cluster',
      badge: 'MOST POPULAR',
      priceMonthly: 99,
      priceAnnual: 79,
      credits: '10,000,000',
      nodes: 'Up to 10 Nodes',
      description: 'Ideal for fast-growing engineering teams and production database clusters.',
      features: [
        'Up to 10 OS Host Nodes with eBPF probes',
        'Up to 10 PostgreSQL / MySQL primary & replicas',
        '10,000,000 monthly telemetry trace credits',
        '30-day high-resolution forensic replay',
        'Automated deadlock cycle detection & alerts',
        'Role-Based Access Control (RBAC) & 2FA',
        'Priority email & Slack support',
      ],
      cta: 'Provision Cluster',
      popular: true,
    },
    {
      id: 'fleet',
      name: 'Enterprise Fleet',
      badge: 'BEST VALUE',
      priceMonthly: 349,
      priceAnnual: 299,
      credits: '100,000,000',
      nodes: 'Unlimited Nodes',
      description: 'For mission-critical enterprises requiring dedicated VPC and strict compliance.',
      features: [
        'Unlimited OS Host Nodes & Kubernetes clusters',
        'Unlimited PostgreSQL, MySQL & Oracle backends',
        '100,000,000 monthly telemetry trace credits',
        '1-year unlimited trace retention & audit logs',
        'Custom eBPF probes & kernel trace filters',
        'Dedicated VPC / On-Premise air-gapped deployment',
        '24/7/365 dedicated systems engineer SLA',
      ],
      cta: 'Contact Architecture Team',
      popular: false,
    },
  ];

  return (
    <section className="osdbx-pricing-section" aria-label="OS-DBX telemetry plans and credit pack tiles">
      <div className="section-header-centered">
        <span className="section-pill">Capacity &amp; Fleet Licensing</span>
        <h2 className="section-title">Transparent Telemetry Credit Packs</h2>
        <p className="section-lead">
          Scale effortlessly from single developer instances to multi-region cloud database fleets with predictability and zero hidden ingestion fees.
        </p>

        <div className="pricing-toggle-wrap">
          <button
            type="button"
            className={`toggle-btn ${billingCycle === 'monthly' ? 'active' : ''}`}
            onClick={() => setBillingCycle('monthly')}
          >
            Monthly Billing
          </button>
          <button
            type="button"
            className={`toggle-btn ${billingCycle === 'annual' ? 'active' : ''}`}
            onClick={() => setBillingCycle('annual')}
          >
            Annual Billing <span className="discount-pill">Save 20%</span>
          </button>
        </div>
      </div>

      <div className="pricing-grid-container">
        {tiers.map((tier) => {
          const price = billingCycle === 'annual' ? tier.priceAnnual : tier.priceMonthly;

          return (
            <div
              key={tier.id}
              className={`pricing-card ${tier.popular ? 'card-highlighted' : ''}`}
            >
              {tier.badge && (
                <div className={`pricing-card-badge ${tier.popular ? 'badge-popular' : 'badge-best-value'}`}>
                  <Sparkles size={13} /> {tier.badge}
                </div>
              )}

              <div className="card-top-block">
                <h3 className="tier-name">{tier.name}</h3>
                <p className="tier-description">{tier.description}</p>
                <div className="tier-price-row">
                  <span className="price-currency">$</span>
                  <span className="price-amount">{price}</span>
                  <span className="price-period">/ month</span>
                </div>
                {billingCycle === 'annual' && price > 0 && (
                  <span className="billing-annual-note">Billed annually (${price * 12}/yr)</span>
                )}
              </div>

              <div className="card-credits-block">
                <div className="credit-metric">
                  <Zap size={16} className="credit-icon" />
                  <div>
                    <strong>{tier.credits}</strong>
                    <span>Telemetry trace credits / mo</span>
                  </div>
                </div>
                <div className="credit-metric">
                  <Server size={16} className="credit-icon" />
                  <div>
                    <strong>{tier.nodes}</strong>
                    <span>Monitored infrastructure nodes</span>
                  </div>
                </div>
              </div>

              <div className="tier-divider" />

              <ul className="tier-feature-list">
                {tier.features.map((feat, idx) => (
                  <li key={idx}>
                    <Check size={16} className="feature-check" />
                    <span>{feat}</span>
                  </li>
                ))}
              </ul>

              <button
                type="button"
                className={`button ${tier.popular ? 'button-primary' : 'button-secondary'} pricing-cta`}
                onClick={() => onSelectTier?.(tier.name)}
              >
                {tier.cta} <ArrowRight size={15} />
              </button>
            </div>
          );
        })}
      </div>

      <div className="pricing-footer-note">
        <Shield size={16} />
        <span>All plans include 14-day free enterprise trial, data encryption at rest &amp; in-transit, and SOC-2 Type II audit logging.</span>
      </div>
    </section>
  );
}
