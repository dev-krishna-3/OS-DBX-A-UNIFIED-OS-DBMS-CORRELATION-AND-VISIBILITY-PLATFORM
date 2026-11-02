import { useState, type FormEvent } from 'react';
import {
  ArrowRight,
  Cpu,
  Database,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  ShieldAlert,
  UserRound,
  Waypoints,
} from 'lucide-react';
import { authApi } from '../../api';
import type { AuthUser } from '../../api/auth';

type AuthMode = 'Sign in' | 'Request access';

interface AuthPageProps {
  onAuthenticated: (user: AuthUser, emailNotificationSent: boolean) => void;
}

export default function AuthPage({ onAuthenticated }: AuthPageProps) {
  const [mode, setMode] = useState<AuthMode>('Sign in');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [requestedRole, setRequestedRole] = useState<'inspector' | 'member' | 'owner'>('inspector');
  const [reason, setReason] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const changeMode = (nextMode: AuthMode): void => {
    setMode(nextMode);
    setError('');
    setMessage('');
  };

  const submit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setBusy(true);
    setError('');
    setMessage('');

    try {
      if (mode === 'Request access') {
        if (password !== confirmPassword) throw new Error('Those passwords don’t match. Try again.');
        const result = await authApi.requestAccess({
          username,
          email,
          password,
          requested_role: requestedRole,
          reason,
        });
        setMessage(
          `Registration request for "${result.username}" submitted successfully! Your account is in PENDING status. An administrator will review your requested access level (${result.requested_role}) and approve your account before you can sign in.`
        );
        setMode('Sign in');
        setPassword('');
        setConfirmPassword('');
      } else {
        const result = await authApi.signIn(email, password);
        const user = await authApi.currentUser();
        setPassword('');
        onAuthenticated(user, result.email_notification_sent);
      }
    } catch (requestError) {
      if (mode === 'Sign in') authApi.signOut();
      setError(requestError instanceof Error ? requestError.message : 'We couldn’t complete that request. Try again.');
    } finally {
      setBusy(false);
    }
  };

  const isRequest = mode === 'Request access';

  return (
    <main className="auth-entry">
      <section className="login-card" aria-label="OS-DBX account access">
        <aside className="login-story" aria-label="About OS-DBX">
          <a className="login-brand" href="#account-form" aria-label="OS-DBX home">
            <span className="brand-mark" aria-hidden="true"><span /><span /><span /></span>
            <span className="login-brand-name">OS-DBX</span>
            <span className="login-brand-divider" />
            <span className="login-brand-caption">Cross-layer observability</span>
          </a>

          <div className="login-story-copy">
            <h1>Every event has a story.</h1>
            <p>Connect operating system activity with database behavior to understand what changed, where, and why.</p>
          </div>

          <div className="login-map" aria-label="Operating system signals connect through an identity bridge to database activity">
            <div className="login-map-line" aria-hidden="true"><span /></div>
            <div className="login-map-node login-map-os">
              <span className="login-map-icon"><Cpu size={19} strokeWidth={1.7} /></span>
              <span><strong>Operating system</strong><small>Processes & resources</small></span>
              <span className="login-node-signal" aria-hidden="true" />
            </div>
            <div className="login-map-node login-map-bridge">
              <span className="login-map-icon"><Waypoints size={19} strokeWidth={1.7} /></span>
              <span><strong>Identity bridge</strong><small>Evidence-based links</small></span>
              <span className="login-node-signal" aria-hidden="true" />
            </div>
            <div className="login-map-node login-map-dbms">
              <span className="login-map-icon"><Database size={19} strokeWidth={1.7} /></span>
              <span><strong>Database activity</strong><small>Queries & transactions</small></span>
              <span className="login-node-signal" aria-hidden="true" />
            </div>
          </div>

          <div className="login-story-foot">
            <span className="login-foot-mark"><span /><span /><span /></span>
            <span>One clear view across both layers.</span>
          </div>
        </aside>

        <section className="login-form-side">
          <div className="login-form-topline">
            <span className="login-secure"><LockKeyhole size={14} /> Secure workspace</span>
            <span className="login-local-label"><i /> Local environment</span>
          </div>

          <div className="login-form-content">
            <div className="login-form-heading">
              <h2>{isRequest ? 'Request workspace access' : 'Welcome back'}</h2>
              <p>{isRequest ? 'Submit your registration request for administrator approval and access role assignment.' : 'Sign in with your administrator or approved user credentials.'}</p>
            </div>

            <div className="login-tabs" role="tablist" aria-label="Account access">
              {(['Sign in', 'Request access'] as const).map((item) => (
                <button
                  type="button"
                  role="tab"
                  aria-selected={mode === item}
                  className={mode === item ? 'selected' : ''}
                  onClick={() => changeMode(item)}
                  key={item}
                >
                  {item}
                </button>
              ))}
            </div>

            {!isRequest && (
              <div
                style={{
                  marginBottom: '16px',
                  padding: '10px 14px',
                  borderRadius: '10px',
                  background: 'rgba(99, 102, 241, 0.09)',
                  border: '1px solid rgba(99, 102, 241, 0.22)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '8px',
                }}
              >
                <div style={{ fontSize: '12px', lineHeight: 1.4 }}>
                  <strong style={{ color: 'var(--color-primary, #6366f1)', display: 'block' }}>Administrator Login</strong>
                  <span style={{ color: 'var(--color-ink-subtle)' }}>admin · DevAdminPassword123!</span>
                </div>
                <button
                  type="button"
                  className="button button-secondary"
                  style={{ padding: '3px 10px', fontSize: '11px', height: '26px', whiteSpace: 'nowrap' }}
                  onClick={() => {
                    setEmail('admin');
                    setPassword('DevAdminPassword123!');
                    setError('');
                  }}
                >
                  Fill Admin
                </button>
              </div>
            )}

            <form id="account-form" className="login-form" onSubmit={submit}>
              {isRequest && (
                <label className="login-field" htmlFor="signup-username">
                  <span>Username</span>
                  <span className="login-input-wrap">
                    <UserRound size={17} aria-hidden="true" />
                    <input
                      id="signup-username"
                      required
                      minLength={3}
                      maxLength={100}
                      value={username}
                      onChange={(event) => setUsername(event.target.value)}
                      autoComplete="username"
                      placeholder="e.g. krishna or alex"
                    />
                  </span>
                </label>
              )}

              <label className="login-field" htmlFor="account-email">
                <span>{isRequest ? 'Email address' : 'Username or Email address'}</span>
                <span className="login-input-wrap">
                  <Mail size={17} aria-hidden="true" />
                  <input
                    id="account-email"
                    required
                    type={isRequest ? 'email' : 'text'}
                    maxLength={254}
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    autoComplete="username"
                    placeholder={isRequest ? 'you@example.com' : 'admin or your registered email'}
                  />
                </span>
              </label>

              {isRequest && (
                <>
                  <label className="login-field" htmlFor="request-role">
                    <span>Desired access level</span>
                    <span className="login-input-wrap">
                      <select
                        id="request-role"
                        value={requestedRole}
                        onChange={(event) => setRequestedRole(event.target.value as 'inspector' | 'member' | 'owner')}
                        style={{
                          width: '100%',
                          height: '42px',
                          padding: '0 12px',
                          border: 'none',
                          background: 'transparent',
                          color: 'var(--color-ink)',
                          fontSize: '13px',
                          outline: 'none',
                          cursor: 'pointer',
                        }}
                      >
                        <option value="inspector">Inspector (Read-only / Host Telemetry & Device Monitoring)</option>
                        <option value="member">Member (General Workspace Telemetry & Analysis)</option>
                        <option value="owner">Owner / Admin (Full Workspace Controls)</option>
                      </select>
                    </span>
                  </label>

                  <label className="login-field" htmlFor="request-reason">
                    <span>Purpose or note for administrator (optional)</span>
                    <span className="login-input-wrap">
                      <input
                        id="request-reason"
                        maxLength={500}
                        value={reason}
                        onChange={(event) => setReason(event.target.value)}
                        placeholder="e.g. Testing device agent on peer computer"
                      />
                    </span>
                  </label>
                </>
              )}

              <label className="login-field" htmlFor="account-password">
                <span>Password</span>
                <span className="login-input-wrap">
                  <LockKeyhole size={17} aria-hidden="true" />
                  <input
                    id="account-password"
                    required
                    minLength={isRequest ? 12 : 1}
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    autoComplete={isRequest ? 'new-password' : 'current-password'}
                    placeholder={isRequest ? 'Create a secure password (min 12 chars)' : 'Enter your password'}
                  />
                  <button className="password-visibility" type="button" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? 'Hide password' : 'Show password'}>
                    {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </span>
              </label>

              {isRequest && (
                <label className="login-field" htmlFor="account-password-confirm">
                  <span>Confirm password</span>
                  <span className="login-input-wrap">
                    <LockKeyhole size={17} aria-hidden="true" />
                    <input
                      id="account-password-confirm"
                      required
                      minLength={12}
                      type={showPassword ? 'text' : 'password'}
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                      autoComplete="new-password"
                      placeholder="Enter it again"
                    />
                  </span>
                </label>
              )}

              {!isRequest && (
                <div className="login-form-options">
                  <button type="button" className="forgot-link" onClick={() => setMessage('Password recovery is managed by the administrator. Contact your administrator to reset access.')}>Forgot password?</button>
                </div>
              )}

              {error && (
                <div
                  className="auth-feedback auth-error"
                  role="alert"
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '8px',
                    lineHeight: 1.5,
                  }}
                >
                  <ShieldAlert size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
                  <span>{error}</span>
                </div>
              )}
              {message && (
                <p className="auth-feedback auth-success" role="status">
                  {message}
                </p>
              )}

              <button type="submit" className="login-submit" disabled={busy}>
                <span>{busy ? 'Please wait…' : isRequest ? 'Submit access request' : 'Sign in'}</span>
                {!busy && <ArrowRight size={17} aria-hidden="true" />}
              </button>
            </form>

            <p className="login-security-note"><LockKeyhole size={14} /> Requests and sessions are encrypted and securely authenticated.</p>
            <p className="login-email-note">{isRequest ? 'Administrators are notified of pending requests.' : 'Signed in as workspace administrator or approved member.'}</p>
          </div>

          <footer className="login-form-footer">OS-DBX · Cross-layer observability workspace</footer>
        </section>
      </section>
    </main>
  );
}
