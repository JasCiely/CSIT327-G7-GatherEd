# apps/register_page/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from .models import AdminProfile


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Use filter() instead of get() to handle multiple users
            users = User.objects.filter(email=username)

            # Try each user until we find one with matching password
            for user in users:
                if user.check_password(password):
                    # Additional check for admin verification
                    if user.is_staff:
                        try:
                            admin_profile = AdminProfile.objects.get(user=user)
                            if not admin_profile.is_verified:
                                return None  # Admin not verified
                        except AdminProfile.DoesNotExist:
                            return None  # No admin profile found
                    return user

            return None  # No user with matching password

        except Exception:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None