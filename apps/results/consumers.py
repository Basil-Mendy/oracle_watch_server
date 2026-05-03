"""
WebRTC Signaling Server for Live Streaming

Handles WebSocket connections and exchanges:
- SDP offers/answers between broadcaster (polling unit) and viewers (admin)
- ICE candidates for NAT traversal
- Authentication and session management

Install: pip install channels channels-redis
"""

import json
import asyncio
import uuid
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from apps.locations.models import PollingUnit
from apps.elections.models import Election


class LiveStreamSession:
    """In-memory session management for active streams"""
    sessions = {}  # {sessionId: {broadcaster, viewers, sdp, ice_candidates}}

    @classmethod
    def create(cls, unit_id, election_id):
        """Create new streaming session"""
        session_id = str(uuid.uuid4())
        cls.sessions[session_id] = {
            'unit_id': unit_id,
            'election_id': election_id,
            'broadcaster': None,
            'viewers': set(),
            'sdp': None,
            'ice_candidates': [],
            'created_at': asyncio.get_event_loop().time(),
        }
        return session_id

    @classmethod
    def get(cls, session_id):
        """Get session"""
        return cls.sessions.get(session_id)
    
    @classmethod
    def get_or_create(cls, session_id, unit_id='unknown', election_id='unknown'):
        """Get or create session (for viewers who connect with a session_id)"""
        if session_id not in cls.sessions:
            cls.sessions[session_id] = {
                'unit_id': unit_id,
                'election_id': election_id,
                'broadcaster': None,
                'viewers': set(),
                'sdp': None,
                'ice_candidates': [],
                'created_at': asyncio.get_event_loop().time(),
            }
        return cls.sessions[session_id]

    @classmethod
    def add_broadcaster(cls, session_id, consumer):
        """Add broadcaster to session"""
        if session := cls.get_or_create(session_id):
            session['broadcaster'] = consumer
            return True
        return False

    @classmethod
    def add_viewer(cls, session_id, consumer):
        """Add viewer to session"""
        if session := cls.get_or_create(session_id):
            session['viewers'].add(consumer)
            return True
        return False

    @classmethod
    def remove_viewer(cls, session_id, consumer):
        """Remove viewer from session"""
        if session := cls.get(session_id):
            session['viewers'].discard(consumer)

    @classmethod
    def broadcast_to_viewers(cls, session_id, message):
        """Send message to all viewers in session"""
        if session := cls.get(session_id):
            for viewer in session['viewers']:
                asyncio.create_task(viewer.send(json.dumps(message)))


class LiveStreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for WebRTC signaling
    
    Flow:
    1. Polling Unit: Authenticates as broadcaster with unit credentials
    2. Admin: Authenticates as viewer with auth token
    3. Both: Exchange SDP offers/answers and ICE candidates
    4. Video: Flows directly via P2P WebRTC connection
    """

    async def connect(self):
        """Accept WebSocket connection"""
        await self.accept()
        self.session_id = None
        self.role = None  # 'broadcaster' or 'viewer'
        self.unit_id = None

    # Sync-to-async database query helpers
    @sync_to_async
    def get_polling_unit(self, unit_id):
        """Get polling unit from database"""
        return PollingUnit.objects.get(unit_id=unit_id)

    @sync_to_async
    def get_election(self, election_id):
        """Get election from database"""
        return Election.objects.get(id=election_id)

    async def disconnect(self, close_code):
        """Clean up on disconnect"""
        if self.session_id:
            if self.role == 'broadcaster':
                # Broadcaster disconnected - notify all viewers
                session = LiveStreamSession.get(self.session_id)
                if session:
                    await self.broadcast_to_viewers({
                        'type': 'broadcaster_disconnected',
                        'message': 'Live stream ended'
                    })
                    # Clean up session
                    LiveStreamSession.sessions.pop(self.session_id, None)
            else:
                # Viewer disconnected
                LiveStreamSession.remove_viewer(self.session_id, self)

    async def receive(self, text_data):
        """Handle incoming WebSocket message"""
        try:
            message = json.loads(text_data)
            msg_type = message.get('type')

            if msg_type == 'auth':
                await self.handle_auth(message)
            elif msg_type == 'offer':
                await self.handle_offer(message)
            elif msg_type == 'answer':
                await self.handle_answer(message)
            elif msg_type == 'ice_candidate':
                await self.handle_ice_candidate(message)
            else:
                await self.send_error(f'Unknown message type: {msg_type}')

        except json.JSONDecodeError:
            await self.send_error('Invalid JSON')
        except Exception as e:
            await self.send_error(str(e))

    async def handle_auth(self, message):
        """
        Authenticate user as broadcaster or viewer
        
        Broadcaster (Polling Unit):
        {
          "type": "auth",
          "unitId": "AB/UMU/PU/0001",
          "password": "polling_unit_password",
          "electionId": "uuid",
          "role": "broadcaster"
        }
        
        Viewer (Admin):
        {
          "type": "auth",
          "sessionId": "stream-uuid",
          "token": "auth_token",
          "role": "viewer"
        }
        """

        role = message.get('role')

        if role == 'broadcaster':
            # Authenticate polling unit
            unit_id = message.get('unitId')
            password = message.get('password')
            election_id = message.get('electionId')

            try:
                # Verify polling unit credentials (use sync_to_async)
                polling_unit = await self.get_polling_unit(unit_id)
                if not check_password(password, polling_unit.password):
                    await self.send_error('Invalid credentials')
                    return

                # Verify election exists (use sync_to_async)
                election = await self.get_election(election_id)

                # Create streaming session
                session_id = LiveStreamSession.create(unit_id, election_id)
                LiveStreamSession.add_broadcaster(session_id, self)

                self.session_id = session_id
                self.role = 'broadcaster'
                self.unit_id = unit_id

                await self.send(json.dumps({
                    'type': 'auth_success',
                    'sessionId': session_id,
                    'message': f'Welcome {polling_unit.name}!'
                }))

            except PollingUnit.DoesNotExist:
                await self.send_error('Polling unit not found')
            except Election.DoesNotExist:
                await self.send_error('Election not found')
            except Exception as e:
                await self.send_error(f'Authentication error: {str(e)}')

        elif role == 'viewer':
            # Authenticate admin viewer
            session_id = message.get('sessionId')
            auth_token = message.get('token')

            try:
                # Verify authentication token (from JWT or session)
                # For now, we'll accept any non-empty token
                # In production, verify JWT or session token
                if not auth_token:
                    await self.send_error('Invalid or missing token')
                    return

                # Get or create session (viewers might connect before broadcaster)
                session = LiveStreamSession.get_or_create(session_id)

                # Add viewer to session
                LiveStreamSession.add_viewer(session_id, self)

                self.session_id = session_id
                self.role = 'viewer'

                await self.send(json.dumps({
                    'type': 'auth_success',
                    'sessionId': session_id,
                    'message': 'Connected to live stream'
                }))

                # If broadcaster has already sent offer, relay it to this viewer
                if session['sdp']:
                    await self.send(json.dumps({
                        'type': 'offer',
                        'sdp': session['sdp']
                    }))

                    # Relay any ICE candidates already received
                    for candidate in session['ice_candidates']:
                        await self.send(json.dumps({
                            'type': 'ice_candidate',
                            'candidate': candidate
                        }))

            except Exception as e:
                await self.send_error(f'Viewer authentication error: {str(e)}')

        else:
            await self.send_error('Invalid role. Must be "broadcaster" or "viewer"')

    async def handle_offer(self, message):
        """Handle SDP offer from broadcaster"""
        if self.role != 'broadcaster':
            await self.send_error('Only broadcaster can send offers')
            return

        session = LiveStreamSession.get(self.session_id)
        if not session:
            await self.send_error('Session not found')
            return

        # Store offer in session
        session['sdp'] = message.get('sdp')

        # Relay offer to all viewers
        LiveStreamSession.broadcast_to_viewers(self.session_id, {
            'type': 'offer',
            'sdp': message.get('sdp')
        })

    async def handle_answer(self, message):
        """Handle SDP answer from viewer"""
        if self.role != 'viewer':
            await self.send_error('Only viewers can send answers')
            return

        session = LiveStreamSession.get(self.session_id)
        if not session or not session['broadcaster']:
            await self.send_error('Broadcaster not connected')
            return

        # Relay answer to broadcaster
        broadcaster = session['broadcaster']
        await broadcaster.send(json.dumps({
            'type': 'answer',
            'sdp': message.get('sdp')
        }))

    async def handle_ice_candidate(self, message):
        """Handle ICE candidate from either broadcaster or viewer"""
        session = LiveStreamSession.get(self.session_id)
        if not session:
            await self.send_error('Session not found')
            return

        candidate = message.get('candidate')

        if self.role == 'broadcaster':
            # Store and relay broadcaster's ICE candidates to viewers
            session['ice_candidates'].append(candidate)
            LiveStreamSession.broadcast_to_viewers(self.session_id, {
                'type': 'ice_candidate',
                'candidate': candidate
            })
        else:
            # Relay viewer's ICE candidates to broadcaster
            if session['broadcaster']:
                await session['broadcaster'].send(json.dumps({
                    'type': 'ice_candidate',
                    'candidate': candidate
                }))

    async def send_error(self, error_message):
        """Send error message to client"""
        await self.send(json.dumps({
            'type': 'auth_error' if not self.session_id else 'error',
            'error': error_message
        }))
