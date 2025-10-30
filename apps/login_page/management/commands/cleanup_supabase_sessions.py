import os
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.sessions.models import Session
from dotenv import load_dotenv
from supabase import create_client, Client
from django.conf import settings


class Command(BaseCommand):
    help = "🧹 Delete expired or inactive sessions from django_session and revoke Supabase tokens."

    def handle(self, *args, **options):
        load_dotenv()

        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            self.stdout.write(self.style.ERROR("❌ Missing Supabase credentials in .env"))
            return

        # Initialize Supabase client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

        inactivity_limit = getattr(settings, "SESSION_INACTIVITY_LIMIT_HOURS", 6)
        cutoff = timezone.now() - timedelta(hours=inactivity_limit)

        self.stdout.write(f"🧹 Starting cleanup of sessions inactive for > {inactivity_limit} hours...")

        expired_sessions = Session.objects.filter(expire_date__lt=cutoff)
        if not expired_sessions.exists():
            self.stdout.write(self.style.SUCCESS("✅ No expired sessions found."))
            return

        deleted_count = 0
        revoked_count = 0

        for session in expired_sessions:
            try:
                data = session.get_decoded()
                supabase_user_id = data.get("supabase_user_id")

                # Try to revoke Supabase session if user_id exists
                if supabase_user_id:
                    try:
                        supabase.auth.admin.sign_out_user(supabase_user_id)
                        revoked_count += 1
                        self.stdout.write(f"🗑️ Revoked Supabase session for user {supabase_user_id}")
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"⚠️ Failed to revoke Supabase user {supabase_user_id}: {e}"))

                # Delete expired session
                session.delete()
                deleted_count += 1

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️ Error decoding/deleting session: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"✅ Done — {deleted_count} Django sessions deleted, {revoked_count} Supabase sessions revoked."
        ))
