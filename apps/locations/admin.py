from django.contrib import admin
from .models import LGA, Ward, PollingUnit


@admin.register(LGA)
class LGAAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    ordering = ['name']


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ['name', 'lga', 'created_at']
    list_filter = ['lga']
    search_fields = ['name']
    ordering = ['lga', 'name']


@admin.register(PollingUnit)
class PollingUnitAdmin(admin.ModelAdmin):
    list_display = ['unit_id', 'name', 'ward', 'lga', 'is_active', 'created_at']
    list_filter = ['lga', 'ward', 'is_active', 'created_at']
    search_fields = ['unit_id', 'name']
    ordering = ['unit_id']
    readonly_fields = ['unit_id', 'created_at', 'updated_at']
