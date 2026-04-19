"""
Models for managing Elections and Parties.
"""
import uuid
from django.db import models
from django.utils import timezone


class Party(models.Model):
    """Political Parties"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    acronym = models.CharField(max_length=20, blank=True, default='')
    logo = models.ImageField(upload_to='party_logos/', blank=True, null=True)
    is_starred = models.BooleanField(default=False)  # Only one can be starred
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Ensure only one party is starred
        if self.is_starred:
            Party.objects.exclude(pk=self.pk).update(is_starred=False)
        super().save(*args, **kwargs)


class Election(models.Model):
    """Elections being monitored"""
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('active', 'Active'),
        ('ended', 'Ended'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)  # e.g., "2027 Abia Governorship election"
    election_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-election_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['election_date']),
        ]

    def __str__(self):
        return f"{self.name} ({self.status})"

    def check_and_update_status(self):
        """
        Check if election date has passed and update status.
        This should be called periodically or before retrieving elections.
        """
        now = timezone.now()
        if self.status == 'upcoming' and now >= self.election_date:
            self.status = 'active'
            self.save(update_fields=['status', 'updated_at'])


class ElectionParty(models.Model):
    """Junction table linking Elections to Parties"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='election_parties')
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name='election_parties')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['election', 'party']  # Each party appears once per election
        ordering = ['election', 'party']

    def __str__(self):
        return f"{self.party.name} in {self.election.name}"
