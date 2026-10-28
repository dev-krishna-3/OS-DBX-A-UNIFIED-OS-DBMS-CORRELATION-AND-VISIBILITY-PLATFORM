import { useState, type FormEvent } from 'react';
import { Check, LockKeyhole } from 'lucide-react';
import { authApi } from '../../api';
import type { AuthUser } from '../../api/auth';

type AuthMode = 'Sign in' | 'Create account';

export default function AuthPage({ onAuthenticated }: { onAuthenticated: (user: AuthUser, emailNotificationSent: boolean) => void }) {
  const [mode, setMode] = useState<AuthMode>('Sign in');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [uid, setUid] = useState('1001');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
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
        if (password !== confirmPassword) throw new Error('Passwords do not match.');
        const result = await authApi.signUp({ username, email, uid_linux: Number(uid), password });
        setMessage(result.email_notification_sent
          ? 'Account created. A sign-up notification was sent to your email.'
          : 'Account created. Email notification was not sent; check the SMTP configuration.');
        setMode('Sign in');
        setPassword('');
        setConfirmPassword('');
      } else {
        const result = await authApi.signIn(username, password);
        const user = await authApi.currentUser();
        setPassword('');
        onAuthenticated(user, result.email_notification_sent);
      }
    } catch (requestError) {
      if (mode === 'Sign in') authApi.signOut();
      setError(requestError instanceof Error ? requestError.message : 'Unable to complete the request.');
    } finally {
      setBusy(false);
    }
  };

  return <div className="auth-entry" data-theme="original">
    <main className="auth-entry-main">
      <a className="auth-entry-brand" href="#auth-form" aria-label="OS-DBX authentication">
        <span className="brand-mark" aria-hidden="true"><span /><span /><span /></span><strong>OS-DBX</strong><small>Cross-layer observability</small>
      </a>
      <div className="auth-entry-heading"><h1>Welcome to OS-DBX</h1><p>Sign in to open your operating system and database observability workspace.</p></div>
      <div className="content-two-col auth-entry-grid">
    <section className="surface-panel access-panel" id="auth-form">
      <div className="panel-heading"><div><h3>{mode}</h3><p>{mode === 'Sign in' ? 'Access the OS-DBX workspace' : 'Create an OS-DBX account'}</p></div><span className="event-tag tag-lavender">Secure access</span></div>
      <div className="access-tabs" role="tablist" aria-label="Account access">
        {(['Sign in', 'Create account'] as const).map((item) => <button type="button" role="tab" aria-selected={mode === item} className={mode === item ? 'chosen' : ''} onClick={() => changeMode(item)} key={item}>{item}</button>)}
      </div>
      <form onSubmit={submit}>
        <label className="field-label">Username<input required minLength={3} maxLength={100} value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" placeholder="Enter username" /></label>
        {mode === 'Create account' && <>
          <label className="field-label">Email<input required type="email" maxLength={254} value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" placeholder="you@example.com" /></label>
          <label className="field-label">Linux user ID (UID)<input required type="number" min="0" value={uid} onChange={(event) => setUid(event.target.value)} placeholder="For example, 1001" /></label>
        </>}
        <label className="field-label">Password<input required minLength={6} type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === 'Sign in' ? 'current-password' : 'new-password'} placeholder="Enter password" /></label>
        {mode === 'Create account' && <label className="field-label">Confirm password<input required minLength={6} type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} autoComplete="new-password" placeholder="Enter password again" /></label>}
        {error && <p className="auth-feedback auth-error" role="alert">{error}</p>}
        {message && <p className="auth-feedback auth-success" role="status"><Check size={14} />{message}</p>}
        <button type="submit" className="button button-primary access-submit" disabled={busy}>{busy ? 'Please wait…' : mode === 'Sign in' ? 'Continue to workspace' : 'Create account'}</button>
      </form>
      <p className="access-note"><LockKeyhole size={13} /> Credentials are sent only to the configured API. SMTP secrets stay on the server.</p>
    </section>
    <section className="surface-panel">
      <div className="panel-heading"><div><h3>Account notifications</h3><p>Sign-up and successful sign-in alerts</p></div></div>
      <div className="source-distinction"><strong>Email delivery</strong><p>Notifications are sent by the backend to the account email when SMTP is configured. Passwords and SMTP credentials are never included in email or stored by this page.</p></div>
      <div className="health-facts"><span>Sign-up alert <b>Sent to account email</b></span><span>Login alert <b>Sent after successful authentication</b></span><span>Delivery setup <b>Backend environment settings</b></span></div>
    </section>
      </div>
      <footer className="auth-entry-footer">Local observability workspace · Account credentials are handled by the OS-DBX API</footer>
    </main>
  </div>;
}
