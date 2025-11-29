from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    cit_id = models.CharField(max_length=15, unique=True, db_column='cit_id')
    organization_name = models.CharField(
        max_length=255,
        unique=True,
        db_column='organization_name'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admins'

    def __str__(self):
        return f"{self.name} ({self.organization_name})"

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    cit_id = models.CharField(max_length=15, unique=True, db_column='cit_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'students'

    def __str__(self):
        return self.name

class AdminInvitation(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email = models.EmailField(unique=True)
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    organization_name = models.CharField(max_length=255)

    def is_expired(self):
        return self.expires_at < timezone.now()

    def __str__(self):
        return f"Invite for {self.email} (Used: {self.is_used})"