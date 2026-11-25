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


def _send_email(to_email: str, subject: str, text_body: str, html_body: str) -> tuple[bool, str]:
    """Send an email via SMTP (trying SSL port 465, then STARTTLS port 587) and return (success, error_detail)."""
    if not to_email or "@" not in to_email:
        return False, "Recipient email address is invalid."
    if not is_smtp_configured():
        return False, f"SMTP configuration missing on server (host={settings.smtp_host!r}, user={settings.smtp_username!r}, has_password={bool(settings.smtp_password)})."

    from_addr = settings.smtp_from_email or settings.smtp_username
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"OS-DBX Security <{from_addr}>"
    msg["To"] = to_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    errors = []

    # Attempt 1: Port 465 with direct SSL (often preferred on cloud hosts)
    try:
        with smtplib.SMTP_SSL(settings.smtp_host, 465, timeout=10) as server:
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
        return True, ""
    except Exception as exc1:
        errors.append(f"Port 465 (SSL): {exc1}")

    # Attempt 2: Port 587 with STARTTLS
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port or 587, timeout=10) as server:
            server.ehlo()
            if settings.smtp_use_tls:
                server.starttls()
                server.ehlo()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
        return True, ""
    except Exception as exc2:
        errors.append(f"Port 587 (TLS): {exc2}")

    err_summary = " | ".join(errors)
    import logging
    logging.getLogger("os_dbx.email").error(f"Failed to deliver email to {to_email}: {err_summary}")
    return False, err_summary


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
    return _send_email(to_email, subject, text_body, html_body)[0]


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
    return _send_email(to_email, subject, text_body, html_body)[0]


def send_email_verification_code(to_email: Optional[str], username: str, code: str) -> tuple[bool, str]:
    """Send an email verification code."""
    if not to_email:
        return False, "No recipient email address associated with account."
    subject = f"OS-DBX Verification Code: {code}"
    text_body = (
        f"Hello {username},\n\n"
        f"Your verification code to complete your OS-DBX account registration is: {code}\n\n"
        "This code will expire in 15 minutes.\n"
        "If you did not request this, please contact your administrator.\n\n"
        "— OS-DBX Security"
    )
    html_body = f"""
    <div style="font-family: system-ui, -apple-system, sans-serif; max-width: 540px; margin: 0 auto; padding: 24px; border: 1px solid #e5e7eb; border-radius: 12px;">
      <h2 style="color: #1f2937; margin-top: 0;">Complete Your Registration</h2>
      <p style="color: #4b5563; line-height: 1.6;">
        Hello <strong>{username}</strong>, enter the code below in your account panel to verify your email address and complete registration:
      </p>
      <div style="background: #f0fdf4; border: 1px solid #bbf7d0; padding: 16px; border-radius: 8px; margin: 20px 0; text-align: center;">
        <span style="font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #166534;">{code}</span>
      </div>
      <p style="color: #6b7280; font-size: 13px;">
        This code expires in 15 minutes.
      </p>
    </div>
    """
    return _send_email(to_email, subject, text_body, html_body)
