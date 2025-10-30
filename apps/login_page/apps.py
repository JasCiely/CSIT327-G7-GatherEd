from django.apps import AppConfig

class LoginPageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.login_page'

    def ready(self):
        from . import tasks
        tasks.start()
