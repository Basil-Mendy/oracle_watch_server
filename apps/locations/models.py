"""
Models for managing LGAs, Wards, and Polling Units.
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string


class LGA(models.Model):
    """Local Government Area - 17 hardcoded in Abia State"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    acronym = models.CharField(max_length=10, blank=True, default='')  # e.g., "ABU", "OBI", "ANI"
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'LGA'
        verbose_name_plural = 'LGAs'

    def __str__(self):
        return self.name


class Ward(models.Model):
    """Wards within each LGA"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    lga = models.ForeignKey(LGA, on_delete=models.CASCADE, related_name='wards')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['name', 'lga']  # Ward name must be unique within an LGA
        ordering = ['lga', 'name']

    def __str__(self):
        return f"{self.name} ({self.lga.name})"


class PollingUnit(models.Model):
    """Polling Units within each Ward"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit_id = models.CharField(max_length=20, unique=True, blank=True)  # Auto-generated in save()
    name = models.CharField(max_length=200)
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='polling_units')
    lga = models.ForeignKey(LGA, on_delete=models.CASCADE, related_name='polling_units')
    password = models.CharField(max_length=255, blank=True)  # Auto-generated in save()
    plaintext_password = models.CharField(max_length=20, blank=True, null=True)  # Store plaintext for printing/display
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['unit_id']
        indexes = [
            models.Index(fields=['lga']),
            models.Index(fields=['ward']),
            models.Index(fields=['unit_id']),
        ]

    def __str__(self):
        return f"{self.name} ({self.unit_id})"

    def save(self, *args, **kwargs):
        # Auto-generate unit_id if not provided
        if not self.unit_id:
            # Get the LGA acronym
            lga_acronym = self.lga.acronym
            
            # Use safer approach: order by created_at to avoid race conditions during bulk import
            last_unit = PollingUnit.objects.filter(lga=self.lga).order_by('-created_at').first()
            
            if last_unit and last_unit.unit_id:
                # Extract the number from the last unit_id (format: AB/{LGA_ACRONYM}/PU/{SERIAL})
                last_number = int(last_unit.unit_id.split('/')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            # Format: AB/{LGA_ACRONYM}/PU/{SERIAL}
            self.unit_id = f"AB/{lga_acronym}/PU/{new_number:04d}"
        
        # Auto-generate password if not provided
        if not self.password:
            # Generate a 6-digit random password
            self.plaintext_password = get_random_string(6, allowed_chars='0123456789')
            # Hash it for storage
            self.password = make_password(self.plaintext_password)
        
        super().save(*args, **kwargs)
