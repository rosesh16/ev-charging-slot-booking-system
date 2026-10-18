from rest_framework import generics, permissions
from stations.models import Charger, Station
from stations.serializers import (
    ChargerFilterSerializer,
    ChargerSerializer,
    StationDetailSerializer,
    StationListSerializer,
)


class StationListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = StationListSerializer
    queryset = Station.objects.filter(is_active=True).order_by("name")


class StationDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = StationDetailSerializer
    queryset = Station.objects.filter(is_active=True)


class ChargerListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ChargerSerializer

    def get_queryset(self):
        queryset = (
            Charger.objects.filter(
                is_active=True,
                station__is_active=True,
            )
            .select_related("station")
            .order_by("station__name", "name")
        )

        station_param = self.request.query_params.get("station")
        if station_param is not None:
            filter_serializer = ChargerFilterSerializer(
                data={"station": station_param}
            )
            filter_serializer.is_valid(raise_exception=True)
            station_obj = filter_serializer.validated_data["station"]
            queryset = queryset.filter(station=station_obj)

        return queryset
