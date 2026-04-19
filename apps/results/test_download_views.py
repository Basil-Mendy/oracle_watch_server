"""
Test Suite for Download Views
Tests individual and bulk download functionality
"""

import os
import io
import zipfile
from datetime import datetime
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from apps.elections.models import Election
from apps.locations.models import PollingUnit, LGA, Ward
from apps.results.models import Image, Video


class DownloadImageViewTest(TestCase):
    """Test single image download functionality"""

    def setUp(self):
        """Set up test fixtures"""
        # Create test data
        self.lga = LGA.objects.create(name='Test LGA', acronym='TL')
        self.ward = Ward.objects.create(lga=self.lga, name='Test Ward')
        self.polling_unit = PollingUnit.objects.create(
            unit_id='PU-001',
            name='Test Polling Unit',
            lga=self.lga,
            ward=self.ward,
            password='hashed_password'
        )
        
        self.election = Election.objects.create(
            name='Test Election',
            election_date=timezone.now().date(),
            status='active'
        )
        
        # Create test image
        image_file = SimpleUploadedFile(
            'test_image.jpg',
            content=b'fake image content',
            content_type='image/jpeg'
        )
        self.image = Image.objects.create(
            election=self.election,
            polling_unit=self.polling_unit,
            image=image_file,
            uploaded_by='test_user'
        )
        
        self.client = Client()

    def test_download_image_success(self):
        """Test successful image download"""
        response = self.client.get(
            f'/api/results/download-image/{self.image.id}/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        self.assertIn('Content-Disposition', response)
        self.assertIn('attachment', response['Content-Disposition'])

    def test_download_image_not_found(self):
        """Test download with non-existent image"""
        from uuid import uuid4
        fake_id = uuid4()
        
        response = self.client.get(
            f'/api/results/download-image/{fake_id}/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_download_image_filename(self):
        """Test that filename is set correctly"""
        response = self.client.get(
            f'/api/results/download-image/{self.image.id}/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content_disposition = response['Content-Disposition']
        self.assertIn('filename=', content_disposition)
        self.assertIn('image_', content_disposition)


class DownloadVideoViewTest(TestCase):
    """Test single video download functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.lga = LGA.objects.create(name='Test LGA', acronym='TL')
        self.ward = Ward.objects.create(lga=self.lga, name='Test Ward')
        self.polling_unit = PollingUnit.objects.create(
            unit_id='PU-001',
            name='Test Polling Unit',
            lga=self.lga,
            ward=self.ward,
            password='hashed_password'
        )
        
        self.election = Election.objects.create(
            name='Test Election',
            election_date='2026-04-18',
            status='active'
        )
        
        # Create test video
        video_file = SimpleUploadedFile(
            'test_video.mp4',
            content=b'fake video content',
            content_type='video/mp4'
        )
        self.video = Video.objects.create(
            election=self.election,
            polling_unit=self.polling_unit,
            video_file=video_file,
            uploaded_by='test_user'
        )
        
        self.client = Client()

    def test_download_video_success(self):
        """Test successful video download"""
        response = self.client.get(
            f'/api/results/download-video/{self.video.id}/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'video/mp4')
        self.assertIn('Content-Disposition', response)

    def test_download_video_not_found(self):
        """Test download with non-existent video"""
        from uuid import uuid4
        fake_id = uuid4()
        
        response = self.client.get(
            f'/api/results/download-video/{fake_id}/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class BulkDownloadImagesViewTest(TestCase):
    """Test bulk image download functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.lga = LGA.objects.create(name='Test LGA', acronym='TL')
        self.ward = Ward.objects.create(lga=self.lga, name='Test Ward')
        self.polling_unit = PollingUnit.objects.create(
            unit_id='PU-001',
            name='Test Polling Unit',
            lga=self.lga,
            ward=self.ward,
            password='hashed_password'
        )
        
        self.election = Election.objects.create(
            name='Test Election',
            election_date='2026-04-18',
            status='active'
        )
        
        # Create multiple test images
        for i in range(3):
            image_file = SimpleUploadedFile(
                f'test_image_{i}.jpg',
                content=b'fake image content',
                content_type='image/jpeg'
            )
            Image.objects.create(
                election=self.election,
                polling_unit=self.polling_unit,
                image=image_file,
                uploaded_by='test_user'
            )
        
        self.client = Client()

    def test_bulk_download_images_success(self):
        """Test successful bulk image download"""
        response = self.client.post(
            '/results/bulk-download-images/',
            data={
                'unit_id': 'PU-001',
                'password': 'hashed_password',
                'election_id': str(self.election.id)
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/zip')
        self.assertIn('Content-Disposition', response)
        self.assertIn('.zip', response['Content-Disposition'])

    def test_bulk_download_zip_contents(self):
        """Test that ZIP file contains correct files"""
        response = self.client.post(
            '/results/bulk-download-images/',
            data={
                'unit_id': 'PU-001',
                'password': 'hashed_password',
                'election_id': str(self.election.id)
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify ZIP contents
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        file_list = zip_file.namelist()
        
        self.assertEqual(len(file_list), 3)
        for filename in file_list:
            self.assertIn('image_', filename)

    def test_bulk_download_no_election(self):
        """Test bulk download with missing election_id"""
        response = self.client.post(
            '/api/results/bulk-download-images/',
            data={
                'unit_id': 'PU-001',
                'password': 'hashed_password'
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_download_invalid_election(self):
        """Test bulk download with non-existent election"""
        from uuid import uuid4
        fake_id = uuid4()
        
        response = self.client.post(
            '/results/bulk-download-images/',
            data={
                'unit_id': 'PU-001',
                'password': 'hashed_password',
                'election_id': str(fake_id)
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_download_no_images(self):
        """Test bulk download when no images exist"""
        # Create new election with no images
        election2 = Election.objects.create(
            name='Empty Election',
            election_date='2026-04-19',
            status='active'
        )
        
        response = self.client.post(
            '/results/bulk-download-images/',
            data={
                'unit_id': 'PU-001',
                'password': 'hashed_password',
                'election_id': str(election2.id)
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class BulkDownloadVideosViewTest(TestCase):
    """Test bulk video download functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.lga = LGA.objects.create(name='Test LGA', acronym='TL')
        self.ward = Ward.objects.create(lga=self.lga, name='Test Ward')
        self.polling_unit = PollingUnit.objects.create(
            unit_id='PU-001',
            name='Test Polling Unit',
            lga=self.lga,
            ward=self.ward,
            password='hashed_password'
        )
        
        self.election = Election.objects.create(
            name='Test Election',
            election_date='2026-04-18',
            status='active'
        )
        
        # Create multiple test videos
        for i in range(2):
            video_file = SimpleUploadedFile(
                f'test_video_{i}.mp4',
                content=b'fake video content',
                content_type='video/mp4'
            )
            Video.objects.create(
                election=self.election,
                polling_unit=self.polling_unit,
                video_file=video_file,
                uploaded_by='test_user'
            )
        
        self.client = Client()

    def test_bulk_download_videos_success(self):
        """Test successful bulk video download"""
        response = self.client.post(
            '/results/bulk-download-videos/',
            data={
                'unit_id': 'PU-001',
                'password': 'hashed_password',
                'election_id': str(self.election.id)
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/zip')

    def test_bulk_download_zip_has_videos(self):
        """Test that ZIP file contains videos"""
        response = self.client.post(
            '/results/bulk-download-videos/',
            data={
                'unit_id': 'PU-001',
                'password': 'hashed_password',
                'election_id': str(self.election.id)
            },
            content_type='application/json'
        )
        
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        file_list = zip_file.namelist()
        
        self.assertEqual(len(file_list), 2)
        for filename in file_list:
            self.assertIn('video_', filename)

    def test_bulk_download_polling_unit_filter(self):
        """Test that bulk download filters by polling unit"""
        # Create another polling unit
        polling_unit2 = PollingUnit.objects.create(
            unit_id='PU-002',
            name='Test Polling Unit 2',
            ward=self.ward,
            password='hashed_password'
        )
        
        # Add videos to second unit
        for i in range(3):
            video_file = SimpleUploadedFile(
                f'test_video_pu2_{i}.mp4',
                content=b'fake video content',
                content_type='video/mp4'
            )
            Video.objects.create(
                election=self.election,
                polling_unit=polling_unit2,
                video_file=video_file,
                uploaded_by='test_user'
            )
        
        # Download from first polling unit
        response = self.client.post(
            '/results/bulk-download-videos/',
            data={
                'unit_id': 'PU-001',
                'password': 'hashed_password',
                'election_id': str(self.election.id)
            },
            content_type='application/json'
        )
        
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        file_list = zip_file.namelist()
        
        # Should only have 2 videos (from PU-001)
        self.assertEqual(len(file_list), 2)


class DownloadIntegrationTest(TestCase):
    """Integration tests for download system"""

    def setUp(self):
        """Set up test fixtures"""
        self.lga = LGA.objects.create(name='Test LGA', acronym='TL')
        self.ward = Ward.objects.create(lga=self.lga, name='Test Ward')
        self.polling_unit = PollingUnit.objects.create(
            unit_id='PU-001',
            name='Test Polling Unit',
            lga=self.lga,
            ward=self.ward,
            password='hashed_password'
        )
        
        self.election = Election.objects.create(
            name='Test Election',
            election_date='2026-04-18',
            status='active'
        )
        
        self.client = Client()

    def test_download_workflow_images_and_videos(self):
        """Test complete download workflow with images and videos"""
        # Create test files
        for i in range(2):
            image_file = SimpleUploadedFile(
                f'test_image_{i}.jpg',
                content=b'fake image content',
                content_type='image/jpeg'
            )
            Image.objects.create(
                election=self.election,
                polling_unit=self.polling_unit,
                image_file=image_file
            )
            
            video_file = SimpleUploadedFile(
                f'test_video_{i}.mp4',
                content=b'fake video content',
                content_type='video/mp4'
            )
            Video.objects.create(
                election=self.election,
                polling_unit=self.polling_unit,
                video_file=video_file
            )
        
        # Download images
        response_images = self.client.post(
            '/results/bulk-download-images/',
            data={
                'unit_id': 'PU-001',
                'password': 'hashed_password',
                'election_id': str(self.election.id)
            },
            content_type='application/json'
        )
        
        # Download videos
        response_videos = self.client.post(
            '/results/bulk-download-videos/',
            data={
                'unit_id': 'PU-001',
                'password': 'hashed_password',
                'election_id': str(self.election.id)
            },
            content_type='application/json'
        )
        
        self.assertEqual(response_images.status_code, status.HTTP_200_OK)
        self.assertEqual(response_videos.status_code, status.HTTP_200_OK)
        
        # Verify both returned valid ZIPs
        images_zip = zipfile.ZipFile(io.BytesIO(response_images.content))
        videos_zip = zipfile.ZipFile(io.BytesIO(response_videos.content))
        
        self.assertEqual(len(images_zip.namelist()), 2)
        self.assertEqual(len(videos_zip.namelist()), 2)
