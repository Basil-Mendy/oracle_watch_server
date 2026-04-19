"""
Download Views - For downloading images and videos from election results
Supports both individual and bulk downloads with ZIP file generation
"""

import os
import io
import zipfile
from datetime import datetime
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from apps.elections.models import Election
from apps.locations.models import PollingUnit
from .models import Image, Video
from .views import PollingUnitAuthMixin


class DownloadImageView(APIView):
    """
    GET: Download a single image file
    
    URL params:
    - image_id: UUID of the image to download
    
    Query params (optional):
    - token: Download token for public access
    
    Returns: Binary image file
    """
    permission_classes = [AllowAny]
    
    def get(self, request, image_id):
        try:
            image = get_object_or_404(Image, id=image_id)
            
            if not image.image_file:
                return Response(
                    {'error': 'Image file not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get file path
            file_path = image.image_file.path
            
            if not os.path.exists(file_path):
                return Response(
                    {'error': 'Image file not found on server'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Stream the file
            response = FileResponse(
                open(file_path, 'rb'),
                content_type='image/jpeg'
            )
            
            # Set download filename
            filename = f"image_{image.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Image.DoesNotExist:
            return Response(
                {'error': 'Image not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DownloadVideoView(APIView):
    """
    GET: Download a single video file
    
    URL params:
    - video_id: UUID of the video to download
    
    Returns: Binary video file OR redirect to storage URL
    """
    permission_classes = [AllowAny]
    
    def get(self, request, video_id):
        try:
            video = get_object_or_404(Video, id=video_id)
            
            if not video.video_file:
                return Response(
                    {'error': 'Video file not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get file path
            file_path = video.video_file.path
            
            if not os.path.exists(file_path):
                return Response(
                    {'error': 'Video file not found on server'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Stream the file
            response = FileResponse(
                open(file_path, 'rb'),
                content_type='video/mp4'
            )
            
            # Set download filename
            filename = f"video_{video.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Video.DoesNotExist:
            return Response(
                {'error': 'Video not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BulkDownloadImagesView(APIView, PollingUnitAuthMixin):
    """
    POST: Download all images from an election as ZIP
    
    Supports both polling unit and admin access.
    
    Request:
    {
        "unit_id": "string" (optional, for polling unit)
        "password": "string" (optional, for polling unit)
        "election_id": "uuid",
        "access_token": "string" (optional, for admin)
    }
    
    Returns: ZIP file containing all images
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        election_id = request.data.get('election_id')
        unit_id = request.data.get('unit_id')
        access_token = request.data.get('access_token')
        
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
        
        # Determine access scope
        images_query = Image.objects.filter(election=election)
        
        # If unit_id provided, filter to that polling unit only
        if unit_id:
            try:
                polling_unit = PollingUnit.objects.get(unit_id=unit_id)
                images_query = images_query.filter(polling_unit=polling_unit)
            except PollingUnit.DoesNotExist:
                return Response(
                    {'error': 'Polling unit not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        images = images_query.order_by('uploaded_at')
        
        if not images.exists():
            return Response(
                {'error': 'No images found for this election'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create ZIP in memory
        try:
            zip_img = io.BytesIO()
            
            with zipfile.ZipFile(zip_img, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for idx, image in enumerate(images, 1):
                    if image.image_file:
                        file_path = image.image_file.path
                        if os.path.exists(file_path):
                            # Create unique filename
                            file_ext = os.path.splitext(file_path)[1]
                            archive_name = f"image_{idx:03d}_{image.uploaded_at.strftime('%Y%m%d_%H%M%S')}{file_ext}"
                            
                            # Add file to ZIP
                            zip_file.write(file_path, arcname=archive_name)
            
            zip_img.seek(0)
            
            # Create response
            response = HttpResponse(
                zip_img.getvalue(),
                content_type='application/zip'
            )
            
            # Set download filename
            filename = f"{election.name.replace(' ', '_')}_images_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return Response(
                {'error': f'Failed to create ZIP: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BulkDownloadVideosView(APIView, PollingUnitAuthMixin):
    """
    POST: Download all videos from an election as ZIP
    
    Supports both polling unit and admin access.
    
    Request:
    {
        "unit_id": "string" (optional, for polling unit)
        "password": "string" (optional, for polling unit)
        "election_id": "uuid",
        "access_token": "string" (optional, for admin)
    }
    
    Returns: ZIP file containing all videos
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        election_id = request.data.get('election_id')
        unit_id = request.data.get('unit_id')
        access_token = request.data.get('access_token')
        
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
        
        # Determine access scope
        videos_query = Video.objects.filter(election=election)
        
        # If unit_id provided, filter to that polling unit only
        if unit_id:
            try:
                polling_unit = PollingUnit.objects.get(unit_id=unit_id)
                videos_query = videos_query.filter(polling_unit=polling_unit)
            except PollingUnit.DoesNotExist:
                return Response(
                    {'error': 'Polling unit not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        videos = videos_query.order_by('uploaded_at')
        
        if not videos.exists():
            return Response(
                {'error': 'No videos found for this election'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create ZIP in memory
        try:
            zip_img = io.BytesIO()
            
            with zipfile.ZipFile(zip_img, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for idx, video in enumerate(videos, 1):
                    if video.video_file:
                        file_path = video.video_file.path
                        if os.path.exists(file_path):
                            # Create unique filename
                            file_ext = os.path.splitext(file_path)[1]
                            archive_name = f"video_{idx:03d}_{video.uploaded_at.strftime('%Y%m%d_%H%M%S')}{file_ext}"
                            
                            # Add file to ZIP
                            zip_file.write(file_path, arcname=archive_name)
            
            zip_img.seek(0)
            
            # Create response
            response = HttpResponse(
                zip_img.getvalue(),
                content_type='application/zip'
            )
            
            # Set download filename
            filename = f"{election.name.replace(' ', '_')}_videos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return Response(
                {'error': f'Failed to create ZIP: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
