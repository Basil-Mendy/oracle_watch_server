"""
Serializers for the results app - converts ElectionResult, Image, Video, Comment models to/from JSON
"""
from rest_framework import serializers
from .models import ElectionResult, Image, Video, Comment


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
    """Serializer for Video model"""
    video_url = serializers.SerializerMethodField()
    polling_unit = PollingUnitNestedSerializer(read_only=True)
    
    class Meta:
        model = Video
        fields = ['id', 'election', 'polling_unit', 'video', 'video_url', 'uploaded_at', 'uploaded_by']
        read_only_fields = ['id', 'uploaded_at']
    
    def get_video_url(self, obj):
        """Get the full URL to the video"""
        if obj.video:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.video.url)
        return None


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


class AllResultsSerializer(serializers.Serializer):
    """
    Serializer for aggregated results from a polling unit for an election.
    Combines vote counts, images, videos, and comments.
    """
    votes = ElectionResultSerializer(many=True)
    images = ImageSerializer(many=True)
    videos = VideoSerializer(many=True)
    comments = CommentSerializer(many=True)
