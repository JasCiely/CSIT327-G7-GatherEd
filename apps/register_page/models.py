from django.db import models
from django.contrib.auth.models import User

class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    cit_id = models.CharField(max_length=15, unique=True, db_column='cit_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admins'

    def __str__(self):
        return self.name

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    cit_id = models.CharField(max_length=15, unique=True, db_column='cit_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'students'

    def __str__(self):
        return self.name