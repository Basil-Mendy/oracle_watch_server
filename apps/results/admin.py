from django.contrib import admin
from .models import ElectionResult, Image, Video, Comment, LiveStreamSession, PendingResultSubmission


@admin.register(PendingResultSubmission)
class PendingResultSubmissionAdmin(admin.ModelAdmin):
    list_display = ['polling_unit', 'election', 'status', 'submitted_at', 'reviewed_by']
    list_filter = ['election', 'status', 'submitted_at']
    search_fields = ['polling_unit__name', 'polling_unit__unit_id', 'reviewed_by']
    ordering = ['-submitted_at']
    readonly_fields = ['id', 'submitted_at', 'reviewed_at', 'vote_data', 'ec8a_form_image']
    
    fieldsets = (
        ('Submission Info', {
            'fields': ('id', 'election', 'polling_unit', 'submitted_at', 'ec8a_form_image')
        }),
        ('Vote Data', {
            'fields': ('vote_data', 'edited_vote_data')
        }),
        ('Status & Review', {
            'fields': ('status', 'reviewed_at', 'reviewed_by', 'admin_notes', 'edit_reason')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status != 'pending':
            return self.readonly_fields + ['election', 'polling_unit', 'vote_data']
        return self.readonly_fields


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
