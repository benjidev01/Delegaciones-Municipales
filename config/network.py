"""Client addressing at the explicitly configured reverse-proxy boundary."""
from ipaddress import ip_address
from django.conf import settings


def client_ip(request):
    address = request.META.get('REMOTE_ADDR')
    if settings.TRUST_PROXY:
        candidate = request.META.get('HTTP_X_REAL_IP', '')
        try:
            return str(ip_address(candidate))
        except ValueError:
            pass
    return address
