from django.db import models
import uuid

from apps.admin_dashboard_page.models import Event
from apps.register_page.models import StudentProfile

class Registration(models.Model):
    STATUS_CHOICES = [
        ('REGISTERED', 'Registered'),
        ('ATTENDED', 'Attended'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        db_column='student_id',
        related_name='registrations'
    )

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        db_column='event_id',
        related_name='registrations'
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='REGISTERED'
    )

    registered_at = models.DateTimeField(auto_now_add=True)
    attended_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    @property
    def student_name(self):
        return self.student.name

    @property
    def event_title(self):
        return self.event.title

    class Meta:
        db_table = 'registrations'
        unique_together = ('student', 'event')

    def __str__(self):
        return f"{self.student_name} - {self.event_title} ({self.status})"

class Feedback(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        db_column='student_id',
        related_name='feedback_submissions'
    )

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        db_column='event_id',
        related_name='feedback'
    )

    rating = models.IntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        null=True, blank=True
    )
    comments = models.TextField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    @property
    def student_name(self):
        return self.student.name

    @property
    def event_title(self):
        return self.event.title

    class Meta:
        db_table = 'feedback'
        unique_together = ('student', 'event')

    def __str__(self):
        return f"Feedback for {self.event_title} by {self.student_name}"