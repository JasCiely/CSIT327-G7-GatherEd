# apps/cleanup_inactive_sessions.py
from datetime import timedelta
from django.utils import timezone
from django.contrib.sessions.models import Session

def cleanup_inactive_sessions():
    """Delete all expired sessions from the database."""
    cutoff = timezone.now() - timedelta(hours=6)
    deleted, _ = Session.objects.filter(expire_date__lt=cutoff).delete()
    print(f"[Cleanup] Deleted {deleted} expired sessions older than 6 hours.")
