import random
import os
import json
import time
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)


def get_base_url():
    """Get base URL dynamically based on environment and settings"""
    if settings.DEBUG:
        return 'http://localhost:8000'
    else:
        # Get from RENDER_EXTERNAL_HOSTNAME environment variable
        render_hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME')
        if render_hostname:
            return f'https://{render_hostname}'

        # Fallback to your main Render URL
        return 'https://csit327-g7-gathered.onrender.com'


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
            # Simple student email - use direct HTML instead of template
            html_content = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; background: linear-gradient(135deg, #00A9FF 0%, #2F93FF 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                    <h1 style="margin: 0;">🎓 Welcome to GatherEd!</h1>
                </div>

                <div style="padding: 20px; background: #f8fafc; border-radius: 0 0 10px 10px;">
                    <p>Hello <strong>{profile.name}</strong>,</p>

                    <p>Welcome to GatherEd! Here's your verification code:</p>

                    <div style="font-size: 48px; font-weight: bold; text-align: center; color: #1e40af; 
                              background: white; padding: 20px; margin: 20px 0; border-radius: 10px; 
                              border: 2px solid #3b82f6;">
                        {otp}
                    </div>

                    <p><strong style="color: #dc2626;">⚠️ This code expires in 60 seconds!</strong></p>

                    <p>Enter this code on the verification page to complete your registration.</p>

                    <p>Best regards,<br>
                    <strong>The GatherEd Team</strong><br>
                    "Empowering educators, one connection at a time"</p>
                </div>
            </body>
            </html>
            '''

            plain_text = f'''
            Welcome to GatherEd!

            Hello {profile.name},

            Your verification code is: {otp}

            This code will expire in 60 seconds for security reasons.

            Enter this code on the verification page to complete your registration.

            Best regards,
            The GatherEd Team
            "Empowering educators, one connection at a time"
            '''

            subject = '🎓 Your GatherEd Student Verification Code'
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

                    <p><strong style="color: #dc2626;">⚠️ This code expires in 60 seconds!</strong></p>

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

            This code will expire in 60 seconds for security reasons.

            Best regards,
            The GatherEd Team
            "Empowering educators, one connection at a time"
            '''

            subject = '🔐 Your GatherEd Verification Code - Valid for 60 seconds!'

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


def send_access_code_request_notification(request_data, request_id):
    """Send notification email to admin about new access code request with FORM-BASED ACTIONS"""
    try:
        SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

        if not SENDGRID_API_KEY:
            print("ERROR: SendGrid API key not found!")
            return False

        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        # Generate URLs for the one-click actions
        # Use base_url from request_data or fallback to dynamic base URL
        if 'base_url' in request_data:
            base_url = request_data['base_url']
        else:
            base_url = get_base_url()

        # IMPORTANT: Use /auth/ prefix as per your main urls.py
        approve_url = f"{base_url}/auth/one-click-action/{request_id}/approve/"
        decline_url = f"{base_url}/auth/one-click-action/{request_id}/decline/"

        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                .action-button {{
                    display: inline-block;
                    padding: 12px 24px;
                    margin: 10px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    cursor: pointer;
                    border: none;
                    font-size: 16px;
                }}
                .approve-btn {{
                    background: linear-gradient(135deg, #10B981 0%, #059669 100%);
                    color: white;
                }}
                .decline-btn {{
                    background: linear-gradient(135deg, #DC2626 0%, #B91C1C 100%);
                    color: white;
                }}
            </style>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; background: linear-gradient(135deg, #00A9FF 0%, #2F93FF 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0;">🔐 New Access Code Request</h1>
            </div>

            <div style="padding: 20px; background: #f8fafc; border-radius: 0 0 10px 10px;">
                <p>A new access code request requires your immediate attention:</p>

                <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0; border: 2px solid #e2e8f0;">
                    <p><strong>👤 Requester Name:</strong> {request_data['name']}</p>
                    <p><strong>📧 Email:</strong> {request_data['email']}</p>
                    <p><strong>🏢 Organization:</strong> {request_data['organization_name']}</p>
                    <p><strong>📝 Message:</strong><br>{request_data['message'] or 'No additional message provided.'}</p>
                    <p><strong>⏰ Requested:</strong> {timezone.now().strftime('%Y-%m-%d %H:%M')}</p>
                    <p><strong>🔑 Request ID:</strong> {request_id}</p>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <h3 style="color: #2F93FF; margin-bottom: 20px;">ONE-CLICK ACTION:</h3>

                    <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; margin-bottom: 30px;">
                        <!-- APPROVE BUTTON -->
                        <a href="{approve_url}" class="action-button approve-btn" 
                           onclick="return confirm('Are you sure you want to APPROVE this request? An access code will be sent to {request_data["email"]}.');">
                            ✅ ONE-CLICK APPROVE
                        </a>

                        <!-- DECLINE BUTTON -->
                        <a href="{decline_url}" class="action-button decline-btn">
                            ❌ ONE-CLICK DECLINE
                        </a>
                    </div>

                    <p style="color: #666; font-size: 0.9rem; margin-top: 15px;">
                        <strong>APPROVE:</strong> One click → Generates code → Sends to requester<br>
                        <strong>DECLINE:</strong> One click → Enter reason → Submit → Sends rejection
                    </p>
                </div>

                <div style="background: #FFFBEB; border-left: 4px solid #F59E0B; padding: 15px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                    <p><strong>⚠️ How it works:</strong></p>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li><strong>APPROVE:</strong> Click green button → Confirm → Access code generated and emailed</li>
                        <li><strong>DECLINE:</strong> Click red button → Enter reason → Submit → Rejection email sent</li>
                        <li>You'll be taken to a confirmation page</li>
                        <li>The system handles everything automatically</li>
                    </ul>
                </div>

                <div style="border-top: 2px dashed #e2e8f0; margin: 30px 0; padding-top: 20px;">
                    <h4 style="color: #2F93FF;">Quick Notes:</h4>
                    <p style="margin: 5px 0;">✅ Approve if: Organization doesn't have existing admin & requester is legitimate</p>
                    <p style="margin: 5px 0;">❌ Decline if: Organization already has admin or requester is not authorized</p>
                    <p style="margin: 5px 0;">⏰ Please respond within 48 hours</p>
                </div>

                <p style="color: #666; font-size: 0.9rem; text-align: center; margin-top: 30px;">
                    This is an automated notification from GatherEd Access Control System.
                </p>

                <p>Best regards,<br>
                <strong>The GatherEd Team</strong><br>
                "Empowering educators, one connection at a time"</p>
            </div>
        </body>
        </html>
        '''

        plain_text = f'''
        NEW ACCESS CODE REQUEST - REQUIRES IMMEDIATE ACTION

        A new access code request has been submitted:

        Requester Name: {request_data['name']}
        Email: {request_data['email']}
        Organization: {request_data['organization_name']}
        Message: {request_data['message'] or 'No additional message provided.'}
        Requested: {timezone.now().strftime('%Y-%m-%d %H:%M')}
        Request ID: {request_id}

        TO APPROVE:
        Click this link: {approve_url}

        TO DECLINE:
        Click this link: {decline_url}

        How it works:
        - APPROVE: Click link → Confirm → Access code generated and emailed to requester
        - DECLINE: Click link → Enter reason → Submit → Rejection email sent to requester

        Quick Notes:
        - Approve if: Organization doesn't have existing admin & requester is legitimate
        - Decline if: Organization already has admin or requester is not authorized
        - Please respond within 48 hours

        This is an automated notification from GatherEd Access Control System.

        Best regards,
        The GatherEd Team
        "Empowering educators, one connection at a time"
        '''

        # Create email
        message = Mail(
            from_email='GatherEd Access Control <jasminecielyp@gmail.com>',
            to_emails='jasminecielyp@gmail.com',
            subject=f'🔐 ACTION REQUIRED: Access Code Request from {request_data["name"]}',
            html_content=html_content,
            plain_text_content=plain_text
        )

        # Send email
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        if response.status_code in [200, 202]:
            print(f"✅ Access code request notification sent to admin")
            return True
        else:
            print(f"❌ SendGrid API error for request notification: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error sending access code request notification: {e}")
        return False


def send_access_code_approval_email(request_data, access_code):
    """Send approval email with access code to requester"""
    try:
        SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

        if not SENDGRID_API_KEY:
            print("ERROR: SendGrid API key not found!")
            return False

        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        # Get base URL for dynamic links
        base_url = get_base_url()

        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; background: linear-gradient(135deg, #00A9FF 0%, #2F93FF 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0;">✅ Access Code Request Approved</h1>
            </div>

            <div style="padding: 20px; background: #f8fafc; border-radius: 0 0 10px 10px;">
                <p>Hello <strong>{request_data['name']}</strong>,</p>

                <p>Your request for an access code has been <strong style="color: #10B981;">approved</strong>!</p>

                <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0; border: 2px solid #e2e8f0;">
                    <p><strong>🏢 Organization:</strong> {request_data['organization_name']}</p>
                    <p><strong>📅 Approved:</strong> {timezone.now().strftime('%Y-%m-%d %H:%M')}</p>
                </div>

                <p>Here is your access code:</p>

                <div style="font-size: 48px; font-weight: bold; text-align: center; color: #1e40af; 
                          background: white; padding: 20px; margin: 20px 0; border-radius: 10px; 
                          border: 2px solid #3b82f6; letter-spacing: 10px;">
                    {access_code}
                </div>

                <div style="background: #FFFBEB; border-left: 4px solid #F59E0B; padding: 15px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                    <p><strong>⚠️ Important Instructions:</strong></p>
                    <ol style="margin: 10px 0; padding-left: 20px;">
                        <li>Go to: <a href="{base_url}/register/organizer-access/">Organizer Registration Access</a></li>
                        <li>Enter the access code above</li>
                        <li>Complete the organizer registration form</li>
                        <li>Verify your email with the OTP sent to you</li>
                    </ol>
                </div>

                <p><strong style="color: #DC2626;">⏰ This code will expire in 7 days!</strong></p>

                <div style="border-top: 2px dashed #e2e8f0; margin: 30px 0; padding-top: 20px;">
                    <h3 style="color: #2F93FF;">Need Help?</h3>
                    <p>If you encounter any issues, please reply to this email or contact our support team.</p>
                </div>

                <p>Best regards,<br>
                <strong>The GatherEd Team</strong><br>
                "Empowering educators, one connection at a time"</p>
            </div>
        </body>
        </html>
        '''

        plain_text = f'''
        ACCESS CODE REQUEST APPROVED

        Hello {request_data['name']},

        Your request for an access code has been approved!

        Organization: {request_data['organization_name']}
        Approved: {timezone.now().strftime('%Y-%m-%d %H:%M')}

        Here is your access code:

        {access_code}

        Important Instructions:
        1. Go to: {base_url}/register/organizer-access/
        2. Enter the access code above
        3. Complete the organizer registration form
        4. Verify your email with the OTP sent to you

        ⚠️ This code will expire in 7 days!

        Need Help?
        If you encounter any issues, please reply to this email or contact our support team.

        Best regards,
        The GatherEd Team
        "Empowering educators, one connection at a time"
        '''

        # Create email
        message = Mail(
            from_email='GatherEd Access Control <jasminecielyp@gmail.com>',
            to_emails=request_data['email'],
            subject=f'✅ Your GatherEd Access Code for {request_data["organization_name"]}',
            html_content=html_content,
            plain_text_content=plain_text
        )

        # Send email
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        if response.status_code in [200, 202]:
            print(f"✅ Access code approval email sent to {request_data['email']}")
            return True
        else:
            print(f"❌ SendGrid API error for approval email: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error sending approval email: {e}")
        return False


def send_access_code_declined_email(request_data, decline_reason):
    """Send declined email to requester"""
    try:
        SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

        if not SENDGRID_API_KEY:
            print("ERROR: SendGrid API key not found!")
            return False

        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        # Get base URL for dynamic links
        base_url = get_base_url()

        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; background: linear-gradient(135deg, #DC2626 0%, #B91C1C 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0;">❌ Access Code Request Declined</h1>
            </div>

            <div style="padding: 20px; background: #f8fafc; border-radius: 0 0 10px 10px;">
                <p>Hello <strong>{request_data['name']}</strong>,</p>

                <p>We regret to inform you that your request for an access code has been <strong style="color: #DC2626;">declined</strong>.</p>

                <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0; border: 2px solid #e2e8f0;">
                    <p><strong>🏢 Organization:</strong> {request_data['organization_name']}</p>
                    <p><strong>📅 Declined:</strong> {timezone.now().strftime('%Y-%m-%d %H:%M')}</p>
                </div>

                <div style="background: #FEF2F2; border-left: 4px solid #DC2626; padding: 15px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                    <p><strong>📝 Reason for Decline:</strong></p>
                    <p>{decline_reason}</p>
                </div>

                <div style="border-top: 2px dashed #e2e8f0; margin: 30px 0; padding-top: 20px;">
                    <h3 style="color: #2F93FF;">Next Steps:</h3>
                    <p>If you believe this was a mistake or would like to appeal the decision:</p>
                    <ol style="margin: 10px 0; padding-left: 20px;">
                        <li>Reply to this email with additional information</li>
                        <li>Ensure your organization doesn't already have a verified administrator</li>
                        <li>Provide proof of your role in the organization</li>
                    </ol>
                </div>

                <div style="border-top: 2px dashed #e2e8f0; margin: 30px 0; padding-top: 20px;">
                    <h3 style="color: #2F93FF;">Alternative Options:</h3>
                    <p>You can still participate in GatherEd as a student:</p>
                    <div style="text-align: center; margin: 20px 0;">
                        <a href="{base_url}/register/student/" style="display: inline-block; background: #00A9FF; color: white; padding: 12px 30px; text-decoration: none; border-radius: 50px; font-weight: bold; border: none;">
                            👨‍🎓 Register as Student
                        </a>
                    </div>
                </div>

                <p>Best regards,<br>
                <strong>The GatherEd Team</strong><br>
                "Empowering educators, one connection at a time"</p>
            </div>
        </body>
        </html>
        '''

        plain_text = f'''
        ACCESS CODE REQUEST DECLINED

        Hello {request_data['name']},

        We regret to inform you that your request for an access code has been declined.

        Organization: {request_data['organization_name']}
        Declined: {timezone.now().strftime('%Y-%m-%d %H:%M')}

        Reason for Decline:
        {decline_reason}

        Next Steps:
        If you believe this was a mistake or would like to appeal the decision:
        1. Reply to this email with additional information
        2. Ensure your organization doesn't already have a verified administrator
        3. Provide proof of your role in the organization

        Alternative Options:
        You can still participate in GatherEd as a student.
        Register at: {base_url}/register/student/

        Best regards,
        The GatherEd Team
        "Empowering educators, one connection at a time"
        '''

        # Create email
        message = Mail(
            from_email='GatherEd Access Control <jasminecielyp@gmail.com>',
            to_emails=request_data['email'],
            subject=f'❌ Update on Your GatherEd Access Code Request for {request_data["organization_name"]}',
            html_content=html_content,
            plain_text_content=plain_text
        )

        # Send email
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        if response.status_code in [200, 202]:
            print(f"✅ Access code declined email sent to {request_data['email']}")
            return True
        else:
            print(f"❌ SendGrid API error for declined email: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error sending declined email: {e}")
        return False