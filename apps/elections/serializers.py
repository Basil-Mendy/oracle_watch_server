"""
Serializers for the elections app - converts Election, Party, ElectionParty models to/from JSON
"""
from rest_framework import serializers
from .models import Party, Election, ElectionParty


class PartySerializer(serializers.ModelSerializer):
    """Serializer for Party model"""
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Party
        fields = ['id', 'name', 'acronym', 'logo', 'logo_url', 'is_starred', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_logo_url(self, obj):
        """Get the full URL to the party logo"""
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
        return None


class ElectionPartySerializer(serializers.ModelSerializer):
    """Serializer for ElectionParty junction model"""
    party_details = PartySerializer(source='party', read_only=True)
    
    class Meta:
        model = ElectionParty
        fields = ['id', 'election', 'party', 'party_details', 'created_at']
        read_only_fields = ['id', 'created_at']


class ElectionSerializer(serializers.ModelSerializer):
    """Serializer for Election model"""
    parties_count = serializers.SerializerMethodField()
    parties = serializers.SerializerMethodField()
    
    class Meta:
        model = Election
        fields = [
            'id', 'name', 'election_date', 'status',
            'parties_count', 'parties', 'created_at', 'ended_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_parties_count(self, obj):
        """Get the number of parties in this election"""
        return obj.election_parties.count()
    
    def get_parties(self, obj):
        """Get all parties for this election with their details"""
        election_parties = obj.election_parties.all()
        if election_parties:
            # Return just the Party data, not the ElectionParty junction data
            parties_list = [ep.party for ep in election_parties]
            return PartySerializer(parties_list, many=True, context=self.context).data
        return []


class ElectionDetailSerializer(ElectionSerializer):
    """Extended Election serializer with all parties and full details"""
    
    class Meta(ElectionSerializer.Meta):
        fields = ElectionSerializer.Meta.fields + ['updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'ended_at']
