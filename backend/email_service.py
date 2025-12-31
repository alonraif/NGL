"""
Email delivery utilities (SMTP).
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from config import Config


def send_invite_email(to_email, invite_link, inviter_username=None, expires_hours=48):
    if not Config.SMTP_HOST:
        logging.info('SMTP not configured; skipping invite email to %s', to_email)
        return False, 'SMTP not configured'

    subject = 'Your NGL account invite'
    inviter_line = f'Invited by: {inviter_username}\n' if inviter_username else ''
    body = (
        f'You have been invited to NGL.\n'
        f'{inviter_line}'
        f'Invite link (valid for {expires_hours} hours):\n'
        f'{invite_link}\n'
    )

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = Config.SMTP_FROM
    message['To'] = to_email
    message.set_content(body)

    context = ssl.create_default_context()
    server = smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10)
    try:
        if Config.SMTP_USE_TLS:
            server.starttls(context=context)
        if Config.SMTP_USER:
            server.login(Config.SMTP_USER, Config.SMTP_PASS or '')
        server.send_message(message)
    finally:
        server.quit()

    return True, None
