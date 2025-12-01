from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random

class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    cit_id = models.CharField(max_length=15, unique=True, db_column='cit_id')
    organization_name = models.CharField(
        max_length=255,
        unique=True,
        db_column='organization_name'
    )
    is_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admins'

    def __str__(self):
        return f"{self.name} ({self.organization_name})"

    def generate_otp(self):
        """Generate 6-digit OTP"""
        self.otp_code = str(random.randint(100000, 999999))
        self.otp_created_at = timezone.now()
        self.save()
        return self.otp_code

    def is_otp_expired(self):
        """Check if OTP is expired (30 seconds)"""
        if not self.otp_created_at:
            return True
        expiration_time = self.otp_created_at + timezone.timedelta(seconds=30)
        return timezone.now() > expiration_time

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    cit_id = models.CharField(max_length=15, unique=True, db_column='cit_id')
    is_verified = models.BooleanField(default=False)  # Add this
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'students'

    def __str__(self):
        return self.name

    def generate_otp(self):
        """Generate 6-digit OTP"""
        self.otp_code = str(random.randint(100000, 999999))
        self.otp_created_at = timezone.now()
        self.save()
        return self.otp_code

    def is_otp_expired(self):  # Add this method
        """Check if OTP is expired (30 seconds)"""
        if not self.otp_created_at:
            return True
        expiration_time = self.otp_created_at + timezone.timedelta(seconds=30)
        return timezone.now() > expiration_time