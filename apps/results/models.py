"""
Models for storing election results, images, videos, and comments.
"""
import uuid
import json
from django.db import models
from django.core.validators import MinValueValidator
from apps.locations.models import PollingUnit
from apps.elections.models import Election, Party


class PendingResultSubmission(models.Model):
    """Stores pending result submissions awaiting admin approval (audit workflow)"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='pending_submissions')
    polling_unit = models.ForeignKey(PollingUnit, on_delete=models.CASCADE, related_name='pending_submissions')
    
    # EC8A form image (optional - can submit votes without image first)
    ec8a_form_image = models.ImageField(upload_to='ec8a_forms/%Y/%m/%d/', null=True, blank=True)
    
    # Vote counts stored as JSON: {"party_id": vote_count}
    vote_data = models.JSONField(default=dict)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Audit trail
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.CharField(max_length=150, null=True, blank=True)  # Admin username
    admin_notes = models.TextField(null=True, blank=True)  # Reason for rejection or approval notes
    
    # Tracking edits made by admin
    edited_vote_data = models.JSONField(null=True, blank=True)  # If admin modified vote counts
    edit_reason = models.TextField(null=True, blank=True)  # Why admin edited

    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['election', 'status']),
            models.Index(fields=['election', 'polling_unit']),
            models.Index(fields=['status', '-submitted_at']),
        ]

    def __str__(self):
        return f"{self.polling_unit.name} - {self.election.name} ({self.status})"


class ElectionResult(models.Model):
    """Vote counts submitted by polling units (approved results only)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='results')
    polling_unit = models.ForeignKey(PollingUnit, on_delete=models.CASCADE, related_name='results')
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='results')
    vote_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Link to approved submission (ForeignKey allows multiple results per submission)
    submission = models.ForeignKey(PendingResultSubmission, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_results')
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)

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


class LiveStreamSession(models.Model):
    """Track active live streaming sessions from polling units"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='live_streams')
    polling_unit = models.ForeignKey(PollingUnit, on_delete=models.CASCADE, related_name='live_streams')
    stream_url = models.URLField(max_length=500, null=True, blank=True)  # URL to the live stream
    thumbnail_url = models.URLField(max_length=500, null=True, blank=True)  # Thumbnail image URL
    is_active = models.BooleanField(default=True)  # Whether stream is currently live
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)  # Duration in seconds

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['election', 'polling_unit']),
            models.Index(fields=['election', 'is_active']),
        ]

    def __str__(self):
        return f"Stream from {self.polling_unit.name} - {self.election.name} ({'active' if self.is_active else 'ended'})"


class RejectionNotification(models.Model):
    """Track result rejections to notify polling units"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.OneToOneField(PendingResultSubmission, on_delete=models.CASCADE, related_name='rejection_notification')
    reason = models.TextField()  # Rejection reason
    rejected_at = models.DateTimeField(auto_now_add=True)
    rejected_by = models.CharField(max_length=150)  # Admin username
    is_read = models.BooleanField(default=False)  # Whether polling unit has seen the notification
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-rejected_at']
        indexes = [
            models.Index(fields=['submission']),
            models.Index(fields=['rejected_at']),
        ]

    def __str__(self):
        return f"Rejection for {self.submission.polling_unit.name} - {self.submission.election.name}"
