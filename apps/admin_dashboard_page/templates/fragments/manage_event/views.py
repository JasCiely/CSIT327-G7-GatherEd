import datetime
import traceback
from uuid import UUID

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction

from apps.admin_dashboard_page.models import Event
from apps.student_dashboard_page.models import Registration


def format_to_readable_date(date_str):
    if not date_str:
        return 'N/A'
    try:
        if isinstance(date_str, datetime.date):
            date_obj = date_str
        else:
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        return date_obj.strftime('%B %d, %Y').lstrip('0')
    except Exception:
        return date_str


def format_to_12hr(time_str):
    if not time_str:
        return ''
    try:
        if isinstance(time_str, datetime.time):
            time_obj = time_str
        else:
            for fmt in ('%H:%M:%S', '%H:%M'):
                try:
                    time_obj = datetime.datetime.strptime(time_str, fmt).time()
                    break
                except ValueError:
                    continue
            else:
                return time_str
        return time_obj.strftime('%I:%M %p').lstrip('0')
    except Exception:
        return time_str


def parse_time(ts):
    if isinstance(ts, datetime.time):
        return ts
    if not ts:
        return datetime.time(0, 0)
    for fmt in ('%H:%M:%S', '%H:%M'):
        try:
            return datetime.datetime.strptime(ts, fmt).time()
        except ValueError:
            continue
    return datetime.time(0, 0)


def get_detailed_event_timing(event_date_str, start_time_str, end_time_str, manual_close_date_str=None,
                              manual_close_time_str=None):
    try:
        if not all([event_date_str, start_time_str]):
            return {'status': 'Unknown'}

        if isinstance(event_date_str, datetime.date):
            event_date = event_date_str
        else:
            event_date = datetime.datetime.strptime(event_date_str, '%Y-%m-%d').date()

        start_time = parse_time(start_time_str)
        default_end_dt = datetime.datetime.combine(event_date, start_time) + datetime.timedelta(hours=2)
        end_time = parse_time(end_time_str) if end_time_str else default_end_dt.time()

        start_dt = datetime.datetime.combine(event_date, start_time)
        end_dt = datetime.datetime.combine(event_date, end_time)
        if end_dt < start_dt:
            end_dt += datetime.timedelta(days=1)

        manual_limit_dt = None
        if manual_close_date_str and manual_close_time_str:
            if isinstance(manual_close_date_str, datetime.date):
                limit_date = manual_close_date_str
            else:
                limit_date = datetime.datetime.strptime(manual_close_date_str, '%Y-%m-%d').date()
            limit_time = parse_time(manual_close_time_str)
            manual_limit_dt = datetime.datetime.combine(limit_date, limit_time)

        now = datetime.datetime.now()
        status = 'Upcoming'
        if now >= end_dt:
            status = 'Completed'
        elif now >= start_dt:
            status = 'Active'

        return {
            'status': status,
            'start_dt': start_dt,
            'end_dt': end_dt,
            'manual_limit_dt': manual_limit_dt,
            'event_date_str': event_date.strftime('%Y-%m-%d'),
            'event_date': event_date,
        }

    except Exception:
        traceback.print_exc()
        return {'status': 'Unknown'}


def get_event_status(event_date_str, start_time_str, end_time_str):
    return get_detailed_event_timing(event_date_str, start_time_str, end_time_str).get('status', 'Unknown')


def determine_registration_status(event_data):
    manual = (event_data.get('manual_status_override') or 'AUTO').upper()
    max_attendees = event_data.get('max_attendees') or 0
    current_regs = event_data.get('current_registrations', 0)

    timing = get_detailed_event_timing(
        event_data.get('date'),
        event_data.get('start_time'),
        event_data.get('end_time'),
        event_data.get('manual_close_date'),
        event_data.get('manual_close_time')
    )
    event_status = timing['status']
    now = datetime.datetime.now()

    # Bisaya: check manual override validity
    if manual in ['OPEN_MANUAL', 'CLOSED_MANUAL']:
        limit_dt = timing.get('manual_limit_dt')
        if limit_dt and now >= limit_dt:
            manual = 'AUTO'
        else:
            if manual == 'OPEN_MANUAL':
                return 'Available'
            if manual == 'CLOSED_MANUAL':
                return 'Registration Closed'

    if manual == 'FULL':
        return 'Full'
    if manual == 'ONGOING':
        return 'Closed – Event Ongoing'

    if event_status == 'Completed':
        return 'Registration Closed'

    if event_status == 'Active':
        if max_attendees and current_regs >= max_attendees:
            return 'Full'
        else:
            return 'Closed – Event Ongoing'

    if max_attendees and current_regs >= max_attendees:
        return 'Full'

    return 'Available'


def fetch_single_event(event_id):
    try:
        event = Event.objects.select_related('admin').get(pk=event_id)
        current_regs = Registration.objects.filter(event=event).exclude(status='CANCELLED').count()
        return {
            'id': str(event.id),
            'title': event.title,
            'description': event.description or '',
            'location': event.location or '',
            'date': event.date,
            'start_time': event.start_time,
            'end_time': event.end_time,
            'max_attendees': event.max_attendees or 0,
            'manual_status_override': event.manual_status_override or 'AUTO',
            'manual_close_date': event.manual_close_date,
            'manual_close_time': event.manual_close_time,
            'current_registrations': current_regs,
        }
    except Exception:
        traceback.print_exc()
        return None


def _fetch_single_event(event_id):
    try:
        event = Event.objects.get(pk=event_id)
        current_registrations_count = Registration.objects.filter(event=event).exclude(status='CANCELLED').count()

        data = {
            'id': str(event.id),
            'title': event.title,
            'description': event.description or 'No description provided.',
            'date': event.date.strftime('%Y-%m-%d') if event.date else '',
            'location': event.location or 'N/A',
            'start_time': event.start_time.isoformat() if event.start_time else '',
            'end_time': event.end_time.isoformat() if event.end_time else '',
            'max_attendees': event.max_attendees or 0,
            'current_registrations': current_registrations_count,
            'manual_status_override': event.manual_status_override or 'AUTO',
            'manual_close_date': (event.manual_close_date.strftime('%Y-%m-%d') if event.manual_close_date else ''),
            'manual_close_time': (event.manual_close_time.isoformat() if event.manual_close_time else ''),
        }

        registration_status = determine_registration_status(data)
        event_status = get_event_status(data.get('date'), data.get('start_time'), data.get('end_time'))

        return {
            'id': str(event.id),
            'name': event.title or 'N/A',
            'description': event.description or 'No description provided.',
            'date': format_to_readable_date(data.get('date')),
            'location': data.get('location', 'N/A'),
            'start_time': format_to_12hr(data.get('start_time')),
            'end_time': format_to_12hr(data.get('end_time')),
            'max_attendees': data.get('max_attendees', 0) or 0,
            'registrations': current_registrations_count,
            'status': registration_status,
            'raw_date': data.get('date', ''),
            'raw_start_time': data.get('start_time', ''),
            'raw_end_time': data.get('end_time', ''),
            'event_status': event_status,
            'manual_close_date': data.get('manual_close_date', ''),
            'manual_close_time': data.get('manual_close_time', ''),
        }

    except Exception:
        traceback.print_exc()
        return None


def get_registration_status(event_data):
    return determine_registration_status(event_data)


@login_required
def manage_events(request):
    is_ajax = request.GET.get('is_ajax') == 'true'
    admin_profile = getattr(request.user, 'adminprofile', None)
    if not admin_profile:
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'Admin profile not found'}, status=403)
        return redirect('/admin_dashboard/')

    cache_key = f"events_{admin_profile.id}"
    events_list = cache.get(cache_key)

    if events_list is None:
        events_list = []
        try:
            qs = Event.objects.filter(admin=admin_profile).order_by('date')
            for ev in qs:
                ev_raw = {
                    'id': str(ev.id),
                    'date': ev.date.strftime('%Y-%m-%d') if ev.date else '',
                    'start_time': ev.start_time.isoformat() if ev.start_time else '',
                    'end_time': ev.end_time.isoformat() if ev.end_time else '',
                    'manual_close_date': ev.manual_close_date.strftime('%Y-%m-%d') if ev.manual_close_date else '',
                    'manual_close_time': ev.manual_close_time.isoformat() if ev.manual_close_time else '',
                    'manual_status_override': ev.manual_status_override or 'AUTO',
                    'max_attendees': ev.max_attendees or 0,
                    'current_registrations': Registration.objects.filter(event=ev).exclude(status='CANCELLED').count(),
                }

                event_status = get_event_status(ev_raw['date'], ev_raw['start_time'], ev_raw['end_time'])
                registration_status = determine_registration_status(ev_raw)

                events_list.append({
                    'id': str(ev.id),
                    'name': ev.title or 'N/A',
                    'description': ev.description or 'N/A',
                    'date': format_to_readable_date(ev.date),
                    'location': ev.location or 'N/A',
                    'start_time': format_to_12hr(ev.start_time),
                    'end_time': format_to_12hr(ev.end_time),
                    'event_status': event_status,
                    'registration_status': registration_status,
                    'registrations': ev_raw['current_registrations'],
                    'max_attendees': ev_raw['max_attendees'],
                })

            cache.set(cache_key, events_list, timeout=60)

        except Exception as e:
            traceback.print_exc()

    context = {'events_list': events_list, 'title': 'Manage Events'}

    if is_ajax:
        return render(request, 'fragments/manage_event/manage_events_content.html', context)

    return redirect('/admin_dashboard/')


@login_required
def get_event_details_html(request, event_id):
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return HttpResponse("Unauthorized", status=403)

    try:
        event_data = _fetch_single_event(event_id)
        if not event_data:
            return HttpResponse(
                '<div style="color: red; padding: 20px;">Error 404: Event not found.</div>',
                status=404)

        return render(request, 'fragments/manage_event/event_details_fragment.html', {'event': event_data})

    except Exception:
        return HttpResponse(
            '<div style="color: red; padding: 20px;">Error 500: Server failed to load details.</div>',
            status=500)


@login_required
@require_http_methods(["DELETE"])
def delete_event(request, event_id):
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Unauthorized: Not an AJAX request'}, status=403)

    admin_profile = getattr(request.user, 'adminprofile', None)
    if not admin_profile:
        return JsonResponse({'success': False, 'error': 'Admin profile not found'}, status=403)

    try:
        deleted_count, _ = Event.objects.filter(id=event_id, admin=admin_profile).delete()
        if deleted_count == 0:
            return JsonResponse({'success': False, 'error': 'Event not found or unauthorized to delete.'}, status=404)

        cache.delete(f"events_{admin_profile.id}")
        return JsonResponse({'success': True})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def modify_event_root(request, event_id):
    if request.GET.get('is_ajax') != 'true':
        return JsonResponse({'error': 'Must be AJAX'}, status=400)

    admin_profile = getattr(request.user, 'adminprofile', None)
    if not admin_profile:
        return JsonResponse({'success': False, 'error': 'Admin profile not found'}, status=403)

    try:
        event = Event.objects.get(pk=event_id, admin=admin_profile)
    except Event.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Event not found or unauthorized'}, status=404)

    event_data = {
        'date': event.date.strftime('%Y-%m-%d') if event.date else '',
        'start_time': event.start_time.isoformat() if event.start_time else '',
        'end_time': event.end_time.isoformat() if event.end_time else '',
        'manual_close_date': event.manual_close_date.strftime('%Y-%m-%d') if event.manual_close_date else '',
        'manual_close_time': event.manual_close_time.isoformat() if event.manual_close_time else '',
        'manual_status_override': event.manual_status_override,
        'current_registrations': Registration.objects.filter(event=event).exclude(status='CANCELLED').count(),
        'max_attendees': event.max_attendees or 0,
    }

    timing = get_detailed_event_timing(
        event_data.get('date'), event_data.get('start_time'), event_data.get('end_time'),
        event_data.get('manual_close_date'), event_data.get('manual_close_time')
    )
    event_life_status = timing['status']

    if request.method == 'POST':
        manual_status = (request.POST.get('manual_status_override') or 'AUTO').upper()
        manual_close_date = request.POST.get('manual_close_date') or None
        manual_close_time = request.POST.get('manual_close_time') or None

        if manual_status in ['AUTO', 'ONGOING']:
            manual_close_date = None
            manual_close_time = None

        try:
            max_attendees_val = int(request.POST.get('max_attendees') or 0)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'max_attendees must be an integer'}, status=400)

        update_fields = {
            'title': request.POST.get('title'),
            'description': request.POST.get('description'),
            'location': request.POST.get('location'),
            'date': request.POST.get('date'),
            'start_time': request.POST.get('start_time'),
            'end_time': request.POST.get('end_time') or None,
            'max_attendees': max_attendees_val,
            'manual_status_override': manual_status,
            'manual_close_date': manual_close_date,
            'manual_close_time': manual_close_time,
        }

        timing_post = get_detailed_event_timing(
            update_fields['date'], update_fields['start_time'], update_fields['end_time'],
            manual_close_date, manual_close_time
        )
        event_life_status_post = timing_post['status']
        manual_limit_dt = timing_post.get('manual_limit_dt')

        if event_life_status_post == 'Completed' and manual_status != event.manual_status_override:
            if manual_status not in ['AUTO']:
                return JsonResponse(
                    {'success': False, 'error': "Cannot manually override registration status for a completed event."},
                    status=400)

        current_regs = Registration.objects.filter(event=event).exclude(status='CANCELLED').count()
        if update_fields['max_attendees'] != 0 and update_fields['max_attendees'] < current_regs:
            return JsonResponse({'success': False,
                                 'error': f"Max attendees ({update_fields['max_attendees']}) cannot be less than current registrations ({current_regs})."},
                                status=400)

        if manual_status in ['OPEN_MANUAL', 'CLOSED_MANUAL']:
            validation_error = None
            if manual_limit_dt:
                if manual_limit_dt > timing_post['end_dt']:
                    validation_error = "The manual override limit cannot be set after the event has ended."
                elif event_life_status_post == 'Upcoming' and manual_status == 'CLOSED_MANUAL':
                    if manual_limit_dt >= timing_post['start_dt']:
                        validation_error = "Closing limit must be before the event starts."
                elif event_life_status_post == 'Active' and manual_status == 'OPEN_MANUAL':
                    if manual_limit_dt.date() != timing_post['event_date']:
                        validation_error = "Reopening limit date must be the same as the event date."
                    elif not (manual_limit_dt > timing_post['start_dt'] and manual_limit_dt <= timing_post['end_dt']):
                        validation_error = "Reopening limit time must be during the event duration (after start, on or before end)."

            if validation_error:
                return JsonResponse({'success': False, 'error': f"Validation Error: {validation_error}"}, status=400)

        try:
            with transaction.atomic():
                if update_fields['title'] is not None:
                    event.title = update_fields['title']
                event.description = update_fields['description']
                event.location = update_fields['location']

                if update_fields['date']:
                    try:
                        event.date = datetime.datetime.strptime(update_fields['date'], '%Y-%m-%d').date()
                    except Exception:
                        return JsonResponse({'success': False, 'error': 'Invalid date format (expected YYYY-MM-DD).'}, status=400)
                if update_fields['start_time']:
                    try:
                        event.start_time = parse_time(update_fields['start_time'])
                    except Exception:
                        return JsonResponse({'success': False, 'error': 'Invalid start_time format.'}, status=400)
                if update_fields['end_time']:
                    try:
                        event.end_time = parse_time(update_fields['end_time'])
                    except Exception:
                        return JsonResponse({'success': False, 'error': 'Invalid end_time format.'}, status=400)
                else:
                    event.end_time = None

                event.max_attendees = update_fields['max_attendees']
                event.manual_status_override = update_fields['manual_status_override'] or 'AUTO'

                if manual_close_date:
                    try:
                        event.manual_close_date = datetime.datetime.strptime(manual_close_date, '%Y-%m-%d').date()
                    except Exception:
                        return JsonResponse({'success': False, 'error': 'Invalid manual_close_date format (YYYY-MM-DD).'}, status=400)
                else:
                    event.manual_close_date = None

                if manual_close_time:
                    try:
                        event.manual_close_time = parse_time(manual_close_time)
                    except Exception:
                        return JsonResponse({'success': False, 'error': 'Invalid manual_close_time format.'}, status=400)
                else:
                    event.manual_close_time = None

                event.save()
                cache.delete(f"events_{admin_profile.id}")

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': f"Failed to save changes: {str(e)}"}, status=500)

        current_regs_after = Registration.objects.filter(event=event).exclude(status='CANCELLED').count()

        event_data_for_status = {
            'manual_status_override': event.manual_status_override,
            'max_attendees': event.max_attendees or 0,
            'current_registrations': current_regs_after,
            'date': event.date.strftime('%Y-%m-%d') if event.date else '',
            'start_time': event.start_time.isoformat() if event.start_time else '',
            'end_time': event.end_time.isoformat() if event.end_time else '',
            'manual_close_date': event.manual_close_date.strftime('%Y-%m-%d') if event.manual_close_date else '',
            'manual_close_time': event.manual_close_time.isoformat() if event.manual_close_time else '',
        }

        final_registration_status = determine_registration_status(event_data_for_status)
        final_event_status = get_event_status(event_data_for_status['date'], event_data_for_status['start_time'],
                                              event_data_for_status['end_time'])

        return JsonResponse({
            'success': True,
            'updated_data': {
                'id': str(event.id),
                'name': event.title,
                'date': format_to_readable_date(event.date),
                'status': final_registration_status,
                'event_status': final_event_status,
                'registrations': current_regs_after,
            }
        })

    if request.method == 'GET':
        event_data_context = fetch_single_event(event_id)
        if not event_data_context:
            return JsonResponse({'success': False, 'error': 'Event not found'}, status=404)

        event_life_status_context = get_event_status(
            event_data_context.get('date'), event_data_context.get('start_time'), event_data_context.get('end_time')
        )

        date_str = event.date.strftime('%Y-%m-%d') if event.date else ''
        start_time_str = event.start_time.strftime('%H:%M') if event.start_time else ''
        end_time_str = event.end_time.strftime('%H:%M') if event.end_time else ''
        manual_close_date_str = event.manual_close_date.strftime('%Y-%m-%d') if event.manual_close_date else ''
        manual_close_time_str = event.manual_close_time.strftime('%H:%M') if event.manual_close_time else ''

        context = {
            'event': {
                'id': event_data_context['id'],
                'title': event.title,
                'description': event.description,
                'location': event.location,
                'max_attendees': event.max_attendees,
                'manual_status_override': event.manual_status_override,
                'current_registrations': Registration.objects.filter(event=event).exclude(status='CANCELLED').count(),
            },
            'current_date': date_str,
            'current_start_time': start_time_str,
            'current_end_time': end_time_str,
            'current_manual_close_date': manual_close_date_str,
            'current_manual_close_time': manual_close_time_str,
            'is_completed': event_life_status_context == 'Completed',
        }
        html_content = render_to_string('fragments/manage_event/modify_event_form.html', context, request=request)
        return JsonResponse({'success': True, 'html': html_content})
