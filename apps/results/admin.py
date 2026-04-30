from django.contrib import admin
from .models import ElectionResult, Image, Video, Comment, LiveStreamSession


@admin.register(ElectionResult)
class ElectionResultAdmin(admin.ModelAdmin):
    list_display = ['election', 'polling_unit', 'party', 'vote_count', 'submitted_at']
    list_filter = ['election', 'party', 'submitted_at']
    search_fields = ['polling_unit__name', 'polling_unit__unit_id']
    ordering = ['-submitted_at']
    readonly_fields = ['submitted_at', 'updated_at']


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['election', 'polling_unit', 'uploaded_at']
    list_filter = ['election', 'uploaded_at']
    search_fields = ['polling_unit__name', 'polling_unit__unit_id']
    ordering = ['-uploaded_at']
    readonly_fields = ['uploaded_at']


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['election', 'polling_unit', 'uploaded_at']
    list_filter = ['election', 'uploaded_at']
    search_fields = ['polling_unit__name', 'polling_unit__unit_id']
    ordering = ['-uploaded_at']
    readonly_fields = ['uploaded_at']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['election', 'polling_unit', 'created_at']
    list_filter = ['election', 'created_at']
    search_fields = ['polling_unit__name', 'polling_unit__unit_id']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(LiveStreamSession)
class LiveStreamSessionAdmin(admin.ModelAdmin):
    list_display = ['polling_unit', 'election', 'is_active', 'started_at', 'ended_at', 'duration_seconds']
    list_filter = ['election', 'is_active', 'started_at']
    search_fields = ['polling_unit__name', 'polling_unit__unit_id']
    ordering = ['-started_at']
    readonly_fields = ['id', 'started_at', 'duration_seconds']
    
    fieldsets = (
        ('Stream Information', {
            'fields': ('id', 'election', 'polling_unit', 'is_active')
        }),
        ('URLs', {
            'fields': ('stream_url', 'thumbnail_url')
        }),
        ('Timing', {
            'fields': ('started_at', 'ended_at', 'duration_seconds')
        }),
    )
