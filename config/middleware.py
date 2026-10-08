from django.utils.cache import patch_cache_control
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from time import time


class InactividadMiddleware:
    """Reject expired sessions before private views, renewing on authenticated requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now = time()
            last = request.session.get('ultima_actividad', now)
            if now - last >= settings.SESSION_IDLE_TIMEOUT:
                logout(request)
                return redirect('login')
            request.session['ultima_actividad'] = now
        response = self.get_response(request)
        if request.user.is_authenticated:
            request.session.setdefault('ultima_actividad', time())
        return response


class DatosPrivadosMiddleware:
    """Prevent shared/browser caches from retaining authenticated municipal data."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        patch_cache_control(response, private=True, no_store=True)
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        return response
