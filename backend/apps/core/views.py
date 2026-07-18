"""Health endpoint: the single most useful route in the whole app.

It really checks Postgres and Redis, so container/K8s probes and load
balancers can trust it. Phase 8 reuses this for liveness/readiness probes.
"""
import redis
from django.conf import settings
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    db_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        db_ok = False

    redis_ok = True
    try:
        redis.from_url(settings.REDIS_URL, socket_connect_timeout=2).ping()
    except Exception:
        redis_ok = False

    status = "ok" if db_ok and redis_ok else "degraded"
    return Response({"status": status, "db": db_ok, "redis": redis_ok})
