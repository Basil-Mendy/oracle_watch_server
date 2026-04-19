"""
Views for elections and parties management.
Used by Central Admin to create elections and manage parties.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from django.utils import timezone

from apps.common.permissions import IsCentralAdmin
from .models import Party, Election, ElectionParty
from .serializers import PartySerializer, ElectionSerializer, ElectionDetailSerializer


class PartyListCreateView(ListCreateAPIView):
    """
    GET: List all parties (public)
    POST: Create a new party (admin only)
    """
    queryset = Party.objects.all()
    serializer_class = PartySerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsCentralAdmin()]
        return []


class PartyDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Get a specific party
    PUT: Update a party (admin only)
    DELETE: Delete a party (admin only)
    """
    queryset = Party.objects.all()
    serializer_class = PartySerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsCentralAdmin()]


class ElectionListCreateView(ListCreateAPIView):
    """
    GET: List elections (public access for result center)
    POST: Create a new election (admin only)
    """
    serializer_class = ElectionSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsCentralAdmin()]
        return []
    
    def get_queryset(self):
        """List elections and check if status needs updating"""
        queryset = Election.objects.all()
        
        # Update status for any upcoming elections that should be active
        upcoming = queryset.filter(status='upcoming')
        now = timezone.now()
        for election in upcoming:
            if now >= election.election_date:
                election.status = 'active'
                election.save(update_fields=['status', 'updated_at'])
        
        # Re-fetch to get updated queryset
        queryset = Election.objects.all()
        
        # Allow filtering by status
        status_filter = self.request.query_params.get('status')
        if status_filter in ['upcoming', 'active', 'ended']:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-election_date')


class ElectionDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Get a specific election with all its parties
    PUT: Update election details (admin only)
    DELETE: Delete an election (admin only)
    """
    queryset = Election.objects.all()
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ElectionDetailSerializer
        return ElectionSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsCentralAdmin()]


class ElectionEndView(APIView):
    """
    POST: End an election (mark it as ended/completed)
    Body: {"election_id": "uuid"}
    
    Once ended, the election is archived with its final results.
    """
    permission_classes = [IsAuthenticated, IsCentralAdmin]
    
    def post(self, request, election_id):
        try:
            election = Election.objects.get(id=election_id)
            
            if election.status == 'ended':
                return Response(
                    {'error': 'This election has already been ended'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            election.status = 'ended'
            election.ended_at = timezone.now()
            election.save(update_fields=['status', 'ended_at', 'updated_at'])
            
            return Response(
                {'message': f'Election "{election.name}" has been ended', 'election': ElectionSerializer(election).data},
                status=status.HTTP_200_OK
            )
        except Election.DoesNotExist:
            return Response(
                {'error': 'Election not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ElectionAddPartiesView(APIView):
    """
    POST: Add parties to an election
    Body: {
        "election_id": "uuid",
        "party_ids": ["party-uuid-1", "party-uuid-2"]
    }
    
    Links parties to an election so they can compete in it.
    """
    permission_classes = [IsAuthenticated, IsCentralAdmin]
    
    def post(self, request):
        election_id = request.data.get('election_id')
        party_ids = request.data.get('party_ids', [])
        
        if not election_id or not party_ids:
            return Response(
                {'error': 'Both election_id and party_ids are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            election = Election.objects.get(id=election_id)
            
            for party_id in party_ids:
                try:
                    party = Party.objects.get(id=party_id)
                    ElectionParty.objects.get_or_create(
                        election=election,
                        party=party
                    )
                except Party.DoesNotExist:
                    return Response(
                        {'error': f'Party {party_id} not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            return Response(
                {'message': 'Parties added to election successfully', 'election': ElectionDetailSerializer(election).data},
                status=status.HTTP_201_CREATED
            )
        except Election.DoesNotExist:
            return Response(
                {'error': 'Election not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ElectionRemovePartyView(APIView):
    """
    DELETE: Remove a party from an election
    Body: {"election_id": "uuid", "party_id": "uuid"}
    """
    permission_classes = [IsAuthenticated, IsCentralAdmin]
    
    def delete(self, request):
        election_id = request.data.get('election_id')
        party_id = request.data.get('party_id')
        
        if not election_id or not party_id:
            return Response(
                {'error': 'Both election_id and party_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            ep = ElectionParty.objects.get(election_id=election_id, party_id=party_id)
            ep.delete()
            
            return Response(
                {'message': 'Party removed from election'},
                status=status.HTTP_200_OK
            )
        except ElectionParty.DoesNotExist:
            return Response(
                {'error': 'Party not found in this election'},
                status=status.HTTP_404_NOT_FOUND
            )
