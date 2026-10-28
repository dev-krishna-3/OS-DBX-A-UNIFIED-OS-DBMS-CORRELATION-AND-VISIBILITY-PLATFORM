import { useState, type FormEvent } from 'react';
import {
  ArrowRight,
  Cpu,
  Database,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  UserRound,
  Waypoints,
} from 'lucide-react';
import { authApi } from '../../api';
import type { AuthUser } from '../../api/auth';

type AuthMode = 'Sign in' | 'Create account';

interface AuthPageProps {
  onAuthenticated: (user: AuthUser, emailNotificationSent: boolean) => void;
}

export default function AuthPage({ onAuthenticated }: AuthPageProps) {
  const [mode, setMode] = useState<AuthMode>('Sign in');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
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
      if (mode === 'Create account') {
        if (password !== confirmPassword) throw new Error('Those passwords don’t match. Try again.');
        const result = await authApi.signUp({ username, email, password });
        setMessage(result.email_notification_sent
          ? 'Your account is ready. A sign-up alert was sent to your email.'
          : 'Your account is ready. Email alerts aren’t configured yet.');
        setMode('Sign in');
        setPassword('');
        setConfirmPassword('');
      } else {
        const result = await authApi.signIn(email, password, rememberMe);
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

  const isSignUp = mode === 'Create account';

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
              <h2>{isSignUp ? 'Create your account' : 'Welcome back'}</h2>
              <p>{isSignUp ? 'Set up your account to enter the OS-DBX workspace.' : 'Sign in with your email to continue to your workspace.'}</p>
            </div>

            <div className="login-tabs" role="tablist" aria-label="Account access">
              {(['Sign in', 'Create account'] as const).map((item) => (
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
              {isSignUp && (
                <label className="login-field" htmlFor="signup-username">
                  <span>Your name</span>
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
                      placeholder="For example, Alex Morgan"
                    />
                  </span>
                </label>
              )}

              <label className="login-field" htmlFor="account-email">
                <span>Email address</span>
                <span className="login-input-wrap">
                  <Mail size={17} aria-hidden="true" />
                  <input
                    id="account-email"
                    required
                    type="email"
                    maxLength={254}
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    autoComplete="email"
                    placeholder="you@example.com"
                  />
                </span>
              </label>

              <label className="login-field" htmlFor="account-password">
                <span>Password</span>
                <span className="login-input-wrap">
                  <LockKeyhole size={17} aria-hidden="true" />
                  <input
                    id="account-password"
                    required
                    minLength={6}
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    autoComplete={isSignUp ? 'new-password' : 'current-password'}
                    placeholder={isSignUp ? 'Create a password' : 'Enter your password'}
                  />
                  <button className="password-visibility" type="button" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? 'Hide password' : 'Show password'}>
                    {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </span>
              </label>

              {isSignUp && (
                <label className="login-field" htmlFor="account-password-confirm">
                  <span>Confirm password</span>
                  <span className="login-input-wrap">
                    <LockKeyhole size={17} aria-hidden="true" />
                    <input
                      id="account-password-confirm"
                      required
                      minLength={6}
                      type={showPassword ? 'text' : 'password'}
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                      autoComplete="new-password"
                      placeholder="Enter it again"
                    />
                  </span>
                </label>
              )}

              {!isSignUp && (
                <div className="login-form-options">
                  <label className="remember-option"><input type="checkbox" checked={rememberMe} onChange={(event) => setRememberMe(event.target.checked)} /><span>Remember me</span></label>
                  <button type="button" className="forgot-link" onClick={() => setMessage('Password recovery is not set up yet. Please contact your OS-DBX administrator.')}>Forgot password?</button>
                </div>
              )}

              {error && <p className="auth-feedback auth-error" role="alert">{error}</p>}
              {message && <p className="auth-feedback auth-success" role="status">{message}</p>}

              <button type="submit" className="login-submit" disabled={busy}>
                <span>{busy ? 'Please wait…' : isSignUp ? 'Create account' : 'Sign in'}</span>
                {!busy && <ArrowRight size={17} aria-hidden="true" />}
              </button>
            </form>

            <p className="login-security-note"><LockKeyhole size={14} /> Your credentials are sent to the configured OS-DBX API.</p>
            <p className="login-email-note">{isSignUp ? 'A sign-up email alert is sent when SMTP is configured.' : 'New sign-in email alerts are sent when SMTP is configured.'}</p>
          </div>

          <footer className="login-form-footer">OS-DBX · Cross-layer observability workspace</footer>
        </section>
      </section>
    </main>
  );
}
