"""
Additional admin views for Results Management Dashboard
GET endpoints for videos, images, comments, and aggregated results
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Sum, Q, Prefetch

from apps.locations.models import PollingUnit, LGA, Ward
from apps.elections.models import Election
from .models import ElectionResult, Image, Video, Comment
from .serializers import (
    ElectionResultSerializer, ImageSerializer, VideoSerializer,
    CommentSerializer
)


class AdminVideosListView(APIView):
    """
    GET: List all videos for an election (for admin dashboard)
    Query params: election_id (required)
    
    Returns: List of videos with polling unit metadata
    """
    permission_classes = [IsAuthenticated]  # Only authenticated admins can view
    
    def get(self, request):
        election_id = request.query_params.get('election_id')
        ward_filter = request.query_params.get('ward')
        lga_filter = request.query_params.get('lga')
        search = request.query_params.get('search')
        
        if not election_id:
            return Response(
                {'error': 'election_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            election = Election.objects.get(id=election_id)
        except Election.DoesNotExist:
            return Response(
                {'error': 'Election not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Fetch videos with related polling unit data
        videos = Video.objects.filter(election=election).select_related(
            'polling_unit', 'polling_unit__ward', 'polling_unit__lga'
        )
        
        # Apply filters
        if lga_filter:
            videos = videos.filter(polling_unit__lga__id=lga_filter)
        
        if ward_filter:
            videos = videos.filter(polling_unit__ward__id=ward_filter)
        
        if search:
            videos = videos.filter(
                Q(polling_unit__name__icontains=search) |
                Q(polling_unit__unit_id__icontains=search)
            )
        
        # Order by newest first
        videos = videos.order_by('-uploaded_at')
        
        serializer = VideoSerializer(videos, many=True, context={'request': request})
        return Response({
            'count': videos.count(),
            'videos': serializer.data
        })


class AdminImagesListView(APIView):
    """
    GET: List all images for an election (for admin dashboard)
    Query params: election_id (required)
    
    Returns: List of images with polling unit metadata
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        election_id = request.query_params.get('election_id')
        ward_filter = request.query_params.get('ward')
        lga_filter = request.query_params.get('lga')
        search = request.query_params.get('search')
        
        if not election_id:
            return Response(
                {'error': 'election_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            election = Election.objects.get(id=election_id)
        except Election.DoesNotExist:
            return Response(
                {'error': 'Election not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        images = Image.objects.filter(election=election).select_related(
            'polling_unit', 'polling_unit__ward', 'polling_unit__lga'
        )
        
        if lga_filter:
            images = images.filter(polling_unit__lga__id=lga_filter)
        
        if ward_filter:
            images = images.filter(polling_unit__ward__id=ward_filter)
        
        if search:
            images = images.filter(
                Q(polling_unit__name__icontains=search) |
                Q(polling_unit__unit_id__icontains=search)
            )
        
        images = images.order_by('-uploaded_at')
        
        serializer = ImageSerializer(images, many=True, context={'request': request})
        return Response({
            'count': images.count(),
            'images': serializer.data
        })


class AdminCommentsListView(APIView):
    """
    GET: List all comments for an election (for admin dashboard)
    Query params: election_id (required)
    
    Returns: List of comments with polling unit metadata
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        election_id = request.query_params.get('election_id')
        ward_filter = request.query_params.get('ward')
        lga_filter = request.query_params.get('lga')
        search = request.query_params.get('search')
        
        if not election_id:
            return Response(
                {'error': 'election_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            election = Election.objects.get(id=election_id)
        except Election.DoesNotExist:
            return Response(
                {'error': 'Election not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        comments = Comment.objects.filter(election=election).select_related(
            'polling_unit', 'polling_unit__ward', 'polling_unit__lga'
        )
        
        if lga_filter:
            comments = comments.filter(polling_unit__lga__id=lga_filter)
        
        if ward_filter:
            comments = comments.filter(polling_unit__ward__id=ward_filter)
        
        if search:
            comments = comments.filter(
                Q(polling_unit__name__icontains=search) |
                Q(polling_unit__unit_id__icontains=search) |
                Q(comment_text__icontains=search)
            )
        
        comments = comments.order_by('-created_at')
        
        serializer = CommentSerializer(comments, many=True)
        return Response({
            'count': comments.count(),
            'comments': serializer.data
        })


class AdminAllResultsListView(APIView):
    """
    GET: List all vote results for an election (for admin dashboard)
    Query params: election_id (required)
    
    Returns: List of all vote submissions with full metadata
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        election_id = request.query_params.get('election_id')
        ward_filter = request.query_params.get('ward')
        lga_filter = request.query_params.get('lga')
        search = request.query_params.get('search')
        
        if not election_id:
            return Response(
                {'error': 'election_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            election = Election.objects.get(id=election_id)
        except Election.DoesNotExist:
            return Response(
                {'error': 'Election not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        results = ElectionResult.objects.filter(election=election).select_related(
            'polling_unit', 'polling_unit__ward', 'polling_unit__lga', 'party'
        )
        
        if lga_filter:
            results = results.filter(polling_unit__lga__id=lga_filter)
        
        if ward_filter:
            results = results.filter(polling_unit__ward__id=ward_filter)
        
        if search:
            results = results.filter(
                Q(polling_unit__name__icontains=search) |
                Q(polling_unit__unit_id__icontains=search)
            )
        
        results = results.order_by('-submitted_at')
        
        serializer = ElectionResultSerializer(results, many=True)
        return Response({
            'count': results.count(),
            'results': serializer.data
        })
