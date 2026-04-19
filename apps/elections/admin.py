from django.contrib import admin
from .models import Party, Election, ElectionParty


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_starred', 'created_at']
    list_filter = ['is_starred', 'created_at']
    search_fields = ['name']
    ordering = ['name']


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'election_date', 'status', 'created_at']
    list_filter = ['status', 'election_date', 'created_at']
    search_fields = ['name']
    ordering = ['-election_date']
    readonly_fields = ['created_at', 'updated_at', 'ended_at']


@admin.register(ElectionParty)
class ElectionPartyAdmin(admin.ModelAdmin):
    list_display = ['election', 'party', 'created_at']
    list_filter = ['election', 'party', 'created_at']
    ordering = ['election', 'party']
