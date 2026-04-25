import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import resend
from app.core.config import settings

logger = logging.getLogger(__name__)

_RESET_HTML = """
<html>
  <body style="font-family: Arial, sans-serif; color: #1A1A1A; max-width: 600px; margin: 0 auto;">
    <div style="padding: 40px 20px;">
      <h2 style="color: #2563EB;">GoContract — Reset your password</h2>
      <p>We received a request to reset your password. Click the button below to create a new one.</p>
      <p>This link expires in <strong>1 hour</strong>.</p>
      <div style="margin: 32px 0;">
        <a href="{reset_url}"
           style="background-color:#2563EB;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;">
          Reset Password
        </a>
      </div>
      <p style="color:#64748B;font-size:13px;">
        If you didn't request this, you can safely ignore this email.
      </p>
    </div>
  </body>
</html>
"""


def _send_via_gmail(to_email: str, reset_url: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your GoContract password"
    msg["From"] = settings.GMAIL_USER
    msg["To"] = to_email
    msg.attach(MIMEText(_RESET_HTML.format(reset_url=reset_url), "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
        server.sendmail(settings.GMAIL_USER, to_email, msg.as_string())


def _send_via_resend(to_email: str, reset_url: str) -> None:
    resend.api_key = settings.RESEND_API_KEY
    params: resend.Emails.SendParams = {
        "from": settings.FROM_EMAIL,
        "to": [to_email],
        "subject": "Reset your GoContract password",
        "html": _RESET_HTML.format(reset_url=reset_url),
    }
    resend.Emails.send(params)


async def send_reset_email(to_email: str, token: str) -> None:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    if settings.GMAIL_USER and settings.GMAIL_APP_PASSWORD:
        logger.info(f"Sending reset email via Gmail to {to_email}")
        _send_via_gmail(to_email, reset_url)
    elif settings.RESEND_API_KEY:
        logger.info(f"Sending reset email via Resend to {to_email}")
        _send_via_resend(to_email, reset_url)
    else:
        raise RuntimeError("No email provider configured. Set GMAIL_USER + GMAIL_APP_PASSWORD or RESEND_API_KEY.")
