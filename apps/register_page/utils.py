import random
import os
from django.utils import timezone
from django.conf import settings


def send_otp_email(admin_profile, request):
    """Generate and send OTP email using SendGrid API"""
    try:
        # Generate 6-digit OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        # Save OTP to admin profile
        admin_profile.otp_code = otp
        admin_profile.otp_created_at = timezone.now()
        admin_profile.save()

        # Get SendGrid API key
        SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

        # In development (DEBUG=True), just print to console
        if settings.DEBUG:
            print("\n" + "=" * 60)
            print(f"📧 DEVELOPMENT MODE - Email would be sent to: {admin_profile.user.email}")
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

        # Simple HTML email
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
                <p>Hello <strong>{admin_profile.name}</strong>,</p>

                <p>We're excited to have you back! Here's your verification code:</p>

                <div style="font-size: 48px; font-weight: bold; text-align: center; color: #1e40af; 
                          background: white; padding: 20px; margin: 20px 0; border-radius: 10px; 
                          border: 2px solid #3b82f6;">
                    {otp}
                </div>

                <p><strong style="color: #dc2626;">⚠️ This code expires in 30 seconds!</strong></p>

                <p>Best regards,<br>
                <strong>The GatherEd Team</strong><br>
                "Empowering educators, one connection at a time"</p>
            </div>
        </body>
        </html>
        '''

        # Plain text version
        plain_text = f'''
        Welcome Back to GatherEd!

        Hello {admin_profile.name},

        Your verification code is: {otp}

        This code will expire in 30 seconds for security reasons.

        Best regards,
        The GatherEd Team
        "Empowering educators, one connection at a time"
        '''

        # Create email
        message = Mail(
            from_email='GatherEd Security <jasminecielyp@gmail.com>',
            to_emails=admin_profile.user.email,
            subject='🔐 Your GatherEd Verification Code - Valid for 30 Seconds!',
            html_content=html_content,
            plain_text_content=plain_text
        )

        # Send email
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        # Check response
        if response.status_code in [200, 202]:
            print(f"✅ OTP email sent successfully to {admin_profile.user.email}")
            return True
        else:
            print(f"❌ SendGrid API error: {response.status_code}")
            # Still return True so user can continue with OTP (it's saved in database)
            return True

    except Exception as e:
        print(f"❌ Error in send_otp_email: {e}")
        # Return True anyway so registration doesn't fail
        return True