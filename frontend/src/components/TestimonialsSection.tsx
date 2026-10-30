import { MessageCircle, Repeat2, Heart, Share, BadgeCheck } from 'lucide-react';

interface TestimonialPost {
  id: string;
  name: string;
  handle: string;
  avatarBg: string;
  avatarInitials: string;
  timestamp: string;
  quote: string;
  tags: string[];
  replies: string;
  retweets: string;
  likes: string;
}

export default function TestimonialsSection() {
  const testimonials: TestimonialPost[] = [
    {
      id: '1',
      name: 'Dan Henderson',
      handle: 'dan_systems_sre',
      avatarBg: '#7665bd',
      avatarInitials: 'DH',
      timestamp: '2h',
      quote: 'We had an intermittent latency spike in our checkout cluster that evaded APM tools for 3 weeks. Plugged in OS-DBX: in 45 seconds we saw the exact OS thread getting starved by an unexpected fsync storm during Postgres checkpointing. Incredible platform.',
      tags: ['#eBPF', '#PostgreSQL', '#Observability'],
      replies: '34',
      retweets: '142',
      likes: '891',
    },
    {
      id: '2',
      name: 'Dr. Sarah Lin',
      handle: 'sarah_db_internals',
      avatarBg: '#5a9b7a',
      avatarInitials: 'SL',
      timestamp: '5h',
      quote: 'The cross-layer identity bridge in OS-DBX is pure engineering elegance. Seeing a Linux socket inode mapped with 100% determinism to a backend Postgres PID and transaction lock cycle without CPU overhead makes other monitoring feel like guessing.',
      tags: ['#DatabaseEngineering', '#LinuxKernel', '#OSDBX'],
      replies: '19',
      retweets: '88',
      likes: '512',
    },
    {
      id: '3',
      name: 'Marcus Vance',
      handle: 'marcus_vance_ops',
      avatarBg: '#ce775f',
      avatarInitials: 'MV',
      timestamp: '1d',
      quote: 'Forensic deadlock replay saved our Black Friday weekend. Being able to scrub the timeline and watch transaction T1 and T2 fight for RowExclusiveLocks with visual blast radius metrics is like having time-travel debugging for our database fleet.',
      tags: ['#DevOps', '#SRE', '#DatabaseReliability'],
      replies: '42',
      retweets: '204',
      likes: '1.2k',
    },
    {
      id: '4',
      name: 'Elena Rostova',
      handle: 'elena_cloud_infra',
      avatarBg: '#5781a8',
      avatarInitials: 'ER',
      timestamp: '2d',
      quote: 'Replaced three disjointed monitoring agents with OS-DBX. Our CPU overhead dropped from 8.4% to under 1.2%, and for the first time our systems engineers and DBAs speak the exact same language in post-mortems.',
      tags: ['#Performance', '#DistributedSystems', '#ZeroOverhead'],
      replies: '15',
      retweets: '67',
      likes: '430',
    },
    {
      id: '5',
      name: 'Rajiv Patel',
      handle: 'rajiv_db_architect',
      avatarBg: '#9c8cce',
      avatarInitials: 'RP',
      timestamp: '3d',
      quote: 'The What-If scenario engine and ACID simulation lab alone are worth gold. We test our concurrent transaction schedules in the lab before rolling out schema changes. Zero production deadlocks since onboarding.',
      tags: ['#ACID', '#TransactionSchedules', '#Concurrency'],
      replies: '28',
      retweets: '115',
      likes: '784',
    },
    {
      id: '6',
      name: 'Kavita Menon',
      handle: 'kavita_kernel_dev',
      avatarBg: '#2f6298',
      avatarInitials: 'KM',
      timestamp: '4d',
      quote: 'Unified OS-to-DBMS console is the missing link in modern observability. Seeing VFS block I/O right next to SQL query execution times gives you complete visibility from metal to query cache.',
      tags: ['#KernelTracing', '#Syscalls', '#Postgres'],
      replies: '11',
      retweets: '53',
      likes: '349',
    },
  ];

  return (
    <section className="osdbx-testimonials-section" aria-label="Engineers and DBAs community feedback">
      <div className="section-header-centered">
        <span className="section-pill">Trusted by Systems Engineers</span>
        <h2 className="section-title">Loved by SREs, DBAs &amp; Infrastructure Leads</h2>
        <p className="section-lead">
          See how high-concurrency engineering teams use OS-DBX to diagnose production stalls and resolve deadlocks in seconds.
        </p>
      </div>

      <div className="testimonials-masonry-grid">
        {testimonials.map((post) => (
          <article key={post.id} className="tweet-card" aria-label={`Testimonial from ${post.name}`}>
            <div className="tweet-header">
              <div className="tweet-author-avatar" style={{ backgroundColor: post.avatarBg }}>
                {post.avatarInitials}
              </div>
              <div className="tweet-author-meta">
                <div className="tweet-name-row">
                  <span className="tweet-name">{post.name}</span>
                  <BadgeCheck size={16} className="tweet-verified-icon" aria-label="Verified Engineer" />
                </div>
                <span className="tweet-handle">@{post.handle} &bull; {post.timestamp}</span>
              </div>
              <span className="x-logo-mark" aria-hidden="true">&#x1D54F;</span>
            </div>

            <div className="tweet-body">
              <p className="tweet-quote">{post.quote}</p>
              <div className="tweet-tags">
                {post.tags.map((tag, idx) => (
                  <span key={idx} className="tweet-tag">{tag}</span>
                ))}
              </div>
            </div>

            <div className="tweet-footer-actions">
              <span className="tweet-action-btn"><MessageCircle size={15} /> {post.replies}</span>
              <span className="tweet-action-btn"><Repeat2 size={15} /> {post.retweets}</span>
              <span className="tweet-action-btn heart-btn"><Heart size={15} /> {post.likes}</span>
              <span className="tweet-action-btn"><Share size={15} /></span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
