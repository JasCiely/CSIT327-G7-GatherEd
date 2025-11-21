from django.db import models
import uuid
from apps.register_page.models import AdminProfile

class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

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

    # Picture field with proper configuration
    picture = models.ImageField(
        upload_to='event_pictures/',
        null=True,
        blank=True,
        verbose_name='Event Picture'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    manual_status_override = models.CharField(
        max_length=50,
        choices=[
            ('AUTO', 'Auto'),
            ('OPEN_MANUAL', 'Registration Open (Manual Override)'),
            ('CLOSED_MANUAL', 'Registration Closed (Manual Override)'),
            ('ONGOING', 'Closed – Event Ongoing'),
        ],
        default='AUTO',
        null=False,
        blank=False
    )

    manual_close_date = models.DateField(
        null=True,
        blank=True,
        help_text="The date when the manual override status will expire."
    )

    manual_close_time = models.TimeField(
        null=True,
        blank=True,
        help_text="The time when the manual override status will expire."
    )

    class Meta:
        db_table = 'events'

    @property
    def picture_url(self):
        if self.picture and hasattr(self.picture, 'url'):
            return self.picture.url
        return None

    def __str__(self):
        return self.title