from django.urls import path
from . import views

app_name = 'elections'

urlpatterns = [
    # Party Management
    path('parties/', views.PartyListCreateView.as_view(), name='party-list-create'),
    path('parties/<uuid:pk>/', views.PartyDetailView.as_view(), name='party-detail'),
    
    # Election Management
    path('', views.ElectionListCreateView.as_view(), name='election-list-create'),
    path('<uuid:pk>/', views.ElectionDetailView.as_view(), name='election-detail'),
    path('<uuid:election_id>/end/', views.ElectionEndView.as_view(), name='election-end'),
    
    # Election Parties Management
    path('add-parties/', views.ElectionAddPartiesView.as_view(), name='add-parties'),
    path('remove-party/', views.ElectionRemovePartyView.as_view(), name='remove-party'),
]
