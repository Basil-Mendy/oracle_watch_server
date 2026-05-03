"""
Serializers for the results app - converts ElectionResult, Image, Video, Comment models to/from JSON
"""
from rest_framework import serializers
from .models import ElectionResult, Image, Video, Comment, LiveStreamSession


class WardSerializer(serializers.Serializer):
    """Simple serializer for Ward"""
    id = serializers.IntegerField()
    name = serializers.CharField()


class LGASerializer(serializers.Serializer):
    """Simple serializer for LGA"""
    id = serializers.IntegerField()
    name = serializers.CharField()


class PollingUnitNestedSerializer(serializers.Serializer):
    """Nested serializer for PollingUnit with ward and lga details"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    unit_id = serializers.CharField()
    ward = WardSerializer()
    lga = LGASerializer()


class ElectionResultSerializer(serializers.ModelSerializer):
    """Serializer for ElectionResult model"""
    party_name = serializers.CharField(source='party.name', read_only=True)
    polling_unit_name = serializers.CharField(source='polling_unit.name', read_only=True)
    
    class Meta:
        model = ElectionResult
        fields = [
            'id', 'election', 'polling_unit', 'polling_unit_name',
            'party', 'party_name', 'vote_count', 'submitted_at'
        ]
        read_only_fields = ['id', 'submitted_at']


class ImageSerializer(serializers.ModelSerializer):
    """Serializer for Image model"""
    image_url = serializers.SerializerMethodField()
    polling_unit = PollingUnitNestedSerializer(read_only=True)
    
    class Meta:
        model = Image
        fields = ['id', 'election', 'polling_unit', 'image', 'image_url', 'uploaded_at', 'uploaded_by']
        read_only_fields = ['id', 'uploaded_at']
    
    def get_image_url(self, obj):
        """Get the full URL to the image"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
        return None


class VideoSerializer(serializers.ModelSerializer):
    """Serializer for Video model with support for direct Cloudinary uploads"""
    video_url = serializers.SerializerMethodField()
    streaming_url = serializers.SerializerMethodField()
    polling_unit = PollingUnitNestedSerializer(read_only=True)
    duration_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = Video
        fields = [
            'id', 'election', 'polling_unit', 
            'video', 'video_url',
            'cloudinary_url', 'streaming_url',
            'duration', 'duration_formatted',
            'segment_id', 'recording_timestamp',
            'metadata', 'is_live_stream',
            'uploaded_at', 'uploaded_by'
        ]
        read_only_fields = ['id', 'uploaded_at', 'video_url', 'streaming_url', 'duration_formatted']
    
    def get_video_url(self, obj):
        """Get the full URL to the local video file (if available)"""
        if obj.video:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.video.url)
        return None
    
    def get_streaming_url(self, obj):
        """Get the streaming URL (prioritize Cloudinary URL for direct streaming)"""
        if obj.cloudinary_url:
            # Return Cloudinary URL optimized for streaming
            return obj.cloudinary_url.replace('/upload/', '/upload/q_auto,f_auto/')
        elif obj.video:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.video.url)
        return None
    
    def get_duration_formatted(self, obj):
        """Format duration as MM:SS"""
        if not obj.duration:
            return None
        total_seconds = obj.duration // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"



class CommentSerializer(serializers.ModelSerializer):
    """Serializer for Comment model"""
    polling_unit = PollingUnitNestedSerializer(read_only=True)
    
    class Meta:
        model = Comment
        fields = [
            'id', 'election', 'polling_unit',
            'comment_text', 'created_at', 'created_by', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LiveStreamSessionSerializer(serializers.ModelSerializer):
    """Serializer for LiveStreamSession model"""
    polling_unit = PollingUnitNestedSerializer(read_only=True)
    polling_unit_id = serializers.SerializerMethodField()
    polling_unit_name = serializers.SerializerMethodField()
    lga_name = serializers.SerializerMethodField()
    ward_name = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = LiveStreamSession
        fields = [
            'id', 'election', 'polling_unit', 'polling_unit_id', 'polling_unit_name',
            'lga_name', 'ward_name', 'stream_url', 'thumbnail_url',
            'is_active', 'started_at', 'ended_at', 'duration', 'duration_seconds'
        ]
        read_only_fields = ['id', 'started_at']
    
    def get_polling_unit_id(self, obj):
        """Get polling unit ID"""
        return obj.polling_unit.unit_id if obj.polling_unit else None
    
    def get_polling_unit_name(self, obj):
        """Get polling unit name"""
        return obj.polling_unit.name if obj.polling_unit else None
    
    def get_lga_name(self, obj):
        """Get LGA name"""
        return obj.polling_unit.lga.name if obj.polling_unit and obj.polling_unit.lga else None
    
    def get_ward_name(self, obj):
        """Get ward name"""
        return obj.polling_unit.ward.name if obj.polling_unit and obj.polling_unit.ward else None
    
    def get_duration(self, obj):
        """Get formatted duration (HH:MM:SS)"""
        seconds = obj.duration_seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class AllResultsSerializer(serializers.Serializer):
    """
    Serializer for aggregated results from a polling unit for an election.
    Combines vote counts, images, videos, and comments.
    """
    votes = ElectionResultSerializer(many=True)
    images = ImageSerializer(many=True)
    videos = VideoSerializer(many=True)
    comments = CommentSerializer(many=True)
