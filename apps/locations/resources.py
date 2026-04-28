"""
Import/Export Resources for Locations app models
Defines how data is imported and exported for LGA, Ward, and PollingUnit models

Key behavior:
- id (UUID) is auto-generated on import (don't include in Excel)
- created_at/updated_at are auto-generated (don't include in Excel)
- unit_id for PollingUnit is auto-generated if left blank (can override in Excel)
"""
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import LGA, Ward, PollingUnit


class LGAResource(resources.ModelResource):
    """
    Resource for LGA model
    ID and timestamps are auto-generated
    Import only: name, acronym
    """
    class Meta:
        model = LGA
        # Exclude auto-generated fields from import
        fields = ('name', 'acronym')
        export_order = ('id', 'name', 'acronym', 'created_at', 'updated_at')


class WardResource(resources.ModelResource):
    """
    Resource for Ward model
    ID and timestamps are auto-generated
    Import only: name, lga (use LGA name to match)
    """
    lga = fields.Field(
        column_name='lga',
        attribute='lga',
        widget=ForeignKeyWidget(LGA, 'name')
    )

    class Meta:
        model = Ward
        # Exclude auto-generated fields from import
        fields = ('name', 'lga')
        export_order = ('id', 'name', 'lga', 'created_at', 'updated_at')


class PollingUnitResource(resources.ModelResource):
    """
    Resource for PollingUnit model
    ID and timestamps are auto-generated
    unit_id can be auto-generated OR provided in Excel
    
    Import fields:
    - unit_id (optional - auto-generated if blank using pattern: AB/{LGA_ACRONYM}/PU/{COUNT})
    - name
    - ward (use Ward name)
    - lga (use LGA name)
    - password
    - plaintext_password (optional)
    - is_active (default True)
    """
    lga = fields.Field(
        column_name='lga',
        attribute='lga',
        widget=ForeignKeyWidget(LGA, 'name')
    )
    ward = fields.Field(
        column_name='ward',
        attribute='ward',
        widget=ForeignKeyWidget(Ward, 'name')
    )

    class Meta:
        model = PollingUnit
        # Use unit_id as the unique identifier instead of auto-generated UUID id
        import_id_fields = ['unit_id']
        # Exclude auto-generated id and timestamps from import
        fields = ('unit_id', 'name', 'ward', 'lga', 'password', 'plaintext_password', 'is_active')
        export_order = ('id', 'unit_id', 'name', 'ward', 'lga', 'password', 'plaintext_password', 'is_active', 'created_at', 'updated_at')
