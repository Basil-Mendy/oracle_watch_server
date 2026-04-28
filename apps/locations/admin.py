from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import LGA, Ward, PollingUnit
from .resources import LGAResource, WardResource, PollingUnitResource


@admin.register(LGA)
class LGAAdmin(ImportExportModelAdmin):
    resource_class = LGAResource
    list_display = ['name', 'acronym', 'created_at']
    ordering = ['name']


@admin.register(Ward)
class WardAdmin(ImportExportModelAdmin):
    resource_class = WardResource
    list_display = ['name', 'lga', 'created_at']
    list_filter = ['lga']
    search_fields = ['name']
    ordering = ['lga', 'name']


@admin.register(PollingUnit)
class PollingUnitAdmin(ImportExportModelAdmin):
    resource_class = PollingUnitResource
    list_display = ['unit_id', 'name', 'ward', 'lga', 'is_active', 'created_at']
    list_filter = ['lga', 'ward', 'is_active', 'created_at']
    search_fields = ['unit_id', 'name']
    ordering = ['unit_id']
    readonly_fields = ['unit_id', 'created_at', 'updated_at']
