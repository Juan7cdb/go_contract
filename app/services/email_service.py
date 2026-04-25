import logging
import resend
from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_reset_email(to_email: str, token: str) -> None:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    resend.api_key = settings.RESEND_API_KEY

    params: resend.Emails.SendParams = {
        "from": settings.FROM_EMAIL,
        "to": [to_email],
        "subject": "Reset your GoContract password",
        "html": f"""
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
        """,
    }

    try:
        resend.Emails.send(params)
        logger.info(f"Password reset email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send reset email to {to_email}: {e}")
        raise
