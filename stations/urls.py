from django.urls import path
from stations.views import StationDetailView, StationListView

urlpatterns = [
    path("", StationListView.as_view(), name="station-list"),
    path("<int:pk>/", StationDetailView.as_view(), name="station-detail"),
]
