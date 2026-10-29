import { useState, type FormEvent } from 'react';
import {
  ArrowRight, Cpu, Database, Eye, EyeOff, KeyRound, LockKeyhole,
  Mail, UserRound, Waypoints,
} from 'lucide-react';
import { authApi } from '../../api';
import type { AuthUser, TotpEnableResult, TotpSetupResult } from '../../api/auth';

type AuthMode = 'Sign in' | 'Create account';
type AuthPhase = 'credentials' | 'verify-email' | 'verify-totp' | 'setup-totp' | 'recovery-codes';

interface AuthPageProps {
  onAuthenticated: (user: AuthUser, emailNotificationSent: boolean) => void;
}

export default function AuthPage({ onAuthenticated }: AuthPageProps) {
  const [mode, setMode] = useState<AuthMode>('Sign in');
  const [phase, setPhase] = useState<AuthPhase>('credentials');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [emailCode, setEmailCode] = useState('');
  const [authenticatorCode, setAuthenticatorCode] = useState('');
  const [challengeToken, setChallengeToken] = useState('');
  const [setup, setSetup] = useState<TotpSetupResult | null>(null);
  const [pendingSession, setPendingSession] = useState<TotpEnableResult | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const isSignUp = mode === 'Create account';
  const isCredentials = phase === 'credentials';

  const changeMode = (nextMode: AuthMode): void => {
    setMode(nextMode);
    setPhase('credentials');
    setError('');
    setMessage('');
  };

  const requestEmailCode = async (): Promise<void> => {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const result = await authApi.startEmailVerification(email);
      if (!result.verification_email_sent) {
        throw new Error('We couldn’t send the code. Check the backend SMTP settings and try again.');
      }
      setPhase('verify-email');
      setMessage(`A six-digit verification code was sent to ${email}.`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'We couldn’t send the code. Try again.');
    } finally {
      setBusy(false);
    }
  };

  const completeSession = async (accessToken: string, emailNotificationSent: boolean): Promise<void> => {
    authApi.activateSession(accessToken, rememberMe);
    try {
      const user = await authApi.currentUser();
      onAuthenticated(user, emailNotificationSent);
    } catch (requestError) {
      authApi.signOut();
      throw requestError;
    }
  };

  const submit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setBusy(true);
    setError('');
    setMessage('');

    try {
      if (phase === 'verify-email') {
        const result = await authApi.signUp({ username, email, password, verification_code: emailCode });
        setMode('Sign in');
        setPhase('credentials');
        setPassword('');
        setConfirmPassword('');
        setEmailCode('');
        setMessage(result.email_notification_sent
          ? 'Your email is verified and your account is ready. Sign in to set up Google Authenticator.'
          : 'Your email is verified and your account is ready. Sign in to set up Google Authenticator.');
        return;
      }

      if (phase === 'verify-totp') {
        const result = await authApi.verifyTotp(challengeToken, authenticatorCode, rememberMe);
        await completeSession(result.access_token, result.email_notification_sent);
        return;
      }

      if (phase === 'setup-totp') {
        const result = await authApi.enableTotp(challengeToken, authenticatorCode);
        setPendingSession(result);
        setPhase('recovery-codes');
        return;
      }

      if (isSignUp) {
        if (password !== confirmPassword) throw new Error('Those passwords don’t match. Try again.');
        await requestEmailCode();
        return;
      }

      const result = await authApi.signIn(email, password);
      if (result.access_token) {
        await completeSession(result.access_token, result.email_notification_sent);
      } else if (result.challenge_token) {
        setChallengeToken(result.challenge_token);
        if (result.requires_totp_setup) {
          const setupResult = await authApi.startTotpSetup(result.challenge_token);
          setSetup(setupResult);
          setPhase('setup-totp');
        } else if (result.requires_totp) {
          setPhase('verify-totp');
        }
      } else {
        throw new Error('The sign-in response was incomplete. Please try again.');
      }
      setPassword('');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'We couldn’t complete that request. Try again.');
    } finally {
      setBusy(false);
    }
  };

  const saveRecoveryCodesAndContinue = async (): Promise<void> => {
    if (!pendingSession) return;
    setBusy(true);
    setError('');
    try {
      await completeSession(pendingSession.access_token, pendingSession.email_notification_sent);
    } catch (requestError) {
      authApi.signOut();
      setError(requestError instanceof Error ? requestError.message : 'We couldn’t open your account. Please sign in again.');
    } finally {
      setBusy(false);
    }
  };

  const resendEmailCode = async (): Promise<void> => {
    setEmailCode('');
    await requestEmailCode();
  };

  const copyRecoveryCodes = async (): Promise<void> => {
    if (!pendingSession) return;
    try {
      await navigator.clipboard.writeText(pendingSession.recovery_codes.join('\n'));
      setMessage('Recovery codes copied. Store them somewhere private.');
      setError('');
    } catch {
      setError('Clipboard access is unavailable. Select and copy the codes manually.');
    }
  };

  const heading = phase === 'verify-email'
    ? 'Check your email'
    : phase === 'verify-totp'
      ? 'Two-step verification'
      : phase === 'setup-totp'
        ? 'Set up Google Authenticator'
        : phase === 'recovery-codes'
          ? 'Save your recovery codes'
          : isSignUp ? 'Create your account' : 'Welcome back';
  const description = phase === 'verify-email'
    ? `Enter the six-digit code sent to ${email}. It expires in 10 minutes.`
    : phase === 'verify-totp'
      ? 'Enter the current code from your authenticator app, or use one recovery code.'
      : phase === 'setup-totp'
        ? 'Scan the QR code, then enter the six-digit code from the app to finish setup.'
        : phase === 'recovery-codes'
          ? 'Authenticator verification is on. Keep these one-time codes somewhere safe.'
          : isSignUp ? 'Set up your account and verify your email to continue.' : 'Sign in with your email to continue to your workspace.';

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
              <h2>{heading}</h2>
              <p>{description}</p>
            </div>

            {isCredentials && (
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
            )}

            {phase === 'recovery-codes' && pendingSession ? (
              <div className="totp-recovery-panel">
                <p className="totp-recovery-warning">Each code works once. Save them now; they won’t be shown again.</p>
                <div className="totp-recovery-codes" aria-label="One-time recovery codes">
                  {pendingSession.recovery_codes.map((code) => <code key={code}>{code}</code>)}
                </div>
                <button type="button" className="forgot-link totp-resend" onClick={copyRecoveryCodes}>Copy recovery codes</button>
                {message && <p className="auth-feedback auth-success" role="status">{message}</p>}
                {error && <p className="auth-feedback auth-error" role="alert">{error}</p>}
                <button type="button" className="login-submit" onClick={saveRecoveryCodesAndContinue} disabled={busy}>
                  <span>{busy ? 'Please wait…' : 'I’ve saved my recovery codes'}</span>
                  {!busy && <ArrowRight size={17} aria-hidden="true" />}
                </button>
              </div>
            ) : (
              <form id="account-form" className="login-form" onSubmit={submit}>
                {phase === 'credentials' && isSignUp && (
                  <label className="login-field" htmlFor="signup-username">
                    <span>Your name</span>
                    <span className="login-input-wrap">
                      <UserRound size={17} aria-hidden="true" />
                      <input id="signup-username" required minLength={3} maxLength={100} value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" placeholder="For example, Alex Morgan" />
                    </span>
                  </label>
                )}

                {phase === 'credentials' && (
                  <label className="login-field" htmlFor="account-email">
                    <span>{isSignUp ? 'Email address' : 'Email address or username'}</span>
                    <span className="login-input-wrap">
                      <Mail size={17} aria-hidden="true" />
                      <input id="account-email" required type={isSignUp ? 'email' : 'text'} maxLength={254} value={email} onChange={(event) => setEmail(event.target.value)} autoComplete={isSignUp ? 'email' : 'username'} placeholder={isSignUp ? 'you@example.com' : 'you@example.com or username'} />
                    </span>
                  </label>
                )}

                {phase === 'credentials' && (
                  <label className="login-field" htmlFor="account-password">
                    <span>Password</span>
                    <span className="login-input-wrap">
                      <LockKeyhole size={17} aria-hidden="true" />
                      <input id="account-password" required minLength={6} maxLength={72} type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={isSignUp ? 'new-password' : 'current-password'} placeholder={isSignUp ? 'Create a password' : 'Enter your password'} />
                      <button className="password-visibility" type="button" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? 'Hide password' : 'Show password'}>
                        {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                      </button>
                    </span>
                  </label>
                )}

                {phase === 'credentials' && isSignUp && (
                  <label className="login-field" htmlFor="account-password-confirm">
                    <span>Confirm password</span>
                    <span className="login-input-wrap">
                      <LockKeyhole size={17} aria-hidden="true" />
                      <input id="account-password-confirm" required minLength={6} maxLength={72} type={showPassword ? 'text' : 'password'} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} autoComplete="new-password" placeholder="Enter it again" />
                    </span>
                  </label>
                )}

                {phase === 'verify-email' && (
                  <label className="login-field" htmlFor="email-verification-code">
                    <span>Email verification code</span>
                    <span className="login-input-wrap">
                      <Mail size={17} aria-hidden="true" />
                      <input id="email-verification-code" required inputMode="numeric" pattern="[0-9]{6}" maxLength={6} autoComplete="one-time-code" value={emailCode} onChange={(event) => setEmailCode(event.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="Six-digit code" />
                    </span>
                  </label>
                )}

                {(phase === 'verify-totp' || phase === 'setup-totp') && (
                  <>
                    {phase === 'setup-totp' && setup && (
                      <div className="totp-setup-panel">
                        <img src={setup.qr_code_data_url} alt="QR code to add OS-DBX to an authenticator app" />
                        <p>Can’t scan it? Enter this setup key in Google Authenticator:</p>
                        <code>{setup.secret}</code>
                      </div>
                    )}
                    <label className="login-field" htmlFor="authenticator-code">
                      <span>{phase === 'setup-totp' ? 'Authenticator code' : 'Authenticator or recovery code'}</span>
                      <span className="login-input-wrap">
                        <KeyRound size={17} aria-hidden="true" />
                        <input id="authenticator-code" required minLength={6} maxLength={32} autoComplete="one-time-code" value={authenticatorCode} onChange={(event) => setAuthenticatorCode(event.target.value.replace(/\s/g, '').slice(0, 32))} placeholder={phase === 'setup-totp' ? 'Six-digit code' : 'Code from your app'} />
                      </span>
                    </label>
                  </>
                )}

                {phase === 'credentials' && !isSignUp && (
                  <div className="login-form-options">
                    <label className="remember-option"><input type="checkbox" checked={rememberMe} onChange={(event) => setRememberMe(event.target.checked)} /><span>Remember me</span></label>
                    <button type="button" className="forgot-link" onClick={() => setMessage('Password recovery is not set up yet. Please contact your OS-DBX administrator.')}>Forgot password?</button>
                  </div>
                )}

                {error && <p className="auth-feedback auth-error" role="alert">{error}</p>}
                {message && <p className="auth-feedback auth-success" role="status">{message}</p>}

                <button type="submit" className="login-submit" disabled={busy}>
                  <span>{busy ? 'Please wait…' : phase === 'verify-email' ? 'Verify email and create account' : phase === 'verify-totp' ? 'Verify and sign in' : phase === 'setup-totp' ? 'Enable two-step verification' : isSignUp ? 'Continue with email verification' : 'Sign in'}</span>
                  {!busy && <ArrowRight size={17} aria-hidden="true" />}
                </button>
                {phase === 'verify-email' && (
                  <div className="totp-action-links">
                    <button type="button" className="forgot-link" onClick={() => { setPhase('credentials'); setMessage(''); setError(''); }}>Change email or details</button>
                    <button type="button" className="forgot-link" onClick={resendEmailCode} disabled={busy}>Send a new code</button>
                  </div>
                )}
                {(phase === 'verify-totp' || phase === 'setup-totp') && (
                  <div className="totp-action-links">
                    <button type="button" className="forgot-link" onClick={() => { setPhase('credentials'); setChallengeToken(''); setAuthenticatorCode(''); setMessage(''); setError(''); }}>Sign in with a different account</button>
                  </div>
                )}
              </form>
            )}

            <p className="login-security-note"><LockKeyhole size={14} /> Your credentials are sent to the configured OS-DBX API.</p>
            <p className="login-email-note">{isCredentials && isSignUp ? 'Email verification is required before an account is created.' : phase === 'setup-totp' ? 'Use Google Authenticator or another compatible authenticator app.' : 'Authenticator codes are verified by the OS-DBX API.'}</p>
          </div>

          <footer className="login-form-footer">OS-DBX · Cross-layer observability workspace</footer>
        </section>
      </section>
    </main>
  );
}
