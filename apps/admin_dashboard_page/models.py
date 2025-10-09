from django.db import models
from django.contrib.auth.models import User
import uuid
from apps.register_page.models import AdminProfile


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    admin = models.ForeignKey(
        AdminProfile,
        on_delete=models.CASCADE,
        db_column='admin_id',
        related_name='created_events'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    date = models.DateField()
    location = models.CharField(max_length=255, null=True, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    max_attendees = models.IntegerField(null=True, blank=True)
    picture_url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'events'

    def __str__(self):
        return self.title