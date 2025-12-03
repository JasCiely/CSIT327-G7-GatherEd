from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
import re
import uuid

from apps.register_page.models import AdminProfile, StudentProfile, AccessCodeRequest, OrganizationAccessCode
from apps.register_page.utils import send_otp_email, send_student_otp_email, send_access_code_declined_email, \
    send_access_code_approval_email, send_access_code_request_notification

EMAIL_DOMAIN = '@cit.edu'


def register_choice(request):
    """Display registration type choice page"""
    return render(request, 'register_choice.html')


def pre_admin_register(request):
    """Handle access code verification before showing admin registration form"""
    if request.method == 'POST':
        access_code = request.POST.get('access_code', '').strip()

        try:
            org_access_code = OrganizationAccessCode.objects.get(
                access_code=access_code,
                is_active=True,
                used_by__isnull=True
            )

            if org_access_code.expires_at and timezone.now() > org_access_code.expires_at:
                messages.error(request, 'This access code has expired.')
                return render(request, 'pre_admin_register.html')

            # Check if organization already has a verified admin
            verified_admin_exists = AdminProfile.objects.filter(
                organization_name=org_access_code.organization_name,
                is_verified=True
            ).exists()

            if verified_admin_exists:
                messages.error(
                    request,
                    f'The organization "{org_access_code.organization_name}" already has a verified administrator.'
                )
                return render(request, 'pre_admin_register.html')

            # Store in session
            request.session['admin_access_verified'] = True
            request.session['access_code_verified'] = access_code
            request.session['organization_name'] = org_access_code.organization_name
            request.session['access_code_id'] = org_access_code.id

            # Find the most recent approved request for this organization
            access_request = AccessCodeRequest.objects.filter(
                organization_name=org_access_code.organization_name,
                status='approved'
            ).order_by('-created_at').first()

            if access_request:
                # Store the request data in session for consistency
                request.session['access_code_request_data'] = {
                    'name': access_request.name,
                    'email': access_request.email,
                    'cit_id': access_request.cit_id,
                    'organization_full': access_request.organization_name
                }

                # Pass all parameters including cit_id
                redirect_url = reverse(
                    'register_administrator') + f'?name={access_request.name}&cit_id={access_request.cit_id}&email={access_request.email}&organization={access_request.organization_name}'
                messages.success(request,
                                 f'Access code verified for {org_access_code.organization_name}! You can now proceed with organizer registration.')
                return redirect(redirect_url)

            messages.success(request,
                             f'Access code verified for {org_access_code.organization_name}! You can now proceed with organizer registration.')
            return redirect('register_administrator')

        except OrganizationAccessCode.DoesNotExist:
            # Hardcoded codes for backward compatibility
            VALID_ACCESS_CODES = [
                '123456', '654321', '000000', '111111', '222222', '333333',
                '444444', '555555', '666666', '777777', '888888', '999999'
            ]

            if access_code in VALID_ACCESS_CODES:
                request.session['admin_access_verified'] = True
                request.session['access_code_verified'] = access_code
                messages.success(request, 'Access code verified! You can now proceed with organizer registration.')
                return redirect('register_administrator')
            else:
                messages.error(request, 'Invalid access code. Please try again or contact your organization head.')
                return render(request, 'pre_admin_register.html')
        except Exception as e:
            messages.error(request, f'Error verifying access code: {str(e)}')
            return render(request, 'pre_admin_register.html')

    return render(request, 'pre_admin_register.html')


def is_admin_user(user):
    """Check if user is an admin"""
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(is_admin_user)
def access_code_request_list(request):
    """Admin view to list all access code requests"""
    requests = AccessCodeRequest.objects.all().order_by('-created_at')
    return render(request, 'admin/access_code_requests.html', {
        'requests': requests
    })


@login_required
@user_passes_test(is_admin_user)
def review_access_code_request(request, request_id):
    """Admin view to review a specific access code request"""
    access_request = get_object_or_404(AccessCodeRequest, id=request_id)
    return render(request, 'admin/review_access_request.html', {
        'access_request': access_request
    })


# ================================================
# ONE-CLICK ACTION VIEWS
# ================================================

def one_click_approve(request, request_id):
    """Handle one-click approval from email"""
    try:
        access_request = get_object_or_404(AccessCodeRequest, id=request_id)

        # Check if already processed
        if access_request.status != 'pending':
            return HttpResponse(f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Already Processed</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        background: #f8fafc;
                        margin: 0;
                        padding: 20px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                    }}
                    .info-box {{
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                        text-align: center;
                        max-width: 600px;
                        border-left: 4px solid #F59E0B;
                    }}
                    .info-icon {{
                        font-size: 80px;
                        color: #F59E0B;
                        margin-bottom: 20px;
                    }}
                    h1 {{
                        color: #F59E0B;
                        margin-bottom: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="info-box">
                    <div class="info-icon">ℹ️</div>
                    <h1>Request Already Processed</h1>
                    <p>This request was already <strong>{access_request.status}</strong> on {access_request.reviewed_at.strftime('%Y-%m-%d %H:%M') if access_request.reviewed_at else 'unknown date'}.</p>
                    <p style="margin-top: 30px;">
                        <a href="/" style="display: inline-block; background: #00A9FF; color: white; padding: 12px 30px; text-decoration: none; border-radius: 50px; font-weight: bold;">
                            Return to Home
                        </a>
                    </p>
                </div>
            </body>
            </html>
            ''')

        # Check if organization already has a verified admin
        verified_admin_exists = AdminProfile.objects.filter(
            organization_name=access_request.organization_name,
            is_verified=True
        ).exists()

        if verified_admin_exists:
            return HttpResponse(f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Organization Already Has Admin</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        background: #f8fafc;
                        margin: 0;
                        padding: 20px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                    }}
                    .error-box {{
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                        text-align: center;
                        max-width: 600px;
                        border-left: 4px solid #DC2626;
                    }}
                    .error-icon {{
                        font-size: 80px;
                        color: #DC2626;
                        margin-bottom: 20px;
                    }}
                    h1 {{
                        color: #DC2626;
                        margin-bottom: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="error-box">
                    <div class="error-icon">❌</div>
                    <h1>Cannot Approve Request</h1>
                    <p>The organization <strong>"{access_request.organization_name}"</strong> already has a verified administrator.</p>
                    <p>Please contact the existing administrator or ask the requester to choose a different organization.</p>
                    <p style="margin-top: 30px;">
                        <a href="/" style="display: inline-block; background: #00A9FF; color: white; padding: 12px 30px; text-decoration: none; border-radius: 50px; font-weight: bold;">
                            Return to Home
                        </a>
                    </p>
                </div>
            </body>
            </html>
            ''')

        # Generate access code
        access_code = access_request.generate_access_code()

        # Update request status
        access_request.status = 'approved'
        access_request.reviewed_at = timezone.now()
        access_request.save()

        # Prepare request data for email
        request_data = {
            'name': access_request.name,
            'cit_id': access_request.cit_id,
            'email': access_request.email,
            'organization_name': access_request.organization_name,
            'message': access_request.message
        }

        # Send approval email to requester
        email_sent = send_access_code_approval_email(request_data, access_code)

        # Create OrganizationAccessCode record
        OrganizationAccessCode.objects.create(
            organization_name=access_request.organization_name,
            access_code=access_code,
            is_active=True,
            expires_at=timezone.now() + timezone.timedelta(days=7)
        )

        # IMPORTANT: Store ALL data in session including cit_id
        organization_full = access_request.organization_name
        organization_abbrev = None

        # Find the abbreviation
        for abbrev, full_name in ORGANIZATION_MAPPING.items():
            if full_name == organization_full:
                organization_abbrev = abbrev
                break

        # Store ALL data in session consistently - MAKE SURE CIT_ID IS INCLUDED
        request.session['access_code_request_data'] = {
            'name': access_request.name,
            'cit_id': access_request.cit_id if access_request.cit_id else '',  # Explicitly include cit_id
            'email': access_request.email,
            'organization_abbrev': organization_abbrev,
            'organization_full': organization_full
        }

        print(f"DEBUG: Stored in session - cit_id: {access_request.cit_id}")

        # Create a direct registration link with all prefilled data
        from urllib.parse import quote
        registration_url = reverse('register_administrator')

        # Build the URL with all parameters including cit_id
        params = f"?name={quote(access_request.name)}&cit_id={quote(access_request.cit_id if access_request.cit_id else '')}&email={quote(access_request.email)}&organization={quote(access_request.organization_name)}"
        full_registration_url = f"{request.build_absolute_uri('/')[:-1]}{registration_url}{params}"

        # Also create a direct link to request_access_code with prefilled data
        request_access_url = reverse('request_access_code')
        request_access_params = f"?name={quote(access_request.name)}&cit_id={quote(access_request.cit_id if access_request.cit_id else '')}&email={quote(access_request.email)}&organization={quote(access_request.organization_name)}"
        full_request_access_url = f"{request.build_absolute_uri('/')[:-1]}{request_access_url}{request_access_params}"

        return HttpResponse(f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Request Approved</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: #f8fafc;
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }}
                .success-box {{
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 600px;
                    border-left: 4px solid #10B981;
                }}
                .success-icon {{
                    font-size: 80px;
                    color: #10B981;
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #10B981;
                    margin-bottom: 20px;
                }}
                .access-code {{
                    font-size: 32px;
                    font-weight: bold;
                    color: #1e40af;
                    background: #eff6ff;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                    letter-spacing: 5px;
                    border: 2px solid #3b82f6;
                }}
                .info {{
                    background: #f0fdf4;
                    border: 1px solid #86efac;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 20px 0;
                    text-align: left;
                }}
                .registration-box {{
                    margin: 30px 0;
                    padding: 20px;
                    background: #f0f9ff;
                    border-radius: 10px;
                    border: 2px solid #3b82f6;
                }}
                .registration-link {{
                    display: inline-block;
                    background: linear-gradient(to right, #10B981, #059669);
                    color: white;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 50px;
                    font-weight: bold;
                    margin: 15px 0;
                    font-size: 1.1rem;
                }}
                .registration-link:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(16, 185, 129, 0.4);
                }}
                .secondary-link {{
                    display: inline-block;
                    background: linear-gradient(to right, #3b82f6, #1d4ed8);
                    color: white;
                    padding: 12px 25px;
                    text-decoration: none;
                    border-radius: 50px;
                    font-weight: bold;
                    margin: 10px;
                    font-size: 0.9rem;
                }}
                .link-group {{
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                    margin: 20px 0;
                }}
            </style>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
        </head>
        <body>
            <div class="success-box">
                <div class="success-icon">✅</div>
                <h1>Request Approved Successfully!</h1>

                <div class="info">
                    <p><strong>Requester:</strong> {access_request.name}</p>
                    <p><strong>Employee ID:</strong> {access_request.cit_id if access_request.cit_id else 'Not provided'}</p>
                    <p><strong>Email:</strong> {access_request.email}</p>
                    <p><strong>Organization:</strong> {access_request.organization_name}</p>
                    <p><strong>Status:</strong> ✅ Access code sent to requester</p>
                </div>

                <p>Generated Access Code:</p>
                <div class="access-code">{access_code}</div>

                <div class="registration-box">
                    <h3 style="color: #1e40af; margin-top: 0;">📝 Ready to Register!</h3>
                    <p>The requester can now register with their information pre-filled:</p>

                    <div class="link-group">
                        <a href="{full_registration_url}" class="registration-link">
                            <i class="fas fa-user-plus"></i> Go to Organizer Registration (All info pre-filled)
                        </a>

                        <a href="{full_request_access_url}" class="secondary-link">
                            <i class="fas fa-edit"></i> View/Edit Request Details First
                        </a>
                    </div>

                    <p style="color: #666; font-size: 0.9rem; margin-top: 10px;">
                        The first link takes them directly to organizer registration. The second link shows their request details first.
                    </p>
                </div>

                <p><strong style="color: #059669;">✅ The access code has been sent to {access_request.email}</strong></p>
                <p>The code will expire in 7 days.</p>

                <p style="color: #666; font-size: 0.9rem; margin-top: 30px;">
                    This window can be closed. The requester has received their access code.
                </p>

                <p style="margin-top: 30px;">
                    <a href="/" style="display: inline-block; background: #00A9FF; color: white; padding: 12px 30px; text-decoration: none; border-radius: 50px; font-weight: bold;">
                        Return to Home
                    </a>
                </p>
            </div>
        </body>
        </html>
        ''')

    except Exception as e:
        return HttpResponse(f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: #f8fafc;
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }}
                .error-box {{
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 600px;
                    border-left: 4px solid #DC2626;
                }}
                .error-icon {{
                    font-size: 80px;
                    color: #DC2626;
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #DC2626;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="error-box">
                <div class="error-icon">❌</div>
                <h1>Error Processing Request</h1>
                <p>Error: {str(e)}</p>
                <p style="margin-top: 30px;">
                    <a href="/" style="display: inline-block; background: #00A9FF; color: white; padding: 12px 30px; text-decoration: none; border-radius: 50px; font-weight: bold;">
                        Return to Home
                    </a>
                </p>
            </div>
        </body>
        </html>
        ''')

def one_click_decline(request, request_id):
    """Handle one-click decline from email"""
    access_request = get_object_or_404(AccessCodeRequest, id=request_id)

    # Check if already processed
    if access_request.status != 'pending':
        return HttpResponse(f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Already Processed</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: #f8fafc;
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }}
                .info-box {{
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 600px;
                    border-left: 4px solid #F59E0B;
                }}
                .info-icon {{
                    font-size: 80px;
                    color: #F59E0B;
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #F59E0B;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="info-box">
                <div class="info-icon">ℹ️</div>
                <h1>Request Already Processed</h1>
                <p>This request was already <strong>{access_request.status}</strong> on {access_request.reviewed_at.strftime('%Y-%m-%d %H:%M') if access_request.reviewed_at else 'unknown date'}.</p>
                <p style="margin-top: 30px;">
                    <a href="/" style="display: inline-block; background: #00A9FF; color: white; padding: 12px 30px; text-decoration: none; border-radius: 50px; font-weight: bold;">
                        Return to Home
                    </a>
                </p>
            </div>
        </body>
        </html>
        ''')

    if request.method == 'POST':
        decline_reason = request.POST.get('reason', '').strip()

        if not decline_reason:
            # Show form again with error
            return HttpResponse(f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Decline Request</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        background: #f8fafc;
                        margin: 0;
                        padding: 20px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                    }}
                    .form-box {{
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                        text-align: center;
                        max-width: 600px;
                        border-left: 4px solid #DC2626;
                    }}
                    .decline-icon {{
                        font-size: 60px;
                        color: #DC2626;
                        margin-bottom: 20px;
                    }}
                    h1 {{
                        color: #DC2626;
                        margin-bottom: 20px;
                    }}
                    textarea {{
                        width: 100%;
                        padding: 15px;
                        border: 2px solid #e2e8f0;
                        border-radius: 8px;
                        font-size: 16px;
                        margin: 20px 0;
                        resize: vertical;
                        min-height: 100px;
                    }}
                    textarea:focus {{
                        outline: none;
                        border-color: #DC2626;
                        box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.2);
                    }}
                    .btn {{
                        display: inline-block;
                        background: #DC2626;
                        color: white;
                        padding: 12px 30px;
                        text-decoration: none;
                        border-radius: 50px;
                        font-weight: bold;
                        margin-top: 10px;
                        border: none;
                        cursor: pointer;
                    }}
                    .info {{
                        background: #fef2f2;
                        border: 1px solid #fca5a5;
                        border-radius: 8px;
                        padding: 15px;
                        margin: 20px 0;
                        text-align: left;
                    }}
                    .error {{
                        color: #DC2626;
                        background: #FEF2F2;
                        padding: 10px;
                        border-radius: 5px;
                        margin: 10px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="form-box">
                    <div class="decline-icon">❌</div>
                    <h1>Decline Access Code Request</h1>

                    <div class="info">
                        <p><strong>Requester:</strong> {access_request.name}</p>
                        <p><strong>Email:</strong> {access_request.email}</p>
                        <p><strong>Organization:</strong> {access_request.organization_name}</p>
                        <p><strong>Request ID:</strong> {request_id}</p>
                    </div>

                    <div class="error">Reason is required. Please enter a reason below.</div>

                    <form method="post">
                        <label for="decline_reason">
                            <strong>Reason for Declining:</strong><br>
                            <small style="color: #666;">This will be sent to the requester</small>
                        </label>
                        <textarea 
                            id="decline_reason" 
                            name="reason" 
                            placeholder="Please provide a clear reason why this request is being declined..."
                            required></textarea>

                        <div>
                            <button type="submit" class="btn">
                                Submit Decline & Send Email
                            </button>
                        </div>
                    </form>

                    <p style="color: #666; font-size: 0.9rem; margin-top: 20px;">
                        Submitting will immediately send a decline email to the requester.
                    </p>
                </div>
            </body>
            </html>
            ''')

        # Update request status
        access_request.status = 'declined'
        access_request.reviewed_at = timezone.now()
        access_request.save()

        # Prepare request data for email
        request_data = {
            'name': access_request.name,
            'email': access_request.email,
            'organization_name': access_request.organization_name,
            'message': access_request.message
        }

        # Send declined email
        email_sent = send_access_code_declined_email(request_data, decline_reason)

        # Return success page
        return HttpResponse(f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Request Declined</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: #f8fafc;
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }}
                .decline-box {{
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 600px;
                    border-left: 4px solid #DC2626;
                }}
                .decline-icon {{
                    font-size: 80px;
                    color: #DC2626;
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #DC2626;
                    margin-bottom: 20px;
                }}
                .info {{
                    background: #FEF2F2;
                    border: 1px solid #fca5a5;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 20px 0;
                    text-align: left;
                }}
            </style>
        </head>
        <body>
            <div class="decline-box">
                <div class="decline-icon">❌</div>
                <h1>Request Declined Successfully</h1>

                <div class="info">
                    <p><strong>Requester:</strong> {access_request.name}</p>
                    <p><strong>Email:</strong> {access_request.email}</p>
                    <p><strong>Organization:</strong> {access_request.organization_name}</p>
                    <p><strong>Reason:</strong> {decline_reason}</p>
                    <p><strong>Status:</strong> ✅ Decline notification has been sent to requester.</p>
                </div>

                <p style="color: #666; font-size: 0.9rem; margin-top: 30px;">
                    This window can be closed. The requester has been notified of the decline.
                </p>

                <p style="margin-top: 30px;">
                    <a href="/" style="display: inline-block; background: #00A9FF; color: white; padding: 12px 30px; text-decoration: none; border-radius: 50px; font-weight: bold;">
                        Return to Home
                    </a>
                </p>
            </div>
        </body>
        </html>
        ''')

    # GET request - show form
    return HttpResponse(f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Decline Request</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f8fafc;
                margin: 0;
                padding: 20px;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }}
            .form-box {{
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                text-align: center;
                max-width: 600px;
                border-left: 4px solid #DC2626;
            }}
            .decline-icon {{
                font-size: 60px;
                color: #DC2626;
                margin-bottom: 20px;
            }}
            h1 {{
                color: #DC2626;
                margin-bottom: 20px;
            }}
            textarea {{
                width: 100%;
                padding: 15px;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                font-size: 16px;
                margin: 20px 0;
                resize: vertical;
                min-height: 100px;
            }}
            textarea:focus {{
                outline: none;
                border-color: #DC2626;
                box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.2);
            }}
            .btn {{
                display: inline-block;
                background: #DC2626;
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 50px;
                font-weight: bold;
                margin-top: 10px;
                border: none;
                cursor: pointer;
            }}
            .info {{
                background: #fef2f2;
                border: 1px solid #fca5a5;
                border-radius: 8px;
                padding: 15px;
                margin: 20px 0;
                text-align: left;
            }}
        </style>
    </head>
<body>
        <div class="form-box">
            <div class="decline-icon">❌</div>
            <h1>Decline Access Code Request</h1>

            <div class="info">
                <p><strong>Requester:</strong> {access_request.name}</p>
                <p><strong>Email:</strong> {access_request.email}</p>
                <p><strong>Organization:</strong> {access_request.organization_name}</p>
                <p><strong>Request ID:</strong> {request_id}</p>
            </div>

            <form method="post">
                <label for="decline_reason">
                    <strong>Reason for Declining:</strong><br>
                    <small style="color: #666;">This will be sent to the requester</small>
                </label>
                <textarea 
                    id="decline_reason" 
                    name="reason" 
                    placeholder="Please provide a clear reason why this request is being declined..."
                    required></textarea>

                <div>
                    <button type="submit" class="btn">
                        Submit Decline & Send Email
                    </button>
                </div>
            </form>

            <p style="color: #666; font-size: 0.9rem; margin-top: 20px;">
                Submitting will immediately send a decline email to the requester.
            </p>
        </div>
    </body>
    </html>
    ''')


ORGANIZATION_MAPPING = {
    # NON-DEPARTMENTAL ORGANIZATION
    'RACMC-CIT': 'Rotaract Club of Metro Cebu - CIT Chapter',
    'DOST SA CIT-U': 'DOST SA CIT-U',
    'CRCY': 'College Red Cross Youth',
    'EDS': 'Elite Debate Society',
    'HONSOC': 'CIT-U Honor Society',
    'CIT-U SPRCY': 'Senior Plus Red Cross Youth',
    'WEL': 'Wildcats Esports League',
    'CFC': 'CIT-U Christian Fellowship',
    'REAVO': 'Radio/Rescue Emergency Assistance Volunteer Organization',
    'JJC CIT-U': 'CIT University Junior Jaycees',
    'TTSP': 'The Technologian Student Press',
    'TQ': 'The Technologian Quills',
    'PFCIT-U SHS': 'SHS Peer Facilitators Program',

    # DEPARTMENTAL ORGANIZATION
    'CASEPsychSoc': 'PsychSoc (Psychology Society)',
    'YEACIT-U': 'Young Educators Association',
    'CELSA': 'Communication and English Language Students Association',
    'CAMVAS': 'Creative Alliance of Multimedia and Visual Arts Student',
    'CCJJCC': 'Junior Criminology Council',
    'CCSCSS': 'Computer Students\' Society',
    'CEAJPIChE CIT-U': 'Junior Philippine Institute of Chemical Engineers',
    'UAPSA': 'United Architects of the Philippines Student Auxiliary',
    'JPSME': 'Junior Philippine Society of Mechanical Engineers',
    'IIEE-CSC CIT-U': 'Institute of Integrated Electrical Engineers - CSC',
    'ICpEP.SE': 'Institute of Computer Engineers Student Edition',
    'IECEP CIT-U SC': 'Institute of Electronics Engineers of the Philippines',
    'IEC': 'Industrial Engineering Council',
    'ACIP - CITU SC': 'American Concrete Institute Philippines - SC',
    'PICE CIT-U SC': 'Philippine Institute of Civil Engineers - SC',
    'PSEM-VSC': 'Philippine Society of Mining Engineers - VSC',
    'CMBAJAHTEX': 'Junior Association of Hospitality and Tourism Executives',
    'JFINEX - CITU': 'Junior Financial Executives - CIT University Chapter',
    'JPMAP': 'Junior People Management Association of the Philippines',
    'IMA': 'Institute of Management Accountants',
    'JPIA': 'Junior Philippine Institute of Accountants',

    # SENIOR HIGH SCHOOL
    'CNAHSHASBO': 'Health Alliance Student Body Organization',
    'NCES': 'Nursing Community Extension Services',
    'SHS DC': 'Senior High School Dance Club',
    'YAS': 'Young Artist Society',
    'GTCIT-U SHS': 'SHS GleeTechs',
    'WCC': 'WILDCATS CHESS CLUB'
}


def request_access_code(request):
    """Handle access code requests"""
    # Get all data from session if available (from access code approval)
    access_request_data = request.session.get('access_code_request_data', {})

    print("DEBUG: Session data:", dict(request.session))
    print("DEBUG: access_code_request_data from session:", access_request_data)

    # Check for GET parameters (from one-click approval email link)
    if request.GET:
        name = request.GET.get('name', '').strip()
        email = request.GET.get('email', '').strip()
        cit_id = request.GET.get('cit_id', '').strip()
        organization_full = request.GET.get('organization', '').strip()

        print(f"DEBUG: GET params - name={name}, email={email}, cit_id={cit_id}, organization={organization_full}")

        # If we have GET parameters, use them (these come from one-click approval)
        if name and email and organization_full:
            access_request_data = {
                'name': name,
                'email': email,
                'cit_id': cit_id if cit_id else '',
                'organization_full': organization_full
            }

            # Find the abbreviation from the full organization name
            for abbrev, full_name in ORGANIZATION_MAPPING.items():
                if full_name == organization_full:
                    access_request_data['organization_abbrev'] = abbrev
                    break

            # Store in session for consistency
            request.session['access_code_request_data'] = access_request_data
            request.session.modified = True
            print("DEBUG: Updated session with GET params:", access_request_data)

    # Check if we should pre-fill from approved access request (when coming from one-click approval via session)
    elif request.session.get('access_code_request_data'):
        access_request_data = request.session['access_code_request_data']
        print("DEBUG: Using existing session data:", access_request_data)

        # If cit_id is missing or empty in session, try to get it from AccessCodeRequest
        if 'cit_id' not in access_request_data or not access_request_data['cit_id']:
            try:
                # Find the latest approved request matching session data
                name = access_request_data.get('name', '')
                email = access_request_data.get('email', '')
                organization_full = access_request_data.get('organization_full', '')

                if name and email and organization_full:
                    access_request = AccessCodeRequest.objects.filter(
                        name=name,
                        email=email,
                        organization_name=organization_full,
                        status='approved'
                    ).order_by('-created_at').first()

                    if access_request and access_request.cit_id:
                        access_request_data['cit_id'] = access_request.cit_id
                        request.session['access_code_request_data'] = access_request_data
                        request.session.modified = True
                        print(f"DEBUG: Retrieved cit_id from AccessCodeRequest: {access_request.cit_id}")
                    elif access_request:
                        print(f"DEBUG: AccessCodeRequest found but cit_id is empty: {access_request.cit_id}")
                else:
                    print("DEBUG: Missing name, email, or organization_full in session data")
            except Exception as e:
                print(f"DEBUG: Error retrieving cit_id from database: {str(e)}")
                import traceback
                traceback.print_exc()

    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name', '').strip()
        cit_id = request.POST.get('cit_id', '').strip()
        email = request.POST.get('email', '').strip()
        organization_abbrev = request.POST.get('organization_name', '').strip()
        message = request.POST.get('message', '').strip()

        # Get the full organization name from mapping
        organization_full = ORGANIZATION_MAPPING.get(organization_abbrev, organization_abbrev)

        # Validate required fields - UPDATED: Include cit_id in validation
        if not all([name, email, organization_abbrev, cit_id]):
            messages.error(request, 'Please fill out all required fields including Employee ID.')
            return render(request, 'request_access_code.html', {
                'name': name,
                'email': email,
                'cit_id': cit_id,
                'organization_abbrev': organization_abbrev,
                'organization_full': organization_full,
            })

        # Validate email domain
        if not email.endswith(EMAIL_DOMAIN):
            messages.error(request, f'Please use a valid {EMAIL_DOMAIN} email address.')
            return render(request, 'request_access_code.html', {
                'name': name,
                'email': email,
                'cit_id': cit_id,
                'organization_abbrev': organization_abbrev,
                'organization_full': organization_full,
            })

        # Validate CIT ID format - UPDATED: Ensure it's not empty
        if not cit_id:
            messages.error(request, 'Employee ID is required.')
            return render(request, 'request_access_code.html', {
                'name': name,
                'email': email,
                'cit_id': cit_id,
                'organization_abbrev': organization_abbrev,
                'organization_full': organization_full,
            })

        if not re.fullmatch(r'^[0-9-]+$', cit_id):
            messages.error(request, 'Employee ID can only contain numbers and dashes (-).')
            return render(request, 'request_access_code.html', {
                'name': name,
                'email': email,
                'cit_id': cit_id,
                'organization_abbrev': organization_abbrev,
                'organization_full': organization_full,
            })

        # Check if organization already has a verified admin
        verified_admin_exists = AdminProfile.objects.filter(
            organization_name=organization_full,
            is_verified=True
        ).exists()

        if verified_admin_exists:
            messages.error(
                request,
                f'The organization "{organization_full}" already has a verified administrator. '
                'Please contact the existing administrator or choose a different organization.'
            )
            return render(request, 'request_access_code.html', {
                'name': name,
                'email': email,
                'cit_id': cit_id,
                'organization_abbrev': organization_abbrev,
                'organization_full': organization_full,
            })

        # Check for duplicate pending requests
        duplicate_request = AccessCodeRequest.objects.filter(
            email=email,
            organization_name=organization_full,
            status='pending'
        ).exists()

        if duplicate_request:
            messages.info(
                request,
                'You already have a pending request for this organization. '
                'Please wait for our administrators to review it.'
            )
            return render(request, 'request_access_code.html', {
                'name': name,
                'email': email,
                'cit_id': cit_id,
                'organization_abbrev': organization_abbrev,
                'organization_full': organization_full,
            })

        try:
            # Create access code request with cit_id - UPDATED: cit_id is now required
            access_request = AccessCodeRequest.objects.create(
                name=name,
                cit_id=cit_id,  # This field is now required
                email=email,
                organization_name=organization_full,
                message=message,
                status='pending'
            )

            print(f"DEBUG: Created AccessCodeRequest with cit_id: {cit_id}")

            # Store request data in session (for any potential future use)
            request.session['access_code_request_data'] = {
                'name': name,
                'email': email,
                'cit_id': cit_id,
                'organization_abbrev': organization_abbrev,
                'organization_full': organization_full
            }

            # Prepare request data for email
            request_data = {
                'name': name,
                'cit_id': cit_id,
                'email': email,
                'organization_name': organization_full,
                'message': message,
                'base_url': request.build_absolute_uri('/')[:-1]
            }

            # Send notification email to admin
            email_sent = send_access_code_request_notification(
                request_data,
                str(access_request.id)
            )

            if email_sent:
                # Clear the session data after successful submission
                if 'access_code_request_data' in request.session:
                    del request.session['access_code_request_data']

                messages.success(
                    request,
                    'Your request has been submitted successfully! '
                    'Our administrators will review it and you will receive an email with the access code once approved.'
                )
            else:
                messages.warning(
                    request,
                    'Your request has been submitted, but there was an issue sending the notification email.'
                )

            return redirect('pre_admin_register')

        except Exception as e:
            print(f"DEBUG: Error creating AccessCodeRequest: {str(e)}")
            messages.error(request, f'An error occurred while submitting your request: {str(e)}')
            return render(request, 'request_access_code.html', {
                'name': name,
                'email': email,
                'cit_id': cit_id,
                'organization_abbrev': organization_abbrev,
                'organization_full': organization_full,
            })

    # GET request - show the request form with pre-filled data if available
    # Get values from access_request_data
    name_value = access_request_data.get('name', '')
    email_value = access_request_data.get('email', '')
    cit_id_value = access_request_data.get('cit_id', '')
    organization_abbrev_value = access_request_data.get('organization_abbrev', '')
    organization_full_value = access_request_data.get('organization_full', '')

    # If cit_id is empty but we have other data, try to find it in database
    if not cit_id_value and name_value and email_value and organization_full_value:
        try:
            access_request = AccessCodeRequest.objects.filter(
                name=name_value,
                email=email_value,
                organization_name=organization_full_value,
                status='approved'
            ).order_by('-created_at').first()

            if access_request and access_request.cit_id:
                cit_id_value = access_request.cit_id
                print(f"DEBUG: Found cit_id in database for GET: {cit_id_value}")
        except Exception as e:
            print(f"DEBUG: Error looking up cit_id in GET: {str(e)}")

    context = {
        'name': name_value,
        'email': email_value,
        'cit_id': cit_id_value,
        'organization_abbrev': organization_abbrev_value,
        'organization_full': organization_full_value,
        'ORGANIZATION_MAPPING': ORGANIZATION_MAPPING
    }

    print("DEBUG: Context passed to template:", context)
    print(f"DEBUG: cit_id being passed: {cit_id_value}")
    print(f"DEBUG: Is cit_id in session data: {'cit_id' in access_request_data}")
    if 'cit_id' in access_request_data:
        print(f"DEBUG: cit_id in session data: {access_request_data['cit_id']}")

    return render(request, 'request_access_code.html', context)


# ================================================
# STUDENT & ADMIN REGISTRATION FUNCTIONS
# ================================================

def register_student(request):
    """Handle student registration with OTP verification"""
    print("DEBUG: register_student called")

    # Reset OTP resend count when starting new registration
    if 'student_otp_resend_count' in request.session:
        del request.session['student_otp_resend_count']

    if request.method != 'POST':
        print("DEBUG: GET request for register_student")
        return render(request, 'register_student.html')

    print("DEBUG: POST request for register_student")

    # Get form data
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '').strip()
    confirm_password = request.POST.get('confirm_password', '').strip()
    name = request.POST.get('name', '').strip()
    cit_id = request.POST.get('cit_id', '').strip()

    print(f"DEBUG: Form data - email={email}, name={name}, cit_id={cit_id}")

    # Validation
    if not all([email, password, cit_id, name]):
        print("DEBUG: Missing required fields")
        messages.error(request, 'Please fill out all required fields.')
        return render(request, 'register_student.html')

    if password != confirm_password:
        print("DEBUG: Passwords don't match")
        messages.error(request, 'Passwords do not match.')
        return render(request, 'register_student.html')

    if not (len(password) >= 8 and re.search(r'[A-Z]', password)
            and re.search(r'[a-z]', password) and re.search(r'\d', password)):
        print("DEBUG: Password requirements not met")
        messages.error(request, 'Password must be at least 8 characters with uppercase, lowercase, and number.')
        return render(request, 'register_student.html')

    if not email.endswith(EMAIL_DOMAIN):
        print(f"DEBUG: Invalid email domain: {email}")
        messages.error(request, f'Registration is limited to {EMAIL_DOMAIN} email addresses only.')
        return render(request, 'register_student.html')

    if not re.fullmatch(r'^[0-9-]+$', cit_id):
        print(f"DEBUG: Invalid CIT ID format: {cit_id}")
        messages.error(request, 'Student ID can only contain numbers and dashes (-).')
        return render(request, 'register_student.html')

    # MODIFIED: Check for existing VERIFIED users only
    # Allow re-registration if existing account is not verified
    existing_user = User.objects.filter(username=email).first()
    if existing_user:
        try:
            student_profile = StudentProfile.objects.get(user=existing_user)
            if student_profile.is_verified:
                print(f"DEBUG: Verified student with email {email} already exists")
                messages.error(request, 'A verified student with this email already exists.')
                return render(request, 'register_student.html')
            else:
                # Delete the unverified student account to allow re-registration
                student_profile.delete()
                existing_user.delete()
                print(f"DEBUG: Deleted unverified student with email {email}")
                # No message shown to user
        except StudentProfile.DoesNotExist:
            try:
                admin_profile = AdminProfile.objects.get(user=existing_user)
                if admin_profile.is_verified:
                    print(f"DEBUG: Verified admin with email {email} already exists")
                    messages.error(request, 'A verified administrator with this email already exists.')
                    return render(request, 'register_student.html')
                else:
                    # Delete the unverified admin account
                    admin_profile.delete()
                    existing_user.delete()
                    print(f"DEBUG: Deleted unverified admin with email {email}")
                    # No message shown to user
            except AdminProfile.DoesNotExist:
                # User exists but has no profile - delete it
                existing_user.delete()

    # MODIFIED: Check for existing CIT ID in VERIFIED accounts only
    existing_student_with_cit_id = StudentProfile.objects.filter(cit_id=cit_id).first()
    if existing_student_with_cit_id:
        if existing_student_with_cit_id.is_verified:
            print(f"DEBUG: Verified student with CIT ID {cit_id} already exists")
            messages.error(request, 'This Student ID is already registered with a verified account.')
            return render(request, 'register_student.html')
        else:
            # Delete the unverified student account
            existing_student_with_cit_id.user.delete()
            print(f"DEBUG: Deleted unverified student with CIT ID {cit_id}")
            # No message shown to user

    # Also check AdminProfile for CIT ID
    existing_admin_with_cit_id = AdminProfile.objects.filter(cit_id=cit_id).first()
    if existing_admin_with_cit_id:
        if existing_admin_with_cit_id.is_verified:
            print(f"DEBUG: Verified admin with CIT ID {cit_id} already exists")
            messages.error(request, 'This ID is already registered as a verified administrator.')
            return render(request, 'register_student.html')
        else:
            # Delete the unverified admin account
            existing_admin_with_cit_id.user.delete()
            print(f"DEBUG: Deleted unverified admin with CIT ID {cit_id}")
            # No message shown to user

    # Create student user
    user = None
    student_profile = None
    try:
        print("DEBUG: Creating user...")
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            is_staff=False,
            is_active=False
        )
        print(f"DEBUG: User created with id: {user.id}")

        print("DEBUG: Creating student profile...")
        student_profile = StudentProfile.objects.create(
            user=user,
            name=name,
            cit_id=cit_id,
            is_verified=False,
            created_at=timezone.now()
        )
        print(f"DEBUG: Student profile created with id: {student_profile.id}")

        # Store user ID in session for OTP verification
        request.session['pending_student_id'] = user.id
        request.session['pending_student_email'] = email

        # Initialize OTP resend counter
        request.session['student_otp_resend_count'] = 0
        print("DEBUG: Session data set")

        # Send OTP email
        print("DEBUG: Sending OTP email...")
        email_sent = send_student_otp_email(student_profile, request)

        if email_sent:
            # FIX: Refresh the profile from database to ensure OTP data is loaded
            student_profile.refresh_from_db()
            print(f"DEBUG: After sending OTP - OTP code: {student_profile.otp_code}")
            print(f"DEBUG: After sending OTP - OTP created at: {student_profile.otp_created_at}")

            print("DEBUG: OTP email sent successfully")
            messages.info(
                request,
                f'Verification code sent to {email}. Please check your email and enter the code within 60 seconds.'
            )
            print("DEBUG: Redirecting to verify_student_otp")
            return redirect('verify_student_otp')
        else:
            print("DEBUG: Failed to send OTP email")
            messages.error(
                request,
                'Account created but failed to send verification email. Please try again.'
            )
            # Clean up if email fails
            if student_profile:
                student_profile.delete()
            if user:
                user.delete()
            return render(request, 'register_student.html')

    except Exception as e:
        print(f"DEBUG: Exception in register_student: {str(e)}")
        print(f"DEBUG: Exception type: {type(e)}")
        import traceback
        traceback.print_exc()  # This will print the full traceback

        # Clean up in reverse order
        if student_profile:
            try:
                student_profile.delete()
            except:
                pass
        if user:
            try:
                user.delete()
            except:
                pass

        messages.error(request, f'Registration failed: {str(e)}')
        return render(request, 'register_student.html')


def register_administrator(request):
    """Handle administrator/organizer registration"""

    # Initialize variables
    name = None
    email = None
    cit_id = None
    organization_full = None

    # Check for prefilled data including cit_id
    if request.GET.get('name') and request.GET.get('email') and request.GET.get('organization'):
        name = request.GET.get('name')
        email = request.GET.get('email')
        cit_id = request.GET.get('cit_id', '')
        organization_full = request.GET.get('organization')
    elif 'prefilled_data' in request.session:
        prefilled = request.session.get('prefilled_data', {})
        name = prefilled.get('name')
        email = prefilled.get('email')
        cit_id = prefilled.get('cit_id', '')
        organization_full = prefilled.get('organization_full')
    elif request.session.get('admin_access_verified'):
        access_code = request.session.get('access_code_verified')
        if access_code:
            try:
                org_access_code = OrganizationAccessCode.objects.get(
                    access_code=access_code,
                    is_active=True,
                    used_by__isnull=True
                )
                # Get the latest approved request for this organization
                access_request = AccessCodeRequest.objects.filter(
                    organization_name=org_access_code.organization_name,
                    status='approved'
                ).order_by('-created_at').first()

                if access_request:
                    name = access_request.name
                    email = access_request.email
                    cit_id = access_request.cit_id
                    organization_full = access_request.organization_name

                    request.session['prefilled_data'] = {
                        'name': name,
                        'email': email,
                        'cit_id': cit_id,
                        'organization_full': organization_full
                    }
            except (OrganizationAccessCode.DoesNotExist, AccessCodeRequest.DoesNotExist):
                pass

    # Handle POST request
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        cit_id = request.POST.get('cit_id')
        organization_name = request.POST.get('organization_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Validate required fields including cit_id
        if not all([name, cit_id, organization_name, email, password, confirm_password]):
            messages.error(request, "Please fill out all required fields!")
            return render(request, 'register_administrator.html', {
                'name': name,
                'email': email,
                'cit_id': cit_id,
                'organization_full': organization_full
            })

        # Validate CIT ID format
        if not re.fullmatch(r'^[0-9-]+$', cit_id):
            messages.error(request, 'Employee ID can only contain numbers and dashes (-).')
            return render(request, 'register_administrator.html', {
                'name': name,
                'email': email,
                'cit_id': cit_id,
                'organization_full': organization_full
            })

        # Check if organization already has a VERIFIED admin
        if AdminProfile.objects.filter(organization_name=organization_name, is_verified=True).exists():
            messages.error(request, f"An organizer already exists for {organization_name}!")
            return render(request, 'register_administrator.html', {
                'name': name,
                'email': email,
                'cit_id': cit_id,
                'organization_full': organization_full
            })

        # MODIFIED: Check if email already exists in a VERIFIED account
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            try:
                admin_profile = AdminProfile.objects.get(user=existing_user)
                if admin_profile.is_verified:
                    messages.error(request, "Email already registered with a verified account!")
                    return render(request, 'register_administrator.html', {
                        'name': name,
                        'email': email,
                        'cit_id': cit_id,
                        'organization_full': organization_full
                    })
                else:
                    # Delete the unverified account to allow re-registration
                    pending_access_code_id = request.session.get('pending_access_code_id')
                    if pending_access_code_id:
                        try:
                            org_access_code = OrganizationAccessCode.objects.get(id=pending_access_code_id)
                            org_access_code.used_by = None
                            org_access_code.used_at = None
                            org_access_code.is_active = True
                            org_access_code.save()
                        except OrganizationAccessCode.DoesNotExist:
                            pass

                    # Delete the unverified user and profile
                    admin_profile.delete()
                    existing_user.delete()
            except AdminProfile.DoesNotExist:
                # If user exists but no admin profile, check if it's a student
                try:
                    student_profile = StudentProfile.objects.get(user=existing_user)
                    if student_profile.is_verified:
                        messages.error(request, "Email already registered as a verified student!")
                        return render(request, 'register_administrator.html', {
                            'name': name,
                            'email': email,
                            'cit_id': cit_id,
                            'organization_full': organization_full
                        })
                    else:
                        # Delete unverified student account
                        student_profile.delete()
                        existing_user.delete()
                except StudentProfile.DoesNotExist:
                    # User exists but has no profile - delete it
                    existing_user.delete()

        # MODIFIED: Check if CIT ID already exists in a VERIFIED account
        existing_admin_with_cit_id = AdminProfile.objects.filter(cit_id=cit_id).first()
        if existing_admin_with_cit_id:
            if existing_admin_with_cit_id.is_verified:
                messages.error(request, "Employee ID already registered with a verified account!")
                return render(request, 'register_administrator.html', {
                    'name': name,
                    'email': email,
                    'cit_id': cit_id,
                    'organization_full': organization_full
                })
            else:
                # Delete the unverified account
                existing_admin_with_cit_id.user.delete()

        # Also check StudentProfile for CIT ID
        existing_student_with_cit_id = StudentProfile.objects.filter(cit_id=cit_id).first()
        if existing_student_with_cit_id:
            if existing_student_with_cit_id.is_verified:
                messages.error(request, "Student ID already registered with a verified student account!")
                return render(request, 'register_administrator.html', {
                    'name': name,
                    'email': email,
                    'cit_id': cit_id,
                    'organization_full': organization_full
                })
            else:
                # Delete the unverified student account
                existing_student_with_cit_id.user.delete()

        # Password validation
        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, 'register_administrator.html', {
                'name': name,
                'email': email,
                'cit_id': cit_id,
                'organization_full': organization_full
            })

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long!")
            return render(request, 'register_administrator.html', {
                'name': name,
                'email': email,
                'cit_id': cit_id,
                'organization_full': organization_full
            })

        if not re.search(r'[A-Z]', password):
            messages.error(request, "Password must contain at least one uppercase letter!")
            return render(request, 'register_administrator.html', {
                'name': name,
                'email': email,
                'cit_id': cit_id,
                'organization_full': organization_full
            })

        if not re.search(r'[a-z]', password):
            messages.error(request, "Password must contain at least one lowercase letter!")
            return render(request, 'register_administrator.html', {
                'name': name,
                'email': email,
                'cit_id': cit_id,
                'organization_full': organization_full
            })

        if not re.search(r'\d', password):
            messages.error(request, "Password must contain at least one number!")
            return render(request, 'register_administrator.html', {
                'name': name,
                'email': email,
                'cit_id': cit_id,
                'organization_full': organization_full
            })

        try:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=name.split()[0] if name else '',
                last_name=' '.join(name.split()[1:]) if name and len(name.split()) > 1 else '',
                is_active=False,
                is_staff=True
            )

            # Create admin profile with cit_id
            admin_profile = AdminProfile.objects.create(
                user=user,
                name=name,
                cit_id=cit_id,
                organization_name=organization_name,
                is_verified=False
            )

            # Store the access code ID in session for later verification
            access_code = request.session.get('access_code_verified')
            if access_code:
                try:
                    org_access_code = OrganizationAccessCode.objects.get(
                        access_code=access_code,
                        is_active=True,
                        used_by__isnull=True
                    )
                    # Store the access code ID in session for OTP verification
                    request.session['pending_access_code_id'] = org_access_code.id
                except OrganizationAccessCode.DoesNotExist:
                    # If using hardcoded code, create a record for it
                    if access_code in ['123456', '654321', '000000', '111111', '222222', '333333',
                                       '444444', '555555', '666666', '777777', '888888', '999999']:
                        org_access_code = OrganizationAccessCode.objects.create(
                            organization_name=organization_name,
                            access_code=access_code,
                            is_active=True,
                            expires_at=timezone.now() + timezone.timedelta(days=30)
                        )
                        request.session['pending_access_code_id'] = org_access_code.id

            # Store pending registration in session
            request.session['pending_admin_id'] = user.id
            request.session['pending_admin_email'] = email

            # Send OTP for verification
            otp = admin_profile.generate_otp()
            email_sent = send_otp_email(admin_profile, request)

            if email_sent:
                messages.success(request, "Account created successfully! Please check your email for OTP verification.")
                return redirect('verify_otp')
            else:
                messages.error(request, "Account created but failed to send verification email. Please try again.")
                # Clean up - delete user and profile
                user.delete()
                return render(request, 'register_administrator.html', {
                    'name': name,
                    'email': email,
                    'cit_id': cit_id,
                    'organization_full': organization_full
                })

        except Exception as e:
            messages.error(request, f"Error creating account: {str(e)}")
            return render(request, 'register_administrator.html', {
                'name': name,
                'email': email,
                'cit_id': cit_id,
                'organization_full': organization_full
            })

    # GET request - render the form with prefilled data if available
    return render(request, 'register_administrator.html', {
        'name': name,
        'email': email,
        'cit_id': cit_id,
        'organization_full': organization_full
    })


def cleanup_pending_registration(request):
    """Clean up pending registration when user goes back"""
    pending_admin_id = request.session.get('pending_admin_id')

    if pending_admin_id:
        try:
            # Get the admin profile and user
            admin_profile = AdminProfile.objects.get(user_id=pending_admin_id)
            user = admin_profile.user

            # If there's a pending access code, make sure it's not marked as used
            pending_access_code_id = request.session.get('pending_access_code_id')
            if pending_access_code_id:
                try:
                    org_access_code = OrganizationAccessCode.objects.get(id=pending_access_code_id)
                    # Reset the access code since registration is being cancelled
                    org_access_code.used_by = None
                    org_access_code.used_at = None
                    org_access_code.is_active = True  # Keep it active for future use
                    org_access_code.save()
                except OrganizationAccessCode.DoesNotExist:
                    pass

            # Delete both the profile and user
            admin_profile.delete()
            user.delete()

            # Clear all session data
            for key in ['pending_admin_id', 'pending_admin_email', 'otp_resend_count',
                        'pending_access_code_id', 'admin_access_verified', 'access_code_verified',
                        'organization_name', 'prefilled_data', 'access_code_id']:
                if key in request.session:
                    del request.session[key]

            messages.info(request, 'Registration cancelled. You can start a new registration.')

        except (AdminProfile.DoesNotExist, User.DoesNotExist):
            # If the objects don't exist, just clear the session
            for key in ['pending_admin_id', 'pending_admin_email', 'otp_resend_count',
                        'pending_access_code_id', 'admin_access_verified', 'access_code_verified',
                        'organization_name', 'prefilled_data', 'access_code_id']:
                if key in request.session:
                    del request.session[key]

    return redirect('register_administrator')


def cleanup_pending_student_registration(request):
    """Clean up pending student registration when user goes back"""
    pending_student_id = request.session.get('pending_student_id')

    if pending_student_id:
        try:
            # Get the student profile and user
            student_profile = StudentProfile.objects.get(user_id=pending_student_id)
            user = student_profile.user

            # Delete both the profile and user
            student_profile.delete()
            user.delete()

            # Clear session data
            if 'pending_student_id' in request.session:
                del request.session['pending_student_id']
            if 'pending_student_email' in request.session:
                del request.session['pending_student_email']
            if 'student_otp_resend_count' in request.session:
                del request.session['student_otp_resend_count']

            messages.info(request, 'Registration cancelled. You can start a new registration.')

        except (StudentProfile.DoesNotExist, User.DoesNotExist):
            # If the objects don't exist, just clear the session
            if 'pending_student_id' in request.session:
                del request.session['pending_student_id']
            if 'pending_student_email' in request.session:
                del request.session['pending_student_email']
            if 'student_otp_resend_count' in request.session:
                del request.session['student_otp_resend_count']

    return redirect('register_student')


def cleanup_and_register(request):
    """Clean up and redirect to registration page"""
    return cleanup_pending_registration(request)


def verify_otp(request):
    """Handle OTP verification - Step 2: Verify account"""
    if request.method == 'GET':
        # Check if there's a pending admin verification
        if 'pending_admin_id' not in request.session:
            messages.error(request, 'No pending verification found. Please register first.')
            return redirect('register_administrator')

        # Calculate remaining time for the current OTP (60 seconds)
        remaining_time = 0
        is_otp_expired = False
        try:
            admin_profile = AdminProfile.objects.get(user_id=request.session.get('pending_admin_id'))
            if admin_profile.otp_created_at:
                elapsed_time = (timezone.now() - admin_profile.otp_created_at).total_seconds()
                remaining_time = max(0, 60 - int(elapsed_time))
                is_otp_expired = elapsed_time >= 60
        except AdminProfile.DoesNotExist:
            cleanup_pending_registration(request)
            messages.error(request, 'Registration session expired. Please register again.')
            return redirect('register_administrator')

        return render(request, 'verify_otp.html', {
            'remaining_time': remaining_time,
            'is_otp_expired': is_otp_expired
        })

    elif request.method == 'POST':
        # Verify OTP code
        entered_otp = request.POST.get('otp_code')
        pending_admin_id = request.session.get('pending_admin_id')

        if not entered_otp:
            messages.error(request, 'Please enter the verification code.')
            # Calculate remaining time for error case
            remaining_time = 0
            is_otp_expired = False
            try:
                admin_profile = AdminProfile.objects.get(user_id=pending_admin_id)
                if admin_profile.otp_created_at:
                    elapsed_time = (timezone.now() - admin_profile.otp_created_at).total_seconds()
                    remaining_time = max(0, 60 - int(elapsed_time))
                    is_otp_expired = elapsed_time >= 60
            except AdminProfile.DoesNotExist:
                cleanup_pending_registration(request)
                messages.error(request, 'Registration session expired. Please register again.')
                return redirect('register_administrator')
            return render(request, 'verify_otp.html', {
                'remaining_time': remaining_time,
                'is_otp_expired': is_otp_expired
            })

        if not pending_admin_id:
            messages.error(request, 'Session expired. Please register again.')
            return redirect('register_administrator')

        try:
            admin_profile = AdminProfile.objects.get(user_id=pending_admin_id)

            # Check if OTP is expired first (60 seconds)
            if admin_profile.is_otp_expired():
                messages.error(
                    request,
                    'Verification code has expired. Please request a new code using the "Resend Code" link.'
                )
                return render(request, 'verify_otp.html', {
                    'remaining_time': 0,
                    'is_otp_expired': True
                })

            # Then check if OTP is correct
            if admin_profile.otp_code == entered_otp:
                # OTP verified successfully
                admin_profile.is_verified = True
                admin_profile.otp_code = None
                admin_profile.otp_created_at = None
                admin_profile.save()

                admin_profile.user.is_active = True
                admin_profile.user.save()

                # MARK ACCESS CODE AS USED AFTER SUCCESSFUL VERIFICATION
                pending_access_code_id = request.session.get('pending_access_code_id')
                if pending_access_code_id:
                    try:
                        org_access_code = OrganizationAccessCode.objects.get(id=pending_access_code_id)
                        org_access_code.used_by = admin_profile.user
                        org_access_code.used_at = timezone.now()
                        org_access_code.is_active = False  # Mark as inactive since it's been used
                        org_access_code.save()

                        # Clear the session data
                        if 'pending_access_code_id' in request.session:
                            del request.session['pending_access_code_id']
                    except OrganizationAccessCode.DoesNotExist:
                        pass  # Access code record not found, but admin is still verified

                # Clean up session including resend counter
                request.session.flush()

                messages.success(request, 'Account verified successfully! Please log in to continue.')
                return redirect('login')
            else:
                # OTP is incorrect but still valid (not expired)
                # Calculate remaining time for the current OTP
                elapsed_time = (timezone.now() - admin_profile.otp_created_at).total_seconds()
                remaining_time = max(0, 60 - int(elapsed_time))
                is_otp_expired = elapsed_time >= 60

                messages.error(request, 'Invalid verification code. Please try again with the same code.')
                return render(request, 'verify_otp.html', {
                    'remaining_time': remaining_time,
                    'is_otp_expired': is_otp_expired
                })

        except AdminProfile.DoesNotExist:
            cleanup_pending_registration(request)
            messages.error(request, 'Admin profile not found. Please register again.')
            return redirect('register_administrator')


def verify_student_otp(request):
    """Handle student OTP verification - Step 2: Verify account"""
    print("DEBUG: verify_student_otp called")

    if request.method == 'GET':
        print("DEBUG: GET request")
        # Check if there's a pending student verification
        if 'pending_student_id' not in request.session:
            print("DEBUG: No pending_student_id in session")
            messages.error(request, 'No pending verification found. Please register first.')
            return redirect('register_student')

        # Calculate remaining time for the current OTP (60 seconds)
        remaining_time = 0
        is_otp_expired = False
        pending_student_email = request.session.get('pending_student_email', '')

        try:
            print("DEBUG: Trying to get student profile")
            # Get fresh instance from database
            student_profile = StudentProfile.objects.get(user_id=request.session.get('pending_student_id'))

            # FIX: Refresh the instance from database
            student_profile.refresh_from_db()

            print(f"DEBUG: OTP code in DB: {student_profile.otp_code}")
            print(f"DEBUG: OTP created at: {student_profile.otp_created_at}")

            if not student_profile.otp_code or not student_profile.otp_created_at:
                print("DEBUG: No OTP data found, generating new OTP")
                # Generate new OTP
                student_profile.generate_otp()
                send_student_otp_email(student_profile, request)
                messages.info(request, 'New verification code sent! Please check your email.')
                remaining_time = 60
                is_otp_expired = False
            else:
                # Calculate time based on existing OTP
                elapsed_time = (timezone.now() - student_profile.otp_created_at).total_seconds()
                remaining_time = max(0, 60 - int(elapsed_time))
                is_otp_expired = elapsed_time >= 60
                print(f"DEBUG: OTP age: {elapsed_time} seconds, remaining: {remaining_time}")

        except StudentProfile.DoesNotExist:
            print("DEBUG: StudentProfile.DoesNotExist")
            # If student profile doesn't exist, cleanup and redirect
            cleanup_pending_student_registration(request)
            messages.error(request, 'Registration session expired. Please register again.')
            return redirect('register_student')
        except Exception as e:
            print(f"DEBUG: Exception in try block: {str(e)}")
            import traceback
            traceback.print_exc()
            # Default to expired
            is_otp_expired = True
            remaining_time = 0

        print("DEBUG: Rendering template with remaining_time={}, is_otp_expired={}".format(remaining_time,
                                                                                           is_otp_expired))
        return render(request, 'verify_student_otp.html', {
            'remaining_time': remaining_time,
            'is_otp_expired': is_otp_expired,
            'pending_student_email': pending_student_email
        })

    elif request.method == 'POST':
        # ============================================
        # POST HANDLER FOR OTP VERIFICATION
        # ============================================
        print("DEBUG: POST request for verify_student_otp")

        # Verify OTP code
        entered_otp = request.POST.get('otp_code')
        pending_student_id = request.session.get('pending_student_id')

        print(f"DEBUG: Entered OTP: {entered_otp}")
        print(f"DEBUG: Pending student ID: {pending_student_id}")

        if not entered_otp:
            print("DEBUG: No OTP provided")
            messages.error(request, 'Please enter the verification code.')
            return redirect('verify_student_otp')

        if not pending_student_id:
            print("DEBUG: No pending student ID in session")
            messages.error(request, 'Session expired. Please register again.')
            return redirect('register_student')

        try:
            # Get fresh instance from database
            student_profile = StudentProfile.objects.get(user_id=pending_student_id)

            # Check if OTP is expired first (60 seconds)
            if student_profile.is_otp_expired():
                print("DEBUG: OTP expired")
                messages.error(
                    request,
                    'Verification code has expired. Please request a new code using the "Resend Code" link.'
                )
                return redirect('verify_student_otp')

            # Then check if OTP is correct
            print(f"DEBUG: Stored OTP: {student_profile.otp_code}")
            print(f"DEBUG: Entered OTP: {entered_otp}")

            if student_profile.otp_code == entered_otp:
                print("DEBUG: OTP matched!")

                # OTP verified successfully
                student_profile.is_verified = True
                student_profile.otp_code = None
                student_profile.otp_created_at = None
                student_profile.save()
                print(f"DEBUG: Student profile updated - is_verified: {student_profile.is_verified}")

                # Activate the user account
                student_profile.user.is_active = True
                student_profile.user.save()
                print(f"DEBUG: User activated - is_active: {student_profile.user.is_active}")

                # Clear session data
                for key in ['pending_student_id', 'pending_student_email', 'student_otp_resend_count']:
                    if key in request.session:
                        del request.session[key]
                print("DEBUG: Session cleared")

                messages.success(request, 'Account verified successfully! Please log in to continue.')
                print("DEBUG: Redirecting to login page")
                return redirect('login')

            else:
                # OTP is incorrect but still valid (not expired)
                print("DEBUG: OTP mismatch")
                messages.error(request, 'Invalid verification code. Please try again with the same code.')
                return redirect('verify_student_otp')

        except StudentProfile.DoesNotExist:
            print("DEBUG: StudentProfile.DoesNotExist")
            cleanup_pending_student_registration(request)
            messages.error(request, 'Registration session expired. Please register again.')
            return redirect('register_student')
        except Exception as e:
            print(f"DEBUG: Exception in POST handler: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'Error verifying OTP: {str(e)}')
            return redirect('verify_student_otp')


def resend_otp(request):
    """Resend OTP verification code - Maximum 3 attempts allowed"""
    pending_admin_id = request.session.get('pending_admin_id')

    if not pending_admin_id:
        messages.error(request, 'Session expired. Please register again.')
        return redirect('register_administrator')

    try:
        admin_profile = AdminProfile.objects.get(user_id=pending_admin_id)

        if admin_profile.is_verified:
            messages.info(request, 'Your account is already verified.')
            return redirect('admin_dashboard')

        # Check if organization was taken by another verified admin
        verified_admin_exists = AdminProfile.objects.filter(
            organization_name=admin_profile.organization_name,
            is_verified=True
        ).exclude(id=admin_profile.id).exists()

        if verified_admin_exists:
            messages.error(
                request,
                f'This organization "{admin_profile.organization_name}" has been assigned to another administrator. Please register with a different organization.'
            )
            # Clean up this registration
            cleanup_pending_registration(request)
            return redirect('register_administrator')

        # Check OTP resend attempt count
        otp_resend_count = request.session.get('otp_resend_count', 0)

        if otp_resend_count >= 3:
            messages.error(
                request,
                'Maximum OTP resend attempts (3) reached. Please register again.'
            )
            # Clean up this registration
            cleanup_pending_registration(request)
            return redirect('register_administrator')

        # Generate and send new OTP (this creates a new OTP with fresh timestamp)
        email_sent = send_otp_email(admin_profile, request)

        if email_sent:
            # Increment resend counter
            otp_resend_count += 1
            request.session['otp_resend_count'] = otp_resend_count

            attempts_remaining = 3 - otp_resend_count
            messages.success(
                request,
                f'New verification code sent! Please check your email. ({attempts_remaining} attempts remaining)'
            )

            # Force session save to ensure counter is updated
            request.session.modified = True

        else:
            messages.error(request, 'Failed to send verification code. Please try again.')

        # Always redirect back to verify OTP page with resend parameter
        return redirect('verify_otp')

    except AdminProfile.DoesNotExist:
        cleanup_pending_registration(request)
        messages.error(request, 'Admin profile not found. Please register again.')
        return redirect('register_administrator')


def resend_student_otp(request):
    """Resend OTP verification code for students - Maximum 3 attempts allowed"""
    pending_student_id = request.session.get('pending_student_id')

    if not pending_student_id:
        messages.error(request, 'Session expired. Please register again.')
        return redirect('register_student')

    try:
        student_profile = StudentProfile.objects.get(user_id=pending_student_id)

        if student_profile.is_verified:
            messages.info(request, 'Your account is already verified.')
            return redirect('student_dashboard')

        # Check OTP resend attempt count
        otp_resend_count = request.session.get('student_otp_resend_count', 0)

        if otp_resend_count >= 3:
            messages.error(
                request,
                'Maximum OTP resend attempts (3) reached. Please register again.'
            )
            # Clean up this registration
            cleanup_pending_student_registration(request)
            return redirect('register_student')

        # Generate and send new OTP (this creates a new OTP with fresh timestamp)
        email_sent = send_student_otp_email(student_profile, request)

        if email_sent:
            # Increment resend counter
            otp_resend_count += 1
            request.session['student_otp_resend_count'] = otp_resend_count

            attempts_remaining = 3 - otp_resend_count
            messages.success(
                request,
                f'New verification code sent! Please check your email. ({attempts_remaining} attempts remaining)'
            )

            # Force session save to ensure counter is updated
            request.session.modified = True

        else:
            messages.error(request, 'Failed to send verification code. Please try again.')

        # Always redirect back to verify OTP page with resend parameter
        return redirect('verify_student_otp')

    except StudentProfile.DoesNotExist:
        cleanup_pending_student_registration(request)
        messages.error(request, 'Student profile not found. Please register again.')
        return redirect('register_student')