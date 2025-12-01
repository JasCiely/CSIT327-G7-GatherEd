import random
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone


def send_otp_email(admin_profile, request):
    """Generate and send creative OTP email to admin"""
    try:
        # Generate 6-digit OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        # Save OTP to admin profile
        admin_profile.otp_code = otp
        admin_profile.otp_created_at = timezone.now()
        admin_profile.save()

        # Creative email content
        subject = '🔐 Your GatherEd Verification Code - Valid for 30 Seconds!'

        message = f'''
🌟 Welcome Back to GatherEd! 🌟

Hello {admin_profile.name},

Your verification code is:

╔═══════════════════════╗
║         {otp}         ║
╚═══════════════════════╝

This code will expire in 30 seconds for security reasons.

Need help? Reply to this email and our team will assist you.

Best regards,
The GatherEd Team
"Empowering educators, one connection at a time"
        '''

        html_message = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
            position: relative;
        }}

        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" preserveAspectRatio="none"><path d="M0,0 L100,0 L100,100 Z" fill="rgba(255,255,255,0.1)"/></svg>');
            background-size: cover;
        }}

        .header-content {{
            position: relative;
            z-index: 2;
        }}

        .logo {{
            font-size: 42px;
            margin-bottom: 15px;
            display: block;
        }}

        .header h1 {{
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 10px;
            letter-spacing: -0.5px;
        }}

        .header p {{
            font-size: 16px;
            opacity: 0.9;
            font-weight: 400;
        }}

        .content {{
            padding: 40px 30px;
            background: #ffffff;
        }}

        .greeting {{
            font-size: 20px;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 25px;
        }}

        .otp-section {{
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            border-radius: 16px;
            padding: 30px;
            margin: 30px 0;
            border: 2px solid #e2e8f0;
            text-align: center;
        }}

        .otp-label {{
            font-size: 14px;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 15px;
            display: block;
        }}

        .otp-code {{
            font-size: 64px;
            font-weight: 800;
            color: #1e40af;
            letter-spacing: 8px;
            background: white;
            padding: 25px;
            border-radius: 12px;
            border: 3px solid #3b82f6;
            display: inline-block;
            margin: 10px 0;
            box-shadow: 0 8px 20px rgba(59, 130, 246, 0.15);
            font-family: 'Courier New', monospace;
            position: relative;
            overflow: hidden;
        }}

        .otp-code::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.1), transparent);
            animation: shimmer 3s infinite;
        }}

        @keyframes shimmer {{
            0% {{ left: -100%; }}
            100% {{ left: 100%; }}
        }}

        .timer-warning {{
            background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
            color: #dc2626;
            padding: 15px 20px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 16px;
            margin: 20px 0;
            border: 2px solid #fca5a5;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }}

        .timer-warning::before {{
            content: '⏰';
            font-size: 20px;
        }}

        .info-section {{
            margin: 35px 0;
        }}

        .info-title {{
            font-size: 18px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .info-title::before {{
            content: '💫';
            font-size: 20px;
        }}

        .features-grid {{
            display: grid;
            gap: 12px;
            margin: 20px 0;
        }}

        .feature-item {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 12px;
            background: #f8fafc;
            border-radius: 8px;
            border-left: 4px solid #3b82f6;
        }}

        .feature-item::before {{
            content: '✓';
            color: #10b981;
            font-weight: bold;
            font-size: 14px;
            margin-top: 2px;
        }}

        .security-note {{
            background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
            border: 2px solid #f59e0b;
            border-radius: 12px;
            padding: 25px;
            margin: 30px 0;
        }}

        .security-title {{
            font-size: 16px;
            font-weight: 700;
            color: #92400e;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .security-title::before {{
            content: '🛡️';
            font-size: 18px;
        }}

        .footer {{
            text-align: center;
            padding: 30px;
            background: #f8fafc;
            border-top: 1px solid #e2e8f0;
            color: #64748b;
            font-size: 14px;
        }}

        .signature {{
            font-size: 16px;
            font-weight: 600;
            color: #1e293b;
            margin: 15px 0;
        }}

        .tagline {{
            font-style: italic;
            color: #667eea;
            margin: 10px 0;
            font-weight: 500;
        }}

        .ps-note {{
            margin-top: 25px;
            padding-top: 25px;
            border-top: 1px dashed #cbd5e1;
            font-size: 13px;
            color: #94a3b8;
        }}

        @media (max-width: 600px) {{
            .content {{
                padding: 25px 20px;
            }}

            .otp-code {{
                font-size: 48px;
                letter-spacing: 6px;
                padding: 20px;
            }}

            .header {{
                padding: 30px 20px;
            }}

            .header h1 {{
                font-size: 24px;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <div class="header-content">
                <div class="logo">🎓</div>
                <h1>GatherEd Verification</h1>
                <p>Your secure access to educational excellence</p>
            </div>
        </div>

        <div class="content">
            <div class="greeting">
                Hello {admin_profile.name},
            </div>

            <p>We're excited to have you back! Here's your verification code to access your GatherEd organizer account:</p>

            <div class="otp-section">
                <span class="otp-label">Verification Code</span>
                <div class="otp-code">{otp}</div>
                <div class="timer-warning">
                    Expires in 30 seconds - Use it quickly!
                </div>
            </div>

            <div class="info-section">
                <div class="info-title">What This Code Unlocks:</div>
                <div class="features-grid">
                    <div class="feature-item">Open Registration for All CIT-U Events</div>
                    <div class="feature-item">Organized Event Management by Campus Groups</div>
                    <div class="feature-item">Unified University Calendar Access</div>
                    <div class="feature-item">Secure Organizer Dashboard</div>
                </div>
            </div>

            <div class="security-note">
                <div class="security-title">Security Notice</div>
                <p>If you didn't request this verification code, please reply to this email immediately. We'll secure your account and investigate the issue.</p>
            </div>

            <p style="text-align: center; margin-top: 30px;">
                Need immediate assistance?<br>
                <strong>Reply directly to this email</strong> - we're here to help!
            </p>
        </div>

        <div class="footer">
            <div class="signature">The GatherEd Team</div>
            <div class="tagline">"Empowering educators, one connection at a time"</div>
            <div class="ps-note">
                P.S. This secure step ensures your educational communities remain protected while you focus on inspiring minds.
            </div>
        </div>
    </div>
</body>
</html>
        '''

        send_mail(
            subject=subject,
            message=message,
            html_message=html_message,
            from_email="GatherEd Security <" + settings.DEFAULT_FROM_EMAIL + ">",
            recipient_list=[admin_profile.user.email],
            fail_silently=False,
        )

        return True

    except Exception as e:
        print(f"Error sending OTP email: {e}")
        return False