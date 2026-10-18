from django.urls import path
from vehicles.views import VehicleListCreateView

urlpatterns = [
    path("", VehicleListCreateView.as_view(), name="vehicle-list-create"),
]
