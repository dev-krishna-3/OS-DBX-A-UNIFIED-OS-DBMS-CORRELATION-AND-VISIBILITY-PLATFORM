"""SMTP email notification service for OS-DBX authentication events."""

from datetime import datetime, timezone
from email.message import EmailMessage
import smtplib
from typing import Optional

from app.config.settings import settings


def is_smtp_configured() -> bool:
    """Return True when all required SMTP credentials are set."""
    return bool(
        settings.smtp_host
        and settings.smtp_port
        and settings.smtp_username
        and settings.smtp_password
    )


def _send_email(to_email: str, subject: str, text_body: str, html_body: str) -> bool:
    """Send an email via SMTP and return True if delivered, False otherwise."""
    if not to_email or "@" not in to_email or not is_smtp_configured():
        return False

    from_addr = settings.smtp_from_email or settings.smtp_username
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"OS-DBX Security <{from_addr}>"
    msg["To"] = to_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5) as server:
            server.ehlo()
            if settings.smtp_use_tls:
                server.starttls()
                server.ehlo()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
        return True
    except Exception:
        return False


def send_signup_notification(to_email: Optional[str], username: str) -> bool:
    """Send a welcome and security confirmation email when a user registers."""
    if not to_email:
        return False
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = "Welcome to OS-DBX — Account Created"
    text_body = (
        f"Hello {username},\n\n"
        f"Your OS-DBX Cross-Layer Observability account was created at {ts}.\n"
        f"Registered email: {to_email}\n\n"
        "You can now sign in to explore OS events, DBMS observations, cross-layer traces, "
        "deadlock forensics, and simulation labs.\n\n"
        "— OS-DBX Platform"
    )
    html_body = f"""
    <div style="font-family: system-ui, -apple-system, sans-serif; max-width: 540px; margin: 0 auto; padding: 24px; border: 1px solid #e5e7eb; border-radius: 12px;">
      <h2 style="color: #1f2937; margin-top: 0;">Welcome to OS-DBX, {username}</h2>
      <p style="color: #4b5563; line-height: 1.6;">
        Your account on the <strong>OS-DBX Cross-Layer Observability Platform</strong> has been created.
      </p>
      <div style="background: #f9fafb; padding: 12px 16px; border-radius: 8px; margin: 16px 0; font-size: 14px; color: #374151;">
        <div><strong>Username:</strong> {username}</div>
        <div><strong>Email:</strong> {to_email}</div>
        <div><strong>Time:</strong> {ts}</div>
      </div>
      <p style="color: #6b7280; font-size: 13px; margin-bottom: 0;">
        If you did not create this account, please contact your OS-DBX administrator.
      </p>
    </div>
    """
    return _send_email(to_email, subject, text_body, html_body)


def send_signin_notification(to_email: Optional[str], username: str) -> bool:
    """Send a security alert email when a user signs in."""
    if not to_email:
        return False
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = "OS-DBX Security Alert — New Sign-In"
    text_body = (
        f"Hello {username},\n\n"
        f"A new sign-in to your OS-DBX workspace was recorded at {ts}.\n"
        f"Account: {username} ({to_email})\n\n"
        "If this was you, no further action is needed.\n\n"
        "— OS-DBX Security"
    )
    html_body = f"""
    <div style="font-family: system-ui, -apple-system, sans-serif; max-width: 540px; margin: 0 auto; padding: 24px; border: 1px solid #e5e7eb; border-radius: 12px;">
      <h2 style="color: #1f2937; margin-top: 0;">New Sign-In Detected</h2>
      <p style="color: #4b5563; line-height: 1.6;">
        Hello <strong>{username}</strong>, a new sign-in to your <strong>OS-DBX</strong> workspace was recorded.
      </p>
      <div style="background: #f9fafb; padding: 12px 16px; border-radius: 8px; margin: 16px 0; font-size: 14px; color: #374151;">
        <div><strong>Account:</strong> {username}</div>
        <div><strong>Email:</strong> {to_email}</div>
        <div><strong>Time:</strong> {ts}</div>
      </div>
      <p style="color: #6b7280; font-size: 13px; margin-bottom: 0;">
        If this was you, you can safely ignore this alert.
      </p>
    </div>
    """
    return _send_email(to_email, subject, text_body, html_body)
