"""
New view for GetSubmissionStatusView - to be integrated into views.py
This provides submission status information for polling units
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.contrib.auth.hashers import check_password
from django.db.models import Count

from apps.locations.models import PollingUnit
from apps.elections.models import Election
from .models import ElectionResult, Image, Video, Comment
from .views import PollingUnitAuthMixin


class GetSubmissionStatusView(APIView, PollingUnitAuthMixin):
    """
    GET/POST: Get submission status for a polling unit in an election
    
    Returns what has been submitted:
    - Vote counts with merge behavior: OVERRIDE (new replaces old)
    - Media (images/videos) with merge behavior: ADD_TO_EXISTING
    - Comments with merge behavior: ADD_TO_EXISTING
    
    Polling units use this to know what submissions exist and what will happen
    on the next submission.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Get status using POST (from polling unit dashboard)"""
        polling_unit, error = self.authenticate_polling_unit(request)
        if error:
            return Response(error, status=status.HTTP_401_UNAUTHORIZED)
        
        election_id = request.data.get('election_id')
        
        if not election_id:
            return Response(
                {'error': 'election_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return self._get_submission_status(polling_unit, election_id)
    
    def get(self, request):
        """Get status using GET query params"""
        unit_id = request.query_params.get('unit_id')
        password = request.query_params.get('password')
        election_id = request.query_params.get('election_id')
        
        if not unit_id or not password or not election_id:
            return Response(
                {'error': 'unit_id, password, and election_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            polling_unit = PollingUnit.objects.get(unit_id=unit_id)
            if not check_password(password, polling_unit.password):
                return Response(
                    {'error': 'Invalid credentials'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except PollingUnit.DoesNotExist:
            return Response(
                {'error': 'Polling unit not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return self._get_submission_status(polling_unit, election_id)
    
    def _get_submission_status(self, polling_unit, election_id):
        """Get submission status for a polling unit and election"""
        try:
            election = Election.objects.get(id=election_id)
            
            # Get vote submission status
            vote_results = ElectionResult.objects.filter(
                election=election,
                polling_unit=polling_unit
            ).select_related('party')
            
            vote_status = {
                'submitted': vote_results.exists(),
                'merge_behavior': 'OVERRIDE',
                'merge_behavior_description': 'New vote count submission will replace the previous one',
                'count': vote_results.count(),
                'details': []
            }
            
            if vote_results.exists():
                # Get submission timestamp from first vote result
                first_result = vote_results.first()
                vote_status['submitted_at'] = first_result.submitted_at.isoformat()
                vote_status['updated_at'] = first_result.updated_at.isoformat()
                
                for result in vote_results:
                    vote_status['details'].append({
                        'party_id': str(result.party.id),
                        'party_name': result.party.name,
                        'party_acronym': result.party.acronym,
                        'vote_count': result.vote_count,
                        'last_updated': result.updated_at.isoformat()
                    })
            
            # Get image submission status
            images = Image.objects.filter(
                election=election,
                polling_unit=polling_unit
            )
            
            image_status = {
                'submitted': images.exists(),
                'merge_behavior': 'ADD_TO_EXISTING',
                'merge_behavior_description': 'New images will be added to existing ones',
                'count': images.count(),
                'max_allowed': 10,
                'remaining': max(0, 10 - images.count()),
                'first_submitted_at': images.earliest('uploaded_at').uploaded_at.isoformat() if images.exists() else None,
                'last_submitted_at': images.latest('uploaded_at').uploaded_at.isoformat() if images.exists() else None,
            }
            
            # Get video submission status
            videos = Video.objects.filter(
                election=election,
                polling_unit=polling_unit
            )
            
            video_status = {
                'submitted': videos.exists(),
                'merge_behavior': 'ADD_TO_EXISTING',
                'merge_behavior_description': 'New videos will be added to existing ones',
                'count': videos.count(),
                'first_submitted_at': videos.earliest('uploaded_at').uploaded_at.isoformat() if videos.exists() else None,
                'last_submitted_at': videos.latest('uploaded_at').uploaded_at.isoformat() if videos.exists() else None,
            }
            
            # Get comment submission status
            comments = Comment.objects.filter(
                election=election,
                polling_unit=polling_unit
            )
            
            comment_status = {
                'submitted': comments.exists(),
                'merge_behavior': 'ADD_TO_EXISTING',
                'merge_behavior_description': 'New comments will be added to existing ones',
                'count': comments.count(),
                'first_submitted_at': comments.earliest('created_at').created_at.isoformat() if comments.exists() else None,
                'last_submitted_at': comments.latest('created_at').created_at.isoformat() if comments.exists() else None,
            }
            
            # Overall submission status
            has_any_submission = any([
                vote_results.exists(),
                images.exists(),
                videos.exists(),
                comments.exists()
            ])
            
            return Response({
                'polling_unit': {
                    'id': str(polling_unit.id),
                    'unit_id': polling_unit.unit_id,
                    'name': polling_unit.name
                },
                'election': {
                    'id': str(election.id),
                    'name': election.name,
                    'status': election.status
                },
                'has_any_submission': has_any_submission,
                'submission_summary': {
                    'votes': vote_status['submitted'],
                    'images': image_status['submitted'],
                    'videos': video_status['submitted'],
                    'comments': comment_status['submitted'],
                },
                'submissions': {
                    'vote_counts': vote_status,
                    'images': image_status,
                    'videos': video_status,
                    'comments': comment_status,
                }
            })
        
        except Election.DoesNotExist:
            return Response(
                {'error': 'Election not found'},
                status=status.HTTP_404_NOT_FOUND
            )
