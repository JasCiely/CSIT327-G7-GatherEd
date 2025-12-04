import uuid

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
        """Check if OTP is expired (10 minutes)"""
        if not self.otp_created_at:
            return True
        expiration_time = self.otp_created_at + timezone.timedelta(seconds=60)
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
        """Check if OTP is expired (10 minutes)"""
        if not self.otp_created_at:
            return True
        expiration_time = self.otp_created_at + timezone.timedelta(seconds=60)
        return timezone.now() > expiration_time

class AccessCodeRequest(models.Model):
    """Model to store access code requests"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('declined', 'Declined'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    cit_id = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField()
    organization_name = models.CharField(max_length=255)
    message = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    access_code = models.CharField(max_length=6, blank=True, null=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.organization_name} ({self.status})"

    def generate_access_code(self):
        """Generate 6-digit access code"""
        self.access_code = str(random.randint(100000, 999999))
        self.save()
        return self.access_code

    class Meta:
        db_table = 'access_code_requests'
        ordering = ['-created_at']


class OrganizationAccessCode(models.Model):
    """Model to store generated access codes for organizations"""
    organization_name = models.CharField(max_length=255)
    access_code = models.CharField(max_length=6, unique=True)
    is_active = models.BooleanField(default=True)
    used_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='created_access_codes')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.organization_name} - {self.access_code}"

    def is_valid(self):
        """Check if access code is still valid"""
        if not self.is_active:
            return False
        if self.used_by:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    class Meta:
        db_table = 'organization_access_codes'