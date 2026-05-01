"""
Views for handling election results submission and retrieval.
Used by polling unit agents to submit results.
Used by public to view results.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Sum, Q
from django.contrib.auth.hashers import check_password

from apps.locations.models import PollingUnit, LGA, Ward
from apps.elections.models import Election, Party
from .models import ElectionResult, Image, Video, Comment, LiveStreamSession
from .serializers import (
    ElectionResultSerializer, ImageSerializer, VideoSerializer,
    CommentSerializer, AllResultsSerializer
)


class PollingUnitAuthMixin:
    """Helper to authenticate polling units by unit_id and password"""
    
    def authenticate_polling_unit(self, request):
        """Extract and validate polling unit credentials from request"""
        unit_id = request.data.get('unit_id') or request.query_params.get('unit_id')
        password = request.data.get('password') or request.query_params.get('password')
        
        if not unit_id or not password:
            return None, {'error': 'unit_id and password are required'}
        
        try:
            polling_unit = PollingUnit.objects.get(unit_id=unit_id)
            if not check_password(password, polling_unit.password):
                return None, {'error': 'Invalid credentials'}
            return polling_unit, None
        except PollingUnit.DoesNotExist:
            return None, {'error': 'Polling unit not found'}


class SubmitElectionResultView(APIView, PollingUnitAuthMixin):
    """
    POST: Submit election results from a polling unit
    Body: {
        "unit_id": "PU-00001",
        "password": "...",
        "election_id": "uuid",
        "results": [
            {"party_id": "uuid", "vote_count": 100},
            {"party_id": "uuid", "vote_count": 50}
        ]
    }
    
    Used by polling unit agents to submit vote counts.
    """
    permission_classes = [AllowAny]  # Polling units don't have user accounts
    
    def post(self, request):
        polling_unit, error = self.authenticate_polling_unit(request)
        if error:
            return Response(error, status=status.HTTP_401_UNAUTHORIZED)
        
        election_id = request.data.get('election_id')
        results_data = request.data.get('results', [])
        
        if not election_id or not results_data:
            return Response(
                {'error': 'election_id and results are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .models import PendingResultSubmission
            import json
            
            election = Election.objects.get(id=election_id)
            
            # Check election is active
            if election.status != 'active':
                return Response(
                    {'error': 'This election is not currently active'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Convert results to vote_data format {party_id: vote_count}
            vote_data = {}
            for result_data in results_data:
                party_id = result_data.get('party_id')
                vote_count = result_data.get('vote_count', 0)
                if party_id:
                    vote_data[party_id] = vote_count
            
            if not vote_data:
                return Response(
                    {'error': 'At least one vote count is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create pending submission for approval workflow
            submission = PendingResultSubmission.objects.create(
                election=election,
                polling_unit=polling_unit,
                vote_data=vote_data,
                status='pending'
            )
            
            return Response({
                'message': 'Results submitted for review. Awaiting admin approval.',
                'submission_id': str(submission.id),
                'status': 'pending',
                'vote_count': sum(vote_data.values())
            }, status=status.HTTP_201_CREATED)
        except Election.DoesNotExist:
            return Response(
                {'error': 'Election not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class UploadResultMediaView(APIView, PollingUnitAuthMixin):
    """
    POST: Upload images or videos for an election
    Expects multipart/form-data with: unit_id, password, election_id, file
    
    Used by polling unit agents to upload images and videos.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        polling_unit, error = self.authenticate_polling_unit(request)
        if error:
            return Response(error, status=status.HTTP_401_UNAUTHORIZED)
        
        election_id = request.data.get('election_id')
        file_obj = request.FILES.get('file')
        file_type = request.data.get('file_type')  # 'image' or 'video'
        
        if not election_id or not file_obj or not file_type:
            return Response(
                {'error': 'election_id, file, and file_type are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            election = Election.objects.get(id=election_id)
            
            if file_type == 'image':
                # Check max 10 images per election per polling unit
                image_count = Image.objects.filter(
                    election=election,
                    polling_unit=polling_unit
                ).count()
                
                if image_count >= 10:
                    return Response(
                        {'error': 'Maximum 10 images allowed per election'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                try:
                    image = Image.objects.create(
                        election=election,
                        polling_unit=polling_unit,
                        image=file_obj,
                        uploaded_by=polling_unit.unit_id
                    )
                    
                    return Response(
                        {'message': 'Image uploaded successfully', 'image': ImageSerializer(image, context={'request': request}).data},
                        status=status.HTTP_201_CREATED
                    )
                except Exception as e:
                    return Response(
                        {'error': f'Failed to save image: {str(e)}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            elif file_type == 'video':
                try:
                    video = Video.objects.create(
                        election=election,
                        polling_unit=polling_unit,
                        video=file_obj,
                        uploaded_by=polling_unit.unit_id
                    )
                    
                    return Response(
                        {'message': 'Video uploaded successfully', 'video': VideoSerializer(video, context={'request': request}).data},
                        status=status.HTTP_201_CREATED
                    )
                except Exception as e:
                    return Response(
                        {'error': f'Failed to save video: {str(e)}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            else:
                return Response(
                    {'error': 'file_type must be "image" or "video"'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except Election.DoesNotExist:
            return Response(
                {'error': 'Election not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'An unexpected error occurred: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AddCommentView(APIView, PollingUnitAuthMixin):
    """
    POST: Add a comment for an election
    Body: {
        "unit_id": "PU-00001",
        "password": "...",
        "election_id": "uuid",
        "comment_text": "..."
    }
    
    Used by polling unit agents to add comments/notes.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        polling_unit, error = self.authenticate_polling_unit(request)
        if error:
            return Response(error, status=status.HTTP_401_UNAUTHORIZED)
        
        election_id = request.data.get('election_id')
        comment_text = request.data.get('comment_text')
        
        if not election_id or not comment_text:
            return Response(
                {'error': 'election_id and comment_text are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            election = Election.objects.get(id=election_id)
            
            comment = Comment.objects.create(
                election=election,
                polling_unit=polling_unit,
                comment_text=comment_text,
                created_by=polling_unit.unit_id
            )
            
            return Response(
                {'message': 'Comment added successfully', 'comment': CommentSerializer(comment).data},
                status=status.HTTP_201_CREATED
            )
        except Election.DoesNotExist:
            return Response(
                {'error': 'Election not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class GetPollingUnitResultsView(APIView, PollingUnitAuthMixin):
    """
    GET/POST: Get all results for a polling unit in an election
    
    Returns: {votes, images, videos, comments}
    
    Public view - no authentication required.
    """
    permission_classes = [AllowAny]
    
    def get(self, request, unit_id, election_id):
        """GET results without authentication (public view)"""
        try:
            polling_unit = PollingUnit.objects.get(unit_id=unit_id)
            election = Election.objects.get(id=election_id)
            
            votes = ElectionResult.objects.filter(
                election=election,
                polling_unit=polling_unit
            )
            images = Image.objects.filter(
                election=election,
                polling_unit=polling_unit
            )
            videos = Video.objects.filter(
                election=election,
                polling_unit=polling_unit
            )
            comments = Comment.objects.filter(
                election=election,
                polling_unit=polling_unit
            )
            
            return Response({
                'polling_unit': {'unit_id': polling_unit.unit_id, 'name': polling_unit.name},
                'election': {'id': str(election.id), 'name': election.name},
                'votes': ElectionResultSerializer(votes, many=True).data,
                'images': ImageSerializer(images, many=True, context={'request': request}).data,
                'videos': VideoSerializer(videos, many=True, context={'request': request}).data,
                'comments': CommentSerializer(comments, many=True).data,
            })
        except (PollingUnit.DoesNotExist, Election.DoesNotExist):
            return Response(
                {'error': 'Polling unit or election not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class GetElectionResultsAggregateView(APIView):
    """
    GET: Get aggregated results for an election at LGA/Ward level
    Query params:
        - election_id: UUID
        - level: 'lga' or 'ward'  (default: 'lga')
        - lga_id: UUID (optional, for filtering)
        - ward_id: UUID (optional, for filtering)
    
    Returns: Aggregated vote counts by party
    
    Public view.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        election_id = request.query_params.get('election_id')
        level = request.query_params.get('level', 'lga')
        lga_id = request.query_params.get('lga_id')
        ward_id = request.query_params.get('ward_id')
        
        if not election_id:
            return Response(
                {'error': 'election_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            election = Election.objects.get(id=election_id)
            
            if level == 'ward' and ward_id:
                # Get results for a specific ward
                polling_units = PollingUnit.objects.filter(ward_id=ward_id)
            elif level == 'lga' and lga_id:
                # Get results for a specific LGA
                polling_units = PollingUnit.objects.filter(lga_id=lga_id)
            elif level == 'lga':
                # Get results for all LGAs
                polling_units = PollingUnit.objects.all()
            else:
                return Response(
                    {'error': 'Invalid level parameter'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Aggregate vote counts by party
            results = ElectionResult.objects.filter(
                election=election,
                polling_unit__in=polling_units
            ).values('party__id', 'party__name', 'party__logo').annotate(
                total_votes=Sum('vote_count')
            ).order_by('-total_votes')
            
            # Get grand total
            grand_total = sum(r['total_votes'] or 0 for r in results)
            
            return Response({
                'election': {'id': str(election.id), 'name': election.name},
                'level': level,
                'results': list(results),
                'grand_total': grand_total,
            })
        except Election.DoesNotExist:
            return Response(
                {'error': 'Election not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class GetHierarchicalResultsView(APIView):
    """
    GET: Get hierarchical results for an election at state, LGA, ward, or polling unit level
    Query params:
        - election: UUID (required)
        - level: 'state', 'lga', 'ward', 'polling_unit' (default: 'state')
        - lga: LGA ID (for filtering ward/polling unit results)
        - ward: Ward ID (for filtering polling unit results)
    
    Returns: Aggregated results for the specified level with parties data
    
    Public view.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        election_id = request.query_params.get('election')
        level = request.query_params.get('level', 'state')
        lga_id = request.query_params.get('lga')
        ward_id = request.query_params.get('ward')
        
        if not election_id:
            return Response(
                {'error': 'election parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            election = Election.objects.get(id=election_id)
            
            # Get all parties in this election through ElectionParty table
            election_parties = Party.objects.filter(
                election_parties__election=election
            ).distinct()
            
            if level == 'state':
                # State level: aggregate all polling unit results
                results_data = self._get_state_level_results(election, election_parties)
            
            elif level == 'lga':
                # LGA level: aggregate results by LGA
                results_data = self._get_lga_level_results(election, election_parties, lga_id)
            
            elif level == 'ward':
                # Ward level: aggregate results by ward within an LGA
                if not lga_id:
                    return Response(
                        {'error': 'lga parameter is required for ward level'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                results_data = self._get_ward_level_results(election, election_parties, lga_id)
            
            elif level == 'polling_unit':
                # Polling unit level: show individual polling unit results
                if not ward_id:
                    return Response(
                        {'error': 'ward parameter is required for polling_unit level'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                results_data = self._get_polling_unit_level_results(election, election_parties, ward_id)
            
            else:
                return Response(
                    {'error': 'Invalid level parameter'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response(results_data)
        
        except Election.DoesNotExist:
            return Response(
                {'error': 'Election not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def _get_state_level_results(self, election, election_parties):
        """Aggregate all results at state level with wins data and LGA breakdown"""
        parties_data = []
        total_votes = 0
        party_polling_wins = {}  # Track polling unit wins per party
        party_ward_wins = {}     # Track ward wins per party
        
        for party in election_parties:
            votes = ElectionResult.objects.filter(
                election=election,
                party=party
            ).aggregate(total=Sum('vote_count'))['total'] or 0
            
            parties_data.append({
                'id': party.id,
                'name': party.name,
                'acronym': party.acronym,
                'logo_url': party.logo.url if party.logo else None,
                'votes': votes
            })
            total_votes += votes
            party_polling_wins[party.acronym] = 0
            party_ward_wins[party.acronym] = 0
        
        # Calculate polling unit wins (which party has most votes in each PU)
        all_polling_units = PollingUnit.objects.all()
        for pu in all_polling_units:
            # Get top party in this polling unit
            pu_results = ElectionResult.objects.filter(
                election=election,
                polling_unit=pu
            ).values('party__acronym').annotate(
                total=Sum('vote_count')
            ).order_by('-total').first()
            
            if pu_results:
                acronym = pu_results['party__acronym']
                party_polling_wins[acronym] = party_polling_wins.get(acronym, 0) + 1
        
        # Calculate ward wins (which party has most votes in each ward)
        all_wards = Ward.objects.all()
        for ward in all_wards:
            # Get top party in this ward
            ward_results = ElectionResult.objects.filter(
                election=election,
                polling_unit__ward=ward
            ).values('party__acronym').annotate(
                total=Sum('vote_count')
            ).order_by('-total').first()
            
            if ward_results:
                acronym = ward_results['party__acronym']
                party_ward_wins[acronym] = party_ward_wins.get(acronym, 0) + 1
        
        # Add wins data to parties
        for party in parties_data:
            party['polling_wins'] = party_polling_wins.get(party['acronym'], 0)
            party['ward_wins'] = party_ward_wins.get(party['acronym'], 0)
        
        # Sort by votes descending
        parties_data.sort(key=lambda x: x['votes'], reverse=True)
        
        # Get LGA breakdown for the LGA chart
        lgas = LGA.objects.all()
        lga_data = []
        for lga in lgas:
            lga_obj = {
                'id': lga.id,
                'name': lga.name,
                'acronym': lga.acronym
            }
            # Add vote counts per party for this LGA
            for party in election_parties:
                votes = ElectionResult.objects.filter(
                    election=election,
                    party=party,
                    polling_unit__lga=lga
                ).aggregate(total=Sum('vote_count'))['total'] or 0
                lga_obj[party.acronym] = votes
            
            lga_data.append(lga_obj)
        
        return {
            'election': {
                'id': str(election.id),
                'name': election.name,
                'status': election.status
            },
            'level': 'state',
            'parties': parties_data,
            'total_votes': total_votes,
            'lgas': lga_data  # Include LGA breakdown for charts
        }
    
    def _get_lga_level_results(self, election, election_parties, lga_id=None):
        """Aggregate results at LGA level"""
        if lga_id:
            try:
                lga = LGA.objects.get(id=lga_id)
                lgas = [lga]
            except LGA.DoesNotExist:
                return {'error': 'LGA not found'}
        else:
            lgas = LGA.objects.all()
        
        lga_results = []
        
        for lga in lgas:
            parties_data = []
            total_votes = 0
            
            polling_units = PollingUnit.objects.filter(lga=lga)
            
            for party in election_parties:
                votes = ElectionResult.objects.filter(
                    election=election,
                    party=party,
                    polling_unit__in=polling_units
                ).aggregate(total=Sum('vote_count'))['total'] or 0
                
                parties_data.append({
                    'id': party.id,
                    'name': party.name,
                    'acronym': party.acronym,
                    'logo_url': party.logo.url if party.logo else None,
                    'votes': votes
                })
                total_votes += votes
            
            parties_data.sort(key=lambda x: x['votes'], reverse=True)
            
            lga_results.append({
                'id': lga.id,
                'name': lga.name,
                'acronym': lga.acronym,
                'parties': parties_data,
                'total_votes': total_votes
            })
        
        lga_results.sort(key=lambda x: x['total_votes'], reverse=True)
        
        return {
            'election': {
                'id': str(election.id),
                'name': election.name,
                'status': election.status
            },
            'level': 'lga',
            'lgas': lga_results,
            'total_votes': sum(lga['total_votes'] for lga in lga_results)
        }
    
    def _get_ward_level_results(self, election, election_parties, lga_id):
        """Aggregate results at ward level within an LGA"""
        try:
            lga = LGA.objects.get(id=lga_id)
        except LGA.DoesNotExist:
            return {'error': 'LGA not found'}
        
        wards = Ward.objects.filter(lga=lga)
        ward_results = []
        
        for ward in wards:
            parties_data = []
            total_votes = 0
            
            polling_units = PollingUnit.objects.filter(ward=ward)
            
            for party in election_parties:
                votes = ElectionResult.objects.filter(
                    election=election,
                    party=party,
                    polling_unit__in=polling_units
                ).aggregate(total=Sum('vote_count'))['total'] or 0
                
                parties_data.append({
                    'id': party.id,
                    'name': party.name,
                    'acronym': party.acronym,
                    'logo_url': party.logo.url if party.logo else None,
                    'votes': votes
                })
                total_votes += votes
            
            parties_data.sort(key=lambda x: x['votes'], reverse=True)
            
            ward_results.append({
                'id': ward.id,
                'name': ward.name,
                'parties': parties_data,
                'total_votes': total_votes,
                'lga': {'id': lga.id, 'name': lga.name}  # Include LGA info
            })
        
        ward_results.sort(key=lambda x: x['total_votes'], reverse=True)
        
        return {
            'election': {
                'id': str(election.id),
                'name': election.name,
                'status': election.status
            },
            'level': 'ward',
            'lga': {'id': lga.id, 'name': lga.name},
            'wards': ward_results,
            'total_votes': sum(ward['total_votes'] for ward in ward_results)
        }
    
    def _get_polling_unit_level_results(self, election, election_parties, ward_id):
        """Get results for individual polling units in a ward"""
        try:
            ward = Ward.objects.get(id=ward_id)
        except Ward.DoesNotExist:
            return {'error': 'Ward not found'}
        
        polling_units = PollingUnit.objects.filter(ward=ward)
        unit_results = []
        
        for unit in polling_units:
            parties_data = []
            total_votes = 0
            
            for party in election_parties:
                results = ElectionResult.objects.filter(
                    election=election,
                    party=party,
                    polling_unit=unit
                )
                
                votes = results.aggregate(total=Sum('vote_count'))['total'] or 0
                
                parties_data.append({
                    'id': party.id,
                    'name': party.name,
                    'acronym': party.acronym,
                    'logo_url': party.logo.url if party.logo else None,
                    'votes': votes
                })
                total_votes += votes
            
            parties_data.sort(key=lambda x: x['votes'], reverse=True)
            
            unit_results.append({
                'id': unit.id,
                'name': unit.name,
                'unit_id': unit.unit_id,
                'parties': parties_data,
                'total_votes': total_votes,
                'ward': {'id': ward.id, 'name': ward.name},  # Include ward info
                'lga': {'id': unit.lga.id, 'name': unit.lga.name} if unit.lga else None  # Include LGA info
            })
        
        unit_results.sort(key=lambda x: x['total_votes'], reverse=True)
        
        return {
            'election': {
                'id': str(election.id),
                'name': election.name,
                'status': election.status
            },
            'level': 'polling_unit',
            'ward': {'id': ward.id, 'name': ward.name},
            'polling_units': unit_results,
            'total_votes': sum(unit['total_votes'] for unit in unit_results)
        }


# ======================== ANALYTICS / AUDIT ENDPOINTS ========================


class GetPendingResultsView(APIView):
    """
    GET: Get all pending result submissions grouped by LGA
    Query params:
        - election_id: UUID (required)
    
    Requires admin authentication (via token or session)
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Check if user is authenticated (admin)
        if not hasattr(request, 'user') or request.user is None or not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required. Please log in as an admin.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        election_id = request.query_params.get('election_id')
        
        if not election_id:
            return Response(
                {'error': 'election_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            election = Election.objects.get(id=election_id)
            
            from .models import PendingResultSubmission
            
            # Get all pending submissions
            pending = PendingResultSubmission.objects.filter(
                election=election
            ).select_related('polling_unit', 'polling_unit__lga')
            
            # Group by LGA
            lga_data = {}
            stats = {
                'pending': pending.filter(status='pending').count(),
                'approved': pending.filter(status='approved').count(),
                'rejected': pending.filter(status='rejected').count(),
            }
            
            for submission in pending:
                lga_name = submission.polling_unit.lga.name
                if lga_name not in lga_data:
                    lga_data[lga_name] = {
                        'lga_id': str(submission.polling_unit.lga.id),
                        'submissions': [],
                        'stats': {
                            'received': 0,
                            'approved': 0,
                            'rejected': 0,
                            'pending': 0
                        }
                    }
                
                submission_dict = {
                    'id': str(submission.id),
                    'polling_unit': {
                        'id': str(submission.polling_unit.id),
                        'unit_id': submission.polling_unit.unit_id,
                        'name': submission.polling_unit.name,
                    },
                    'status': submission.status,
                    'submitted_at': submission.submitted_at.isoformat(),
                    'vote_data': submission.vote_data,
                    'ec8a_form_image': submission.ec8a_form_image.url if submission.ec8a_form_image else None,
                    'admin_notes': submission.admin_notes,
                    'reviewed_by': submission.reviewed_by,
                }
                
                lga_data[lga_name]['submissions'].append(submission_dict)
                lga_data[lga_name]['stats']['received'] += 1
                lga_data[lga_name]['stats'][submission.status] += 1
            
            # Serialize parties
            from apps.elections.serializers import PartySerializer
            parties = [ep.party for ep in election.election_parties.all()]
            parties_data = PartySerializer(parties, many=True, context={'request': request}).data
            
            return Response({
                'election': {'id': str(election.id), 'name': election.name, 'parties': parties_data},
                'overall_stats': stats,
                'lgas': lga_data
            })
        
        except Election.DoesNotExist:
            return Response(
                {'error': 'Election not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ApproveResultSubmissionView(APIView):
    """
    POST: Approve a pending result submission
    Body: {
        "submission_id": "uuid",
        "edited_votes": {...}  # Optional: if admin modified vote counts
    }
    
    Admin only (requires authentication)
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Check if user is authenticated (admin)
        if not hasattr(request, 'user') or request.user is None or not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required. Please log in as an admin.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        submission_id = request.data.get('submission_id')
        edited_votes = request.data.get('edited_votes')
        
        if not submission_id:
            return Response(
                {'error': 'submission_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .models import PendingResultSubmission
            
            submission = PendingResultSubmission.objects.get(id=submission_id)
            
            if submission.status != 'pending':
                return Response(
                    {'error': f'Submission status is {submission.status}, not pending'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Use provided votes or original submission votes
            final_votes = edited_votes if edited_votes else submission.vote_data
            
            # Save the result for each party
            for party_id, vote_count in final_votes.items():
                try:
                    party = Party.objects.get(id=party_id)
                    result, _ = ElectionResult.objects.update_or_create(
                        election=submission.election,
                        polling_unit=submission.polling_unit,
                        party=party,
                        defaults={
                            'vote_count': vote_count,
                            'submission': submission,
                            'approved_at': __import__('django.utils.timezone', fromlist=['now']).now()
                        }
                    )
                except Party.DoesNotExist:
                    pass
            
            # Update submission status
            submission.status = 'approved'
            submission.reviewed_by = request.user.username
            submission.reviewed_at = __import__('django.utils.timezone', fromlist=['now']).now()
            if edited_votes:
                submission.edited_vote_data = edited_votes
            submission.save()
            
            return Response({
                'message': 'Result approved successfully',
                'submission_id': str(submission.id)
            })
        
        except PendingResultSubmission.DoesNotExist:
            return Response(
                {'error': 'Submission not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class RejectResultSubmissionView(APIView):
    """
    POST: Reject a pending result submission
    Body: {
        "submission_id": "uuid",
        "reason": "Reason for rejection"
    }
    
    Admin only (requires authentication)
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Check if user is authenticated (admin)
        if not hasattr(request, 'user') or request.user is None or not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required. Please log in as an admin.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        submission_id = request.data.get('submission_id')
        reason = request.data.get('reason', '')
        
        if not submission_id:
            return Response(
                {'error': 'submission_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .models import PendingResultSubmission, RejectionNotification
            
            submission = PendingResultSubmission.objects.get(id=submission_id)
            
            if submission.status != 'pending':
                return Response(
                    {'error': f'Submission status is {submission.status}, not pending'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update submission status
            submission.status = 'rejected'
            submission.reviewed_by = request.user.username
            submission.reviewed_at = __import__('django.utils.timezone', fromlist=['now']).now()
            submission.admin_notes = reason
            submission.save()
            
            # Create rejection notification for polling unit
            RejectionNotification.objects.create(
                submission=submission,
                reason=reason,
                rejected_by=request.user.username
            )
            
            return Response({
                'message': 'Result rejected. Polling unit will be notified to resubmit.',
                'submission_id': str(submission.id)
            })
        
        except PendingResultSubmission.DoesNotExist:
            return Response(
                {'error': 'Submission not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class SubmitResultWithEC8AView(APIView, PollingUnitAuthMixin):
    """
    POST: Submit election results with EC8A form image (for audit workflow)
    Expects multipart/form-data with:
        - unit_id
        - password
        - election_id
        - ec8a_form_image (file)
        - vote_data (JSON string): {"party_uuid": vote_count}
    
    Polling unit uses this endpoint to submit results for audit
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        polling_unit, error = self.authenticate_polling_unit(request)
        if error:
            return Response(error, status=status.HTTP_401_UNAUTHORIZED)
        
        election_id = request.data.get('election_id')
        ec8a_form_image = request.FILES.get('ec8a_form_image')
        vote_data_str = request.data.get('vote_data')
        
        if not election_id or not ec8a_form_image or not vote_data_str:
            return Response(
                {'error': 'election_id, ec8a_form_image, and vote_data are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            import json
            from .models import PendingResultSubmission
            
            election = Election.objects.get(id=election_id)
            
            # Parse vote_data JSON
            try:
                vote_data = json.loads(vote_data_str)
            except json.JSONDecodeError:
                return Response(
                    {'error': 'vote_data must be valid JSON'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create pending submission
            submission = PendingResultSubmission.objects.create(
                election=election,
                polling_unit=polling_unit,
                ec8a_form_image=ec8a_form_image,
                vote_data=vote_data,
                status='pending'
            )
            
            return Response({
                'message': 'Result submitted for review',
                'submission_id': str(submission.id),
                'status': 'pending'
            }, status=status.HTTP_201_CREATED)
        
        except Election.DoesNotExist:
            return Response(
                {'error': 'Election not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class GetRejectionNotificationsView(APIView, PollingUnitAuthMixin):
    """
    GET: Get rejection notifications for a polling unit
    Query params:
        - unit_id: Polling unit ID
        - password: Polling unit password
        - election_id (optional): Filter by election
    
    Returns all rejection notifications for this polling unit
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        polling_unit, error = self.authenticate_polling_unit(request)
        if error:
            return Response(error, status=status.HTTP_401_UNAUTHORIZED)
        
        election_id = request.query_params.get('election_id')
        
        try:
            from .models import RejectionNotification, PendingResultSubmission
            
            # Get all rejected submissions for this polling unit
            rejected_submissions = PendingResultSubmission.objects.filter(
                polling_unit=polling_unit,
                status='rejected'
            )
            
            if election_id:
                rejected_submissions = rejected_submissions.filter(election_id=election_id)
            
            # Get notifications for these submissions
            notifications = RejectionNotification.objects.filter(
                submission__in=rejected_submissions
            ).select_related('submission', 'submission__election').order_by('-rejected_at')
            
            notification_data = []
            for notif in notifications:
                notification_data.append({
                    'id': str(notif.id),
                    'submission_id': str(notif.submission.id),
                    'election_name': notif.submission.election.name,
                    'reason': notif.reason,
                    'rejected_at': notif.rejected_at.isoformat(),
                    'rejected_by': notif.rejected_by,
                    'is_read': notif.is_read,
                    'read_at': notif.read_at.isoformat() if notif.read_at else None,
                })
                
                # Mark as read
                if not notif.is_read:
                    notif.is_read = True
                    notif.read_at = __import__('django.utils.timezone', fromlist=['now']).now()
                    notif.save()
            
            return Response({
                'polling_unit': {
                    'id': str(polling_unit.id),
                    'unit_id': polling_unit.unit_id,
                    'name': polling_unit.name,
                },
                'notifications': notification_data,
                'total_count': len(notification_data)
            })
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StartLiveStreamView(APIView, PollingUnitAuthMixin):
    """
    POST: Start a live stream session from a polling unit
    Body: {
        "unit_id": "PU-00001",
        "password": "...",
        "election_id": "uuid"
    }
    
    Returns: {
        "id": "stream_session_id",
        "polling_unit_id": "...",
        "is_active": true,
        "started_at": "2024-01-01T00:00:00Z"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        polling_unit, error = self.authenticate_polling_unit(request)
        if error:
            return Response(error, status=status.HTTP_401_UNAUTHORIZED)
        
        election_id = request.data.get('election_id')
        if not election_id:
            return Response(
                {'error': 'election_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            election = Election.objects.get(id=election_id)
            
            # End any existing active streams for this polling unit in this election
            LiveStreamSession.objects.filter(
                polling_unit=polling_unit,
                election=election,
                is_active=True
            ).update(is_active=False)
            
            # Create new stream session
            stream = LiveStreamSession.objects.create(
                election=election,
                polling_unit=polling_unit,
                is_active=True
            )
            
            from .serializers import LiveStreamSessionSerializer
            serializer = LiveStreamSessionSerializer(stream, context={'request': request})
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Election.DoesNotExist:
            return Response(
                {'error': 'Election not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EndLiveStreamView(APIView, PollingUnitAuthMixin):
    """
    POST: End a live stream session from a polling unit
    Body: {
        "unit_id": "PU-00001",
        "password": "...",
        "stream_id": "uuid",
        "duration_seconds": 3600  # Optional: duration of the stream
    }
    
    Returns: {
        "id": "stream_session_id",
        "is_active": false,
        "ended_at": "2024-01-01T01:00:00Z",
        "duration_seconds": 3600
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        polling_unit, error = self.authenticate_polling_unit(request)
        if error:
            return Response(error, status=status.HTTP_401_UNAUTHORIZED)
        
        stream_id = request.data.get('stream_id')
        if not stream_id:
            return Response(
                {'error': 'stream_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            stream = LiveStreamSession.objects.get(
                id=stream_id,
                polling_unit=polling_unit,
                is_active=True
            )
            
            # Update stream with end time
            stream.is_active = False
            stream.ended_at = timezone.now()
            
            # Calculate duration if provided
            duration_seconds = request.data.get('duration_seconds')
            if duration_seconds:
                stream.duration_seconds = duration_seconds
            else:
                # Calculate from start time
                time_diff = stream.ended_at - stream.started_at
                stream.duration_seconds = int(time_diff.total_seconds())
            
            stream.save()
            
            from .serializers import LiveStreamSessionSerializer
            serializer = LiveStreamSessionSerializer(stream, context={'request': request})
            
            return Response(serializer.data)
        
        except LiveStreamSession.DoesNotExist:
            return Response(
                {'error': 'Stream not found or already ended'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
