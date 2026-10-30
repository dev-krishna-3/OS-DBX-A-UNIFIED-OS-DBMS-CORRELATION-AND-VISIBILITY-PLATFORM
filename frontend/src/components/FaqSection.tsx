import { User, Sparkles } from 'lucide-react';

interface ChatMessage {
  id: string;
  sender: 'user' | 'agent';
  senderName: string;
  avatarBg: string;
  time: string;
  questionOrTopic?: string;
  content: string;
  tags?: string[];
}

export default function FaqSection() {
  const conversation: ChatMessage[] = [
    {
      id: '1',
      sender: 'user',
      senderName: 'DevOps Lead',
      avatarBg: '#5781a8',
      time: '10:41 AM',
      content: 'How does OS-DBX link an OS process to a specific PostgreSQL backend without heavy tracing overhead?',
    },
    {
      id: '2',
      sender: 'agent',
      senderName: 'OS-DBX Assistant',
      avatarBg: '#7665bd',
      time: '10:41 AM',
      content: 'OS-DBX uses kernel socket inode correlation. When an application initiates a query, our lightweight probe captures the client socket inode and port (e.g., 127.0.0.1:54320). We simultaneously inspect the database connection catalog via pg_stat_activity. By pairing these identifiers, we establish a 100% deterministic match with microsecond precision while maintaining under 1.2% CPU overhead.',
      tags: ['Socket Inode', 'pg_stat_activity', '<1.2% Overhead'],
    },
    {
      id: '3',
      sender: 'user',
      senderName: 'Lead DBA',
      avatarBg: '#5a9b7a',
      time: '10:43 AM',
      content: 'Can we replay a deadlock that happened at 3 AM to understand the exact lock order?',
    },
    {
      id: '4',
      sender: 'agent',
      senderName: 'OS-DBX Assistant',
      avatarBg: '#7665bd',
      time: '10:43 AM',
      content: 'Yes! The Deadlock Forensic Replay engine stores the exact dependency wait-for graph and resource acquisition sequence. You can scrub the playback scrubber backward and forward to view which transaction held RowExclusiveLock, which one requested ExclusiveLock, and what recommendation would have averted the cycle.',
      tags: ['Deadlock Replay', 'Wait-For Graph', 'Causal Timeline'],
    },
    {
      id: '5',
      sender: 'user',
      senderName: 'Platform Architect',
      avatarBg: '#ce775f',
      time: '10:46 AM',
      content: 'Does OS-DBX require running in root/admin mode or modifying Postgres server code?',
    },
    {
      id: '6',
      sender: 'agent',
      senderName: 'OS-DBX Assistant',
      avatarBg: '#7665bd',
      time: '10:46 AM',
      content: 'No server code modifications or proprietary PostgreSQL extensions are needed! OS-DBX connects via standard PostgreSQL telemetry schemas (pg_stat_activity, pg_locks) and reads standard OS procfs / socket tables. It is designed for zero production disruption.',
      tags: ['Zero-Intrusion', 'Standard SQL', 'Airgap Friendly'],
    },
    {
      id: '7',
      sender: 'user',
      senderName: 'SRE Lead',
      avatarBg: '#2f6298',
      time: '10:48 AM',
      content: 'How does the What-If scenario planner help before deploying high-concurrency database migrations?',
    },
    {
      id: '8',
      sender: 'agent',
      senderName: 'OS-DBX Assistant',
      avatarBg: '#7665bd',
      time: '10:48 AM',
      content: 'The What-If engine runs deterministic simulations (Banker’s deadlock avoidance, Two-Phase Locking, Strict 2PL, and WAL recovery schedules). You feed your proposed transaction sequence, and the planner detects whether concurrent execution would lead to lock convoying or serializability violations.',
      tags: ['What-If Planner', '2PL Simulation', 'ACID Safety'],
    },
  ];

  return (
    <section className="osdbx-faq-chat-section" aria-label="Frequently Asked Questions in chat format">
      <div className="section-header-centered">
        <span className="section-pill">Interactive Knowledge &amp; Q&amp;A</span>
        <h2 className="section-title">Frequently Asked Questions</h2>
        <p className="section-lead">
          Everything you need to know about OS-to-DBMS correlation, eBPF safety, and forensic deadlock detection.
        </p>
      </div>

      <div className="faq-chat-container">
        <div className="faq-chat-header">
          <div className="chat-status-left">
            <span className="chat-status-dot" />
            <span>Systems Architecture Q&amp;A Channel</span>
          </div>
          <div className="chat-header-actions">
            <span className="chat-active-users">3 Engineers Online</span>
          </div>
        </div>

        <div className="faq-chat-stream">
          {conversation.map((msg) => {
            const isUser = msg.sender === 'user';

            return (
              <div
                key={msg.id}
                className={`chat-bubble-row ${isUser ? 'chat-row-user' : 'chat-row-agent'}`}
              >
                {!isUser && (
                  <div className="chat-avatar agent-avatar" style={{ backgroundColor: msg.avatarBg }}>
                    <Sparkles size={16} />
                  </div>
                )}

                <div className={`chat-bubble ${isUser ? 'bubble-user' : 'bubble-agent'}`}>
                  <div className="chat-bubble-top">
                    <span className="chat-sender-name">{msg.senderName}</span>
                    <span className="chat-timestamp">{msg.time}</span>
                  </div>

                  <p className="chat-bubble-body">{msg.content}</p>

                  {msg.tags && (
                    <div className="chat-bubble-tags">
                      {msg.tags.map((tag, i) => (
                        <span key={i} className="bubble-tag">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {isUser && (
                  <div className="chat-avatar user-avatar" style={{ backgroundColor: msg.avatarBg }}>
                    <User size={16} />
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="faq-chat-footer">
          <div className="chat-input-fake">
            <span>Have another systems architecture question? Check our Documentation or reach out to Support.</span>
          </div>
        </div>
      </div>
    </section>
  );
}
