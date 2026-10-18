from django.db import connection
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        try:
            connection.ensure_connection()
            return Response(
                {"status": "healthy", "database": "connected"},
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"status": "unhealthy", "database": "disconnected"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
