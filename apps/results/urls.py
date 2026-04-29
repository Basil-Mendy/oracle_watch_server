from django.urls import path
from . import views
from . import admin_views
from .submission_status_view import GetSubmissionStatusView
from .download_views import (
    DownloadImageView, DownloadVideoView,
    BulkDownloadImagesView, BulkDownloadVideosView
)

app_name = 'results'

urlpatterns = [
    # Result Submission (Polling Unit Agent)
    path('submit/', views.SubmitElectionResultView.as_view(), name='submit-results'),
    path('upload-media/', views.UploadResultMediaView.as_view(), name='upload-media'),
    path('add-comment/', views.AddCommentView.as_view(), name='add-comment'),
    path('submission-status/', GetSubmissionStatusView.as_view(), name='submission-status'),
    
    # Download endpoints
    path('download-image/<uuid:image_id>/', DownloadImageView.as_view(), name='download-image'),
    path('download-video/<uuid:video_id>/', DownloadVideoView.as_view(), name='download-video'),
    path('bulk-download-images/', BulkDownloadImagesView.as_view(), name='bulk-download-images'),
    path('bulk-download-videos/', BulkDownloadVideosView.as_view(), name='bulk-download-videos'),
    
    # Admin API (for Results Management Dashboard)
    path('admin/videos/', admin_views.AdminVideosListView.as_view(), name='admin-videos'),
    path('admin/images/', admin_views.AdminImagesListView.as_view(), name='admin-images'),
    path('admin/comments/', admin_views.AdminCommentsListView.as_view(), name='admin-comments'),
    path('admin/live-streams/', admin_views.AdminLiveStreamsListView.as_view(), name='admin-live-streams'),
    path('admin/all/', admin_views.AdminAllResultsListView.as_view(), name='admin-all-results'),
    
    # Result Retrieval (Public)
    path('polling-unit/<str:unit_id>/<uuid:election_id>/', views.GetPollingUnitResultsView.as_view(), name='polling-unit-results'),
    path('aggregate/', views.GetElectionResultsAggregateView.as_view(), name='aggregate-results'),
    path('', views.GetHierarchicalResultsView.as_view(), name='hierarchical-results'),
]
