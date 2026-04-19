from django.urls import path
from . import views

app_name = 'locations'

urlpatterns = [
    # LGA Management
    path('lgas/', views.LGAListView.as_view(), name='lga-list'),
    
    # Ward Management
    path('wards/', views.WardListView.as_view(), name='ward-list'),
    
    # Polling Unit Management
    path('polling-units/', views.PollingUnitListCreateView.as_view(), name='polling-unit-list-create'),
    
    # Polling Unit Admin Functions (must come before detail routes)
    path('polling-units/reset-password/', views.PollingUnitPasswordResetView.as_view(), name='reset-password'),
    path('polling-units/fetch-passwords/', views.PollingUnitPasswordFetchView.as_view(), name='fetch-passwords'),
    path('polling-units/bulk-upload-excel/', views.PollingUnitExcelUploadView.as_view(), name='bulk-upload-excel'),
    
    # Polling Unit Detail (must come after specific routes)
    path('polling-units/<uuid:pk>/', views.PollingUnitDetailView.as_view(), name='polling-unit-detail'),
    
    # Bulk Operations
    path('bulk-create/', views.BulkCreatePollingUnitsView.as_view(), name='bulk-create'),
]
