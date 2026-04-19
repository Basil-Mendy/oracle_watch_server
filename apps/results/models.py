"""
Models for storing election results, images, videos, and comments.
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator
from apps.locations.models import PollingUnit
from apps.elections.models import Election, Party


class ElectionResult(models.Model):
    """Vote counts submitted by polling units"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='results')
    polling_unit = models.ForeignKey(PollingUnit, on_delete=models.CASCADE, related_name='results')
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='results')
    vote_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['election', 'polling_unit', 'party']
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['election', 'polling_unit']),
            models.Index(fields=['election', 'party']),
        ]

    def __str__(self):
        return f"{self.party.name} - {self.polling_unit.name}: {self.vote_count} votes"


class Image(models.Model):
    """Images uploaded by polling unit agents (max 10 per polling unit per election)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='images')
    polling_unit = models.ForeignKey(PollingUnit, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='election_images/%Y/%m/%d/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.CharField(max_length=100)  # Polling unit ID or name

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['election', 'polling_unit']),
        ]

    def __str__(self):
        return f"Image from {self.polling_unit.name} - {self.election.name}"


class Video(models.Model):
    """Videos uploaded by polling unit agents"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='videos')
    polling_unit = models.ForeignKey(PollingUnit, on_delete=models.CASCADE, related_name='videos')
    video = models.FileField(upload_to='election_videos/%Y/%m/%d/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.CharField(max_length=100)  # Polling unit ID or name

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['election', 'polling_unit']),
        ]

    def __str__(self):
        return f"Video from {self.polling_unit.name} - {self.election.name}"


class Comment(models.Model):
    """Comments/notes added by polling unit agents"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='comments')
    polling_unit = models.ForeignKey(PollingUnit, on_delete=models.CASCADE, related_name='comments')
    comment_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100)  # Polling unit ID or name

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['election', 'polling_unit']),
        ]

    def __str__(self):
        return f"Comment from {self.polling_unit.name} - {self.election.name}"
