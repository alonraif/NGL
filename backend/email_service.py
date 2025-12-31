"""
Email delivery utilities (SMTP).
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from config import Config
from database import SessionLocal
from models import SMTPConfiguration


def _get_smtp_settings(require_enabled=True):
    db = None
    try:
        db = SessionLocal()
        smtp_config = db.query(SMTPConfiguration).first()
        if smtp_config and (smtp_config.is_enabled or not require_enabled):
            return {
                'host': smtp_config.host,
                'port': smtp_config.port or 587,
                'user': smtp_config.username,
                'password': smtp_config.password,
                'from_email': smtp_config.from_email or Config.SMTP_FROM,
                'use_tls': smtp_config.use_tls
            }
    except Exception:
        logging.exception('Failed to load SMTP config from database')
    finally:
        if db:
            db.close()

    return {
        'host': Config.SMTP_HOST,
        'port': Config.SMTP_PORT,
        'user': Config.SMTP_USER,
        'password': Config.SMTP_PASS,
        'from_email': Config.SMTP_FROM,
        'use_tls': Config.SMTP_USE_TLS
    }


def send_invite_email(to_email, invite_link, inviter_username=None, expires_hours=48):
    smtp_settings = _get_smtp_settings()
    if not smtp_settings.get('host'):
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
    message['From'] = smtp_settings['from_email']
    message['To'] = to_email
    message.set_content(body)

    context = ssl.create_default_context()
    server = smtplib.SMTP(smtp_settings['host'], smtp_settings['port'], timeout=10)
    try:
        if smtp_settings['use_tls']:
            server.starttls(context=context)
        if smtp_settings['user']:
            server.login(smtp_settings['user'], smtp_settings['password'] or '')
        server.send_message(message)
    finally:
        server.quit()

    return True, None


def send_test_email(to_email):
    smtp_settings = _get_smtp_settings(require_enabled=False)
    if not smtp_settings.get('host'):
        logging.info('SMTP not configured; skipping test email to %s', to_email)
        return False, 'SMTP not configured'

    subject = 'NGL SMTP test'
    body = (
        'This is a test email from NGL.\n'
        'If you received this message, SMTP settings are working.\n'
    )

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = smtp_settings['from_email']
    message['To'] = to_email
    message.set_content(body)

    context = ssl.create_default_context()
    server = smtplib.SMTP(smtp_settings['host'], smtp_settings['port'], timeout=10)
    try:
        if smtp_settings['use_tls']:
            server.starttls(context=context)
        if smtp_settings['user']:
            server.login(smtp_settings['user'], smtp_settings['password'] or '')
        server.send_message(message)
    finally:
        server.quit()

    return True, None
