"""
Views for locations management (LGA, Ward, PollingUnit)
Used by Central Admin to create and manage polling units.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth.hashers import make_password
from django.db import transaction
import openpyxl
from io import BytesIO

from apps.common.permissions import IsCentralAdmin
from .utils import generate_polling_unit_password
from .models import LGA, Ward, PollingUnit
from .serializers import (
    LGASerializer, WardSerializer, PollingUnitSerializer,
    PollingUnitDetailSerializer, PollingUnitListSerializer,
    PollingUnitCreateSerializer, PollingUnitCreateResponseSerializer, PasswordResetResponseSerializer
)


class LGAListView(ListCreateAPIView):
    """
    GET: List all LGAs (public)
    POST: Create a new LGA (admin only)
    """
    queryset = LGA.objects.all()
    serializer_class = LGASerializer
    pagination_class = None  # Disable pagination to return all LGAs
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsCentralAdmin()]
        return []


class WardListView(ListCreateAPIView):
    """
    GET: List all wards (public), optionally filter by LGA
    POST: Create a new ward (admin only)
    """
    serializer_class = WardSerializer
    pagination_class = None  # Disable pagination to return all wards
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsCentralAdmin()]
        return []
    
    def get_queryset(self):
        """Allow filtering by LGA"""
        queryset = Ward.objects.all()
        lga_id = self.request.query_params.get('lga_id')
        if lga_id:
            queryset = queryset.filter(lga_id=lga_id)
        return queryset
    
    def perform_create(self, serializer):
        """Ensure ward is created by an admin"""
        serializer.save()


class PollingUnitListCreateView(ListCreateAPIView):
    """
    GET: List polling units (public), optionally filter by LGA or Ward
    POST: Create a new polling unit (admin only)
    
    On creation, returns the temporary plain-text password (shown only once).
    """
    pagination_class = None  # Disable pagination to return all polling units
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsCentralAdmin()]
        return []
    
    def get_queryset(self):
        """Allow filtering by LGA or Ward"""
        queryset = PollingUnit.objects.all()
        lga_id = self.request.query_params.get('lga_id')
        ward_id = self.request.query_params.get('ward_id')
        
        if lga_id:
            queryset = queryset.filter(lga_id=lga_id)
        if ward_id:
            queryset = queryset.filter(ward_id=ward_id)
        
        return queryset
    
    def get_serializer_class(self):
        """Use different serializer for list vs creation"""
        if self.request.method == 'GET':
            return PollingUnitListSerializer
        if self.request.method == 'POST':
            return PollingUnitCreateSerializer
        return PollingUnitSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Override create to:
        1. Generate a secure random password
        2. Hash and save to database
        3. Store plaintext for display/printing purposes
        4. Return the plain-text password in response
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Generate temporary password (5-8 chars)
        temporary_password = generate_polling_unit_password()
        
        # Hash and save, also store plaintext for printing
        instance = serializer.save(
            password=make_password(temporary_password),
            plaintext_password=temporary_password
        )
        
        # Prepare response with plain-text password
        response_serializer = PollingUnitCreateResponseSerializer(
            instance,
            context={'temporary_password': temporary_password}
        )
        response_data = response_serializer.data
        response_data['warning'] = 'This password will not be shown again. Please share it with the agent immediately.'
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    def perform_create(self, serializer):
        """Password is handled in create() method"""
        pass  # Don't call save here - handled in create()


class PollingUnitDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET: Get a specific polling unit
    PUT: Update a polling unit (admin only)
    DELETE: Delete a polling unit (admin only)
    """
    queryset = PollingUnit.objects.all()
    serializer_class = PollingUnitDetailSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsCentralAdmin()]


class PollingUnitPasswordResetView(APIView):
    """
    POST: Reset the password for a polling unit
    
    The backend generates a new secure password, hashes it, saves it,
    and returns the plain-text password only in this response (ephemeral).
    
    Body: {
        "polling_unit_id": "unit-uuid"  (or "unit_id": "AB/ANI/PU/0001")
    }
    
    Response: {
        "status": "success",
        "message": "Password reset successfully for ...",
        "pu_code": "AB/ANI/PU/0001",
        "pu_name": "Polling Unit Name",
        "temporary_password": "Xy8#Mn2P",
        "warning": "This password will not be shown again..."
    }
    
    Used by admin to reset polling unit credentials when agent loses password.
    """
    permission_classes = [IsAuthenticated, IsCentralAdmin]
    
    def post(self, request):
        # Accept either 'polling_unit_id' (UUID) or 'unit_id' (the PU Code)
        polling_unit_id = request.data.get('polling_unit_id')
        unit_code = request.data.get('unit_id')  # e.g., "AB/ANI/PU/0001"
        
        if not polling_unit_id and not unit_code:
            return Response(
                {'error': 'Either polling_unit_id (UUID) or unit_id (PU Code) is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Find the polling unit
            if polling_unit_id:
                polling_unit = PollingUnit.objects.get(id=polling_unit_id)
            else:
                polling_unit = PollingUnit.objects.get(unit_id=unit_code)
            
            # Generate new secure password
            temporary_password = generate_polling_unit_password()
            
            # Hash and save to database, also store plaintext
            polling_unit.password = make_password(temporary_password)
            polling_unit.plaintext_password = temporary_password
            polling_unit.save(update_fields=['password', 'plaintext_password', 'updated_at'])
            
            # Return response with plain-text password (ephemeral)
            response_serializer = PasswordResetResponseSerializer({
                'status': 'success',
                'message': f'Password reset successfully for {polling_unit.name}',
                'pu_code': polling_unit.unit_id,
                'pu_name': polling_unit.name,
                'temporary_password': temporary_password,
                'warning': 'This password will not be shown again. Please share it with the agent immediately.'
            })
            
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        except PollingUnit.DoesNotExist:
            search_field = 'unit_id' if unit_code else 'id'
            search_value = unit_code or polling_unit_id
            return Response(
                {'error': f'Polling unit with {search_field}={search_value} not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class PollingUnitPasswordFetchView(APIView):
    """
    POST: Fetch polling unit credentials for printing
    Body: {
        "lga_id": "optional-lga-id",
        "ward_id": "optional-ward-id",
        "unit_ids": ["PU-00001", "PU-00002"]  # optional - specific units
    }
    
    Returns: List of polling units with their IDs and passwords
    
    Used by admin to fetch credentials for printing.
    """
    permission_classes = [IsAuthenticated, IsCentralAdmin]
    
    def post(self, request):
        lga_id = request.data.get('lga_id')
        ward_id = request.data.get('ward_id')
        unit_ids = request.data.get('unit_ids', [])
        
        queryset = PollingUnit.objects.all()
        
        if lga_id:
            queryset = queryset.filter(lga_id=lga_id)
        if ward_id:
            queryset = queryset.filter(ward_id=ward_id)
        if unit_ids:
            queryset = queryset.filter(unit_id__in=unit_ids)
        
        polling_units = queryset.values('id', 'unit_id', 'name', 'lga__name', 'ward__name', 'plaintext_password', 'created_at')
        
        # Normalize field names: lga__name -> lga_name, ward__name -> ward_name
        normalized_units = [
            {
                'id': unit['id'],
                'unit_id': unit['unit_id'],
                'name': unit['name'],
                'lga_name': unit['lga__name'],
                'ward_name': unit['ward__name'],
                'password': unit['plaintext_password'] or 'N/A',  # Return plaintext password for display
                'created_at': unit['created_at'].isoformat() if unit['created_at'] else None,
            }
            for unit in polling_units
        ]
        
        return Response(
            normalized_units,
            status=status.HTTP_200_OK
        )


class BulkCreatePollingUnitsView(APIView):
    """
    POST: Create multiple polling units from Excel data
    Body: {
        "wards": [
            {"name": "Ward Name", "lga_id": "lga-uuid"},
            ...
        ],
        "polling_units": [
            {"name": "PU Name", "ward_id": "ward-uuid", "lga_id": "lga-uuid"},
            ...
        ]
    }
    
    Used by admin to bulk upload ward and polling unit data.
    """
    permission_classes = [IsAuthenticated, IsCentralAdmin]
    
    @transaction.atomic
    def post(self, request):
        wards_data = request.data.get('wards', [])
        polling_units_data = request.data.get('polling_units', [])
        
        created_wards = []
        created_polling_units = []
        errors = []
        
        # Create wards
        for ward_data in wards_data:
            try:
                ward = Ward.objects.create(
                    name=ward_data['name'],
                    lga_id=ward_data['lga_id']
                )
                created_wards.append({
                    'id': str(ward.id),
                    'name': ward.name,
                    'lga_id': str(ward.lga_id)
                })
            except Exception as e:
                errors.append(f"Ward creation error: {str(e)}")
        
        # Create polling units
        for pu_data in polling_units_data:
            try:
                password = generate_polling_unit_password()
                pu = PollingUnit.objects.create(
                    name=pu_data['name'],
                    ward_id=pu_data['ward_id'],
                    lga_id=pu_data['lga_id'],
                    password=make_password(password),
                    plaintext_password=password
                )
                created_polling_units.append({
                    'unit_id': pu.unit_id,
                    'name': pu.name,
                    'password': password  # Return password only once
                })
            except Exception as e:
                errors.append(f"Polling unit creation error: {str(e)}")
        
        return Response(
            {
                'created_wards': created_wards,
                'created_polling_units': created_polling_units,
                'errors': errors
            },
            status=status.HTTP_201_CREATED if not errors else status.HTTP_206_PARTIAL_CONTENT
        )


class PollingUnitExcelUploadView(APIView):
    """
    POST: Create multiple polling units from an Excel file
    
    Excel file must contain columns:
    - lga_name: Name of the LGA
    - ward_name: Name of the Ward within the LGA
    - unit_name: Name of the Polling Unit
    - unit_id (optional): Custom polling unit ID
    
    Returns: {
        'created_count': number of polling units created,
        'failed_count': number of rows that failed,
        'errors': list of error messages,
        'units': list of created polling units with their passwords
    }
    """
    permission_classes = [IsAuthenticated, IsCentralAdmin]
    parser_classes = (MultiPartParser, FormParser)
    
    @transaction.atomic
    def post(self, request):
        try:
            # Get the uploaded file
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read Excel file
            file_content = uploaded_file.read()
            workbook = openpyxl.load_workbook(BytesIO(file_content))
            worksheet = workbook.active
            
            created_units = []
            failed_rows = []
            
            # Get headers (first row)
            headers = {}
            for col_idx, cell in enumerate(worksheet[1], 1):
                header_name = cell.value.strip().lower() if cell.value else None
                if header_name:
                    headers[header_name] = col_idx
            
            # Validate required columns
            required_columns = ['lga_name', 'ward_name', 'unit_name']
            missing_columns = [col for col in required_columns if col not in headers]
            if missing_columns:
                return Response(
                    {'error': f'Missing required columns: {", ".join(missing_columns)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process each row (starting from row 2, after headers)
            for row_idx, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True), 2):
                try:
                    lga_name = row[headers['lga_name'] - 1]
                    ward_name = row[headers['ward_name'] - 1]
                    unit_name = row[headers['unit_name'] - 1]
                    custom_unit_id = row[headers.get('unit_id', 0) - 1] if 'unit_id' in headers else None
                    
                    # Validate required fields
                    if not all([lga_name, ward_name, unit_name]):
                        failed_rows.append({
                            'row': row_idx,
                            'error': 'Missing required fields (lga_name, ward_name, unit_name)'
                        })
                        continue
                    
                    # Get or create LGA
                    lga, _ = LGA.objects.get_or_create(name=str(lga_name).strip())
                    
                    # Get or create Ward
                    ward, _ = Ward.objects.get_or_create(
                        name=str(ward_name).strip(),
                        lga=lga
                    )
                    
                    # Create Polling Unit
                    password = generate_polling_unit_password()
                    polling_unit = PollingUnit.objects.create(
                        name=str(unit_name).strip(),
                        lga=lga,
                        ward=ward,
                        password=make_password(password),
                        plaintext_password=password,
                        custom_unit_id=custom_unit_id
                    )
                    
                    created_units.append({
                        'unit_id': polling_unit.unit_id,
                        'name': polling_unit.name,
                        'lga_name': lga.name,
                        'ward_name': ward.name,
                        'password': password,
                        'created_at': polling_unit.created_at.isoformat()
                    })
                    
                except Exception as e:
                    failed_rows.append({
                        'row': row_idx,
                        'error': str(e)
                    })
            
            return Response(
                {
                    'created_count': len(created_units),
                    'failed_count': len(failed_rows),
                    'errors': failed_rows,
                    'units': created_units
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {'error': f'Failed to process Excel file: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
