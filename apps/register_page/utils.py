from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def send_otp_email(admin_profile, request):
    """Send OTP verification email to admin"""
    try:
        otp_code = admin_profile.generate_otp()

        subject = 'Your GatherEd Organizer Verification Code'

        html_message = render_to_string('email/admin_otp_verification.html', {
            'admin_name': admin_profile.name,
            'organization_name': admin_profile.organization_name,
            'otp_code': otp_code,
        })

        plain_message = strip_tags(html_message)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_profile.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email: {str(e)}")
        return False