from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management import call_command
import atexit


def start():
    scheduler = BackgroundScheduler()

    # Run cleanup command every 6 hours
    scheduler.add_job(
        lambda: call_command("cleanup_supabase_sessions"),
        'interval',
        hours=6,
        id='cleanup_supabase_sessions',
        replace_existing=True
    )

    scheduler.start()
    print("🕒 Scheduler started: will run cleanup_supabase_sessions every 6 hours")

    # Make sure scheduler stops when Django stops
    atexit.register(lambda: scheduler.shutdown(wait=False))
