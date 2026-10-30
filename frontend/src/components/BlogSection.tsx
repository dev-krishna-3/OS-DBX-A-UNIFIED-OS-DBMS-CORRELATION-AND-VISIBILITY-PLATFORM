import { useState } from 'react';
import { Clock, ArrowRight, Tag } from 'lucide-react';

interface BlogPost {
  id: string;
  category: 'OS Kernel' | 'Database Engine' | 'Deadlock Forensic' | 'Performance' | 'All';
  title: string;
  summary: string;
  author: string;
  date: string;
  readTime: string;
  imageAccent: string;
}

export default function BlogSection() {
  const [activeCategory, setActiveCategory] = useState<string>('All');

  const categories = ['All', 'OS Kernel', 'Database Engine', 'Deadlock Forensic', 'Performance'];

  const posts: BlogPost[] = [
    {
      id: '1',
      category: 'OS Kernel',
      title: 'How Socket Inode Matching Replaced Guesswork in Cross-Layer Tracing',
      summary: 'Exploring how eBPF socket lifecycle hooks pair client file descriptors with remote TCP endpoints in under 0.05ms.',
      author: 'Kernel Engineering Team',
      date: 'Oct 24, 2026',
      readTime: '6 min read',
      imageAccent: '#7665bd',
    },
    {
      id: '2',
      category: 'Database Engine',
      title: 'Demystifying PostgreSQL Lock Trees: From RowExclusive to Deadlock',
      summary: 'A deep architectural dive into pg_locks, wait-for cycle graphs, and how concurrent updates cascade into lock convoying.',
      author: 'Database Systems Group',
      date: 'Oct 19, 2026',
      readTime: '9 min read',
      imageAccent: '#5a9b7a',
    },
    {
      id: '3',
      category: 'Deadlock Forensic',
      title: 'Forensic Replay: Time-Traveling Through a 4-Transaction Deadlock Cycle',
      summary: 'Scrub through the exact sequence of resource acquisitions that triggered a production freeze, and learn how victim selection works.',
      author: 'SRE Incident Research',
      date: 'Oct 15, 2026',
      readTime: '8 min read',
      imageAccent: '#ce775f',
    },
    {
      id: '4',
      category: 'Performance',
      title: 'Benchmarking Observability Overhead: Achieving Under 1.2% CPU Impact',
      summary: 'Rigorous benchmark data across Linux and Windows server kernels comparing OS-DBX against traditional invasive APM agents.',
      author: 'Performance Lab',
      date: 'Oct 10, 2026',
      readTime: '5 min read',
      imageAccent: '#2f6298',
    },
    {
      id: '5',
      category: 'OS Kernel',
      title: 'VFS Block I/O Stalls and Postgres Checkpoint Spikes',
      summary: 'Why your fast queries randomly stall for 800ms: understanding kernel dirty page flushing and page cache writeback contention.',
      author: 'Linux Systems Research',
      date: 'Oct 04, 2026',
      readTime: '7 min read',
      imageAccent: '#9c8cce',
    },
    {
      id: '6',
      category: 'Database Engine',
      title: 'Validating ACID Schedules in What-If Simulations Before Migration',
      summary: 'Using Two-Phase Locking and Banker’s safety algorithm in pre-production staging to guarantee conflict-serializability.',
      author: 'Core Architecture',
      date: 'Sep 28, 2026',
      readTime: '11 min read',
      imageAccent: '#5781a8',
    },
  ];

  const filteredPosts = activeCategory === 'All'
    ? posts
    : posts.filter((p) => p.category === activeCategory);

  return (
    <section className="osdbx-blog-section" aria-label="Engineering insights and architecture blog">
      <div className="section-header-centered">
        <span className="section-pill">Systems Architecture Insights</span>
        <h2 className="section-title">Knowledge Base &amp; Engineering Articles</h2>
        <p className="section-lead">
          Deep dives into kernel socket telemetry, Postgres internal lock queues, and zero-overhead performance profiling.
        </p>

        {/* Category Filter Tags */}
        <div className="blog-filter-tags-row" role="group" aria-label="Filter blog posts by category">
          {categories.map((cat) => (
            <button
              type="button"
              key={cat}
              className={`filter-tag-pill ${activeCategory === cat ? 'active' : ''}`}
              onClick={() => setActiveCategory(cat)}
            >
              <Tag size={13} /> {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Grid of Post Cards */}
      <div className="blog-posts-grid">
        {filteredPosts.map((post) => (
          <article key={post.id} className="blog-card" aria-label={post.title}>
            <div className="blog-card-media" style={{ background: `linear-gradient(135deg, ${post.imageAccent}22, ${post.imageAccent}08)` }}>
              <div className="media-category-badge" style={{ borderColor: `${post.imageAccent}55`, color: post.imageAccent }}>
                {post.category}
              </div>
              <div className="media-art-accent" style={{ background: post.imageAccent }} />
            </div>

            <div className="blog-card-content">
              <div className="blog-card-meta">
                <span>{post.date}</span>
                <span className="meta-sep">&bull;</span>
                <span className="meta-read-time"><Clock size={12} /> {post.readTime}</span>
              </div>

              <h3 className="blog-card-title">{post.title}</h3>
              <p className="blog-card-summary">{post.summary}</p>

              <div className="blog-card-footer">
                <span className="blog-author">{post.author}</span>
                <button type="button" className="blog-read-link">
                  Read article <ArrowRight size={14} />
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
