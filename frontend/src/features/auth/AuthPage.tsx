import { useState, type FormEvent } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  Cpu,
  Database,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  ShieldAlert,
  ShieldCheck,
  Smartphone,
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

  // Two-step verification (Google Authenticator) challenge state
  const [isTotpChallenge, setIsTotpChallenge] = useState(false);
  const [challengeToken, setChallengeToken] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [targetUsername, setTargetUsername] = useState('');

  const changeMode = (nextMode: AuthMode): void => {
    setMode(nextMode);
    setError('');
    setMessage('');
    setIsTotpChallenge(false);
  };

  const cancelTotpChallenge = (): void => {
    setIsTotpChallenge(false);
    setChallengeToken('');
    setTotpCode('');
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
        if (result.requires_totp && result.challenge_token) {
          setIsTotpChallenge(true);
          setChallengeToken(result.challenge_token);
          setTotpCode('');
          setTargetUsername(email);
          return;
        }
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

  const submitTotpChallenge = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    const cleanCode = totpCode.trim();
    if (cleanCode.length !== 6) {
      setError('Please enter the full 6-digit verification code.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const result = await authApi.verifyTotpLogin(challengeToken, cleanCode);
      const user = await authApi.currentUser();
      setPassword('');
      setTotpCode('');
      setIsTotpChallenge(false);
      onAuthenticated(user, result.email_notification_sent);
    } catch (totpErr) {
      setError(totpErr instanceof Error ? totpErr.message : 'Invalid 6-digit code. Please check your Google Authenticator app and try again.');
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
            <span className="login-local-label"><i /> Cloud workspace</span>
          </div>

          {isTotpChallenge ? (
            <div className="login-form-content">
              <div className="login-form-heading">
                <div
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '7px',
                    padding: '5px 12px',
                    borderRadius: '20px',
                    background: 'rgba(99, 102, 241, 0.08)',
                    border: '1px solid rgba(99, 102, 241, 0.2)',
                    color: 'var(--color-primary, #6366f1)',
                    fontSize: '11px',
                    fontWeight: 700,
                    marginBottom: '14px',
                    letterSpacing: '0.02em',
                  }}
                >
                  <ShieldCheck size={14} /> Two-Factor Authentication
                </div>
                <h2>Security code</h2>
                <p>
                  Google Authenticator is enabled for <strong style={{ color: 'var(--color-ink)' }}>{targetUsername || email}</strong>.
                  Enter the 6-digit code from your authenticator app to complete sign in.
                </p>
              </div>

              <form className="login-form" onSubmit={submitTotpChallenge}>
                <label className="login-field" htmlFor="totp-challenge-code">
                  <span style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>6-Digit Verification Code</span>
                    <span style={{ fontSize: '11px', color: 'var(--color-muted)', fontWeight: 500, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      <Smartphone size={12} /> Google Authenticator
                    </span>
                  </span>
                  <span className="login-input-wrap" style={{ padding: '0 14px' }}>
                    <input
                      id="totp-challenge-code"
                      required
                      autoFocus
                      type="text"
                      inputMode="numeric"
                      pattern="[0-9]*"
                      maxLength={6}
                      value={totpCode}
                      onChange={(event) => {
                        const val = event.target.value.replace(/\D/g, '').slice(0, 6);
                        setTotpCode(val);
                        if (error) setError('');
                      }}
                      autoComplete="one-time-code"
                      placeholder="000 000"
                      style={{
                        textAlign: 'center',
                        fontSize: '22px',
                        fontWeight: 700,
                        letterSpacing: '0.35em',
                        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                      }}
                    />
                  </span>
                </label>

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

                <button
                  type="submit"
                  className="login-submit"
                  disabled={busy || totpCode.trim().length !== 6}
                >
                  <span>{busy ? 'Verifying security code…' : 'Verify & Sign in'}</span>
                  {!busy && <ArrowRight size={17} aria-hidden="true" />}
                </button>

                <div style={{ display: 'flex', justifyContent: 'center', marginTop: '4px' }}>
                  <button
                    type="button"
                    className="forgot-link"
                    onClick={cancelTotpChallenge}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontSize: '12px',
                      color: 'var(--color-muted)',
                      textDecoration: 'none',
                      cursor: 'pointer',
                    }}
                  >
                    <ArrowLeft size={14} /> Back to credentials
                  </button>
                </div>
              </form>

              <p className="login-security-note">
                <LockKeyhole size={14} /> Verification codes refresh every 30 seconds on your mobile authenticator.
              </p>
            </div>
          ) : (
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
                    <button
                      type="button"
                      className="forgot-link"
                      style={{ color: 'var(--color-primary, #6366f1)', fontWeight: 500 }}
                      onClick={() => {
                        setEmail('admin');
                        setPassword('AdminPass123456!');
                        setError('');
                      }}
                    >
                      Quick-fill admin
                    </button>
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
          )}

          <footer className="login-form-footer">OS-DBX · Cross-layer observability workspace</footer>
        </section>
      </section>
    </main>
  );
}
