import logging
import smtplib
from email.message import EmailMessage

from .config import get_settings

log = logging.getLogger("fth.mail")


def send_mail(subject: str, body: str, reply_to: str | None = None) -> None:
    s = get_settings()
    msg = EmailMessage()
    # EmailMessage rejects CR/LF in header values, which blocks header injection.
    msg["Subject"] = subject
    msg["From"] = s.mail_from
    msg["To"] = s.contact_to
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)

    if s.email_backend == "console":
        log.warning("EMAIL (console backend, not sent)\n%s", msg)
        return
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(s.smtp_user, s.smtp_password)
        smtp.send_message(msg)
