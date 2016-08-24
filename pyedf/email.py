from django.core.mail import EmailMultiAlternatives
from columbus.settings import ADMINS, EMAIL_SENDER
from pyedf.utils import log_n_suppress


def send_mail(receivers, subject=None, message=None, html=None):
    """
    Sends an email to the recipients
    :param receivers: list of recipient email addresses
    :param subject: subject of the email
    :param message: plain text message
    :param html: HTML message
    """
    if not isinstance(receivers, list):
        raise ValueError('Invalid recipients. Must be a list of email addresses.')
    try:
        sender = EMAIL_SENDER
        subject = 'No Subject Specified' if subject is None else subject
        admin = None
        headers = None
        if isinstance(ADMINS, list) and len(ADMINS) > 0 and isinstance(ADMINS[0], tuple) and len(ADMINS[0]) > 0:
            admin = str(ADMINS[0][0]) + '<' + str(ADMINS[0][1]) + '>'
        if message is None and html is None:
            message = 'The sender of this message did not include any details. '
            if admin:
                message += 'If you are not the intended recipient of this message or keep getting these emails, ' \
                           'please send an email to ' + admin
                headers = {"Reply-To": admin}

        mail = EmailMultiAlternatives(subject=subject, body=message, from_email=sender, to=receivers, headers=headers)
        if html:
            mail.attach_alternative(html, "text/html")
        mail.send()
    except Exception as e:
        log_n_suppress(e)
