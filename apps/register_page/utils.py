import random
import os
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string


def send_otp_email(profile, request, is_student=False):
    """Generate and send OTP email using SendGrid API"""
    try:
        # Get user email
        user_email = profile.user.email

        # ===================== DOMAIN CHECK =====================
        ALLOWED_DOMAIN = '@cit.edu'
        if not user_email.endswith(ALLOWED_DOMAIN):
            print(f"❌ REJECTED: Email {user_email} is not from {ALLOWED_DOMAIN}")
            return False
        # ========================================================

        print(f"✅ Domain check passed: {user_email}")

        # Generate OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        profile.otp_code = otp
        profile.otp_created_at = timezone.now()
        profile.save()

        # Get SendGrid API key
        SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

        # In development (DEBUG=True), just print to console
        if settings.DEBUG:
            print("\n" + "=" * 60)
            print(f"📧 DEVELOPMENT MODE - Email would be sent to: {user_email}")
            print(f"📧 OTP CODE: {otp}")
            print("=" * 60 + "\n")
            return True

        # In production, use SendGrid API
        if not SENDGRID_API_KEY:
            print("ERROR: SendGrid API key not found!")
            return False

        # Import SendGrid
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        # Prepare email content based on user type
        if is_student:
            # Render student-specific email template
            context = {
                'student_name': profile.name,
                'otp_code': otp
            }
            html_content = render_to_string('email/student_otp_verification.html', context)
            
            plain_text = f'''
            Welcome to GatherEd!
            
            Hello {profile.name},
            
            Your verification code is: {otp}
            
            This code will expire in 10 minutes for security reasons.
            
            Best regards,
            The GatherEd Team
            "Empowering educators, one connection at a time"
            '''
            
            subject = '🎓 Your GatherEd Student Verification Code - Valid for 10 Minutes!'
        else:
            # Admin email content (existing)
            html_content = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; background: #667eea; color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                    <h1 style="margin: 0;">🎓 GatherEd Verification</h1>
                </div>

                <div style="padding: 20px; background: #f8fafc; border-radius: 0 0 10px 10px;">
                    <p>Hello <strong>{profile.name}</strong>,</p>

                    <p>We're excited to have you back! Here's your verification code:</p>

                    <div style="font-size: 48px; font-weight: bold; text-align: center; color: #1e40af; 
                              background: white; padding: 20px; margin: 20px 0; border-radius: 10px; 
                              border: 2px solid #3b82f6;">
                        {otp}
                    </div>

                    <p><strong style="color: #dc2626;">⚠️ This code expires in 10 minutes!</strong></p>

                    <p>Best regards,<br>
                    <strong>The GatherEd Team</strong><br>
                    "Empowering educators, one connection at a time"</p>
                </div>
            </body>
            </html>
            '''

            plain_text = f'''
            Welcome Back to GatherEd!

            Hello {profile.name},

            Your verification code is: {otp}

            This code will expire in 10 minutes for security reasons.

            Best regards,
            The GatherEd Team
            "Empowering educators, one connection at a time"
            '''
            
            subject = '🔐 Your GatherEd Verification Code - Valid for 10 Minutes!'

        # Create email
        message = Mail(
            from_email='GatherEd Security <jasminecielyp@gmail.com>',
            to_emails=user_email,
            subject=subject,
            html_content=html_content,
            plain_text_content=plain_text
        )

        # Send email
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        # Check response
        if response.status_code in [200, 202]:
            print(f"✅ OTP email sent successfully to {user_email}")
            return True
        else:
            print(f"❌ SendGrid API error: {response.status_code}")
            # Still return True so user can continue with OTP (it's saved in database)
            return True

    except Exception as e:
        print(f"❌ Error in send_otp_email: {e}")
        # Return True anyway so registration doesn't fail
        return True


def send_student_otp_email(student_profile, request):
    """Generate and send OTP email for student registration using SendGrid API"""
    return send_otp_email(student_profile, request, is_student=True)